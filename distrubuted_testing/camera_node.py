import threading
import time
import socket
import json
import select
import sys
import queue
from PIL import Image
import io
import base64

from picamera2 import Picamera2
from datetime import datetime
import os
from libcamera import controls

# Ensure the photos directory exists
PHOTOS_DIR = "./data/photos"
os.makedirs(PHOTOS_DIR, exist_ok=True)

# Initialize the camera
picam2 = Picamera2()
capture_config = picam2.create_still_configuration(main={"size": (1920, 1080)})
picam2.configure(capture_config)

# Set focus mode to auto
picam2.set_controls({"AfMode": controls.AfModeEnum.Continuous})

# Set exposure mode to normal (auto)
picam2.set_controls({"AeEnable": True})

picam2.start()
time.sleep(2)  # Warm-up time

def log(message):
    print(f"[{time.strftime('%H:%M:%S')}] {message}")
    sys.stdout.flush()

class CameraNode:
    def __init__(self, node_id, ip, port, neighbors):
        self.node_id = node_id
        self.ip = ip
        self.port = port
        self.neighbors = neighbors  # Dictionary of neighbor_id: (ip, port, distance)
        self.routing_table = {node_id: (0, node_id)}  # Format: destination: (distance, next_hop)
        self.frame_number = 0
        self.lock = threading.Lock()

        # Camera calibration parameters
        self.camera_matrix = 0  # 3x3 intrinsic matrix
        self.dist_coeffs = 0      # Distortion coefficients
        self.rotation_matrix = 0  # 3x3 rotation matrix (world to camera)
        self.translation_vector = 0  # 3x1 translation vector

        # Create separate sockets for frames and routing
        self.detection_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.routing_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Bind sockets to different ports
        self.detection_socket.bind((ip, port))
        self.routing_socket.bind((ip, port + 1))
        
        self.running = True
        self.command_queue = queue.Queue()
        self.max_packet_size = 65507

    def start(self):
        # Start separate threads for frame and routing listeners
        threading.Thread(target=self.listen_for_detections, daemon=True).start()
        threading.Thread(target=self.listen_for_routing_updates, daemon=True).start()
        threading.Thread(target=self.send_periodic_routing_table_updates, daemon=True).start()
        threading.Thread(target=self.run_person_tracking_pipeline, daemon=True).start()

    def run_person_tracking_pipeline(self):
        # Block this thread from progressing until we fully process this frame.
        while self.frame_number != 10:
            self.take_snapshot_of_scene()
            # self.update_global_view()
            time.sleep(5)

        self.stop()

    def update_global_view(self):
        self.receive_view_from_all_nodes()
        # self.create_global_view()

    def take_snapshot_of_scene(self):
        self.take_photo()
        self.detect_people_in_frame()
        self.send_view_to_all_nodes()
        self.frame_number = self.frame_number + 1

    def take_photo(self):
        filename = os.path.join(PHOTOS_DIR, f"{self.frame_number:05d}.jpg")
        picam2.capture_file(filename)
        print(f"Photo taken: {filename}")

    def send_view_to_all_nodes(self):
        """Send detection results and camera parameters to all nodes"""
        # Get detections from the current frame
        detections = self.detect_people_in_frame()
        
        # Convert detections into global world xz coordinates
        # global_detections = convert_pixel_to_world(detections)
        
        # Prepare the detection message
        message = {
            'type': 'detection',
            'source_node': self.node_id,
            'frame_number': self.frame_number,
            'timestamp': time.time(),
            'detections': detections,
        }

        # Send to each destination node
        for dest_node, (dist, next_hop) in self.routing_table.items():
            if dest_node == self.node_id:
                continue
                
            if next_hop not in self.neighbors:
                log(f"Warning: Next hop {next_hop} not found in neighbors list")
                continue
                
            next_hop_ip, next_hop_port = self.neighbors[next_hop]
            message['destination_node'] = dest_node
            message['next_hop'] = next_hop
            
            try:
                json_data = json.dumps(message)
                self.detection_socket.sendto(json_data.encode(), (next_hop_ip, next_hop_port))
                log(f"Sent detections for frame {self.frame_number} to node {dest_node} via {next_hop}")
            except Exception as e:
                log(f"Error sending detections to node {dest_node}: {e}")

    def detect_people_in_frame(self):
        """Detect people in the current frame and return their bounding boxes"""
        # This is a placeholder
        detections = [
            {
                'bbox': [0, 0, 100, 100], # [x, y, width, height]
                'confidence': 70,
                'tracking_id': 1 
            }
        ]
        # Example detection format:
        # detections = [
        #     {
        #         'bbox': [x, y, width, height],
        #         'confidence': confidence_score,
        #         'tracking_id': unique_id 
        #     }
        # ]
        return detections

    def listen_for_detections(self):
        """Dedicated thread for handling incoming detection messages"""
        self.detection_socket.settimeout(1.0)
        while self.running:
            try:
                data, addr = self.detection_socket.recvfrom(4096)  # Smaller buffer size needed
                message = json.loads(data.decode())
                
                if message.get('type') == 'detection':
                    self.handle_detection_message(message, addr)
            except socket.timeout:
                continue
            except json.JSONDecodeError as e:
                log(f"Error decoding detection message: {e}")
            except Exception as e:
                log(f"Error in detection listener: {e}")

    def handle_detection_message(self, message, addr):
        """Handle received detection messages"""
        # Process detections if we're the destination
        if message['destination_node'] == self.node_id:
            frame_number = message['frame_number']
            source_node = message['source_node']
            timestamp = message['timestamp']
            detections = message['detections']
            calibration = message['calibration']
            
            # Convert calibration data back to numpy arrays if needed
            source_camera_matrix = np.array(calibration['camera_matrix'])
            source_dist_coeffs = np.array(calibration['dist_coeffs'])
            source_rotation_matrix = np.array(calibration['rotation_matrix'])
            source_translation_vector = np.array(calibration['translation_vector'])
            
            # Process the detections (implement your processing logic here)
            self.process_detections(
                detections, 
                frame_number, 
                source_node, 
                timestamp,
                source_camera_matrix,
                source_dist_coeffs,
                source_rotation_matrix,
                source_translation_vector
            )
            
            log(f"Received {len(detections)} detections from node {source_node} for frame {frame_number}")
        
        # Forward detections if we're not the destination
        else:
            dest_node = message['destination_node']
            if dest_node in self.routing_table:
                _, next_hop = self.routing_table[dest_node]
                if next_hop in self.neighbors:
                    next_hop_ip, next_hop_port = self.neighbors[next_hop]
                    message['next_hop'] = next_hop
                    json_data = json.dumps(message)
                    self.detection_socket.sendto(json_data.encode(), (next_hop_ip, next_hop_port))
                    log(f"Forwarded detections for frame {message['frame_number']} to node {dest_node} via {next_hop}")

    def process_detections(self, detections, frame_number, source_node, timestamp,
                         source_camera_matrix, source_dist_coeffs, 
                         source_rotation_matrix, source_translation_vector):
        """Process received detections and camera calibration data"""
        # This is where you would implement your detection processing logic
        # For example:
        # - Transform detections to world coordinates
        # - Merge detections from multiple cameras
        # - Track people across multiple views
        # - Update global state
        pass

    def listen_for_routing_updates(self):
        """Dedicated thread for handling routing table updates"""
        self.routing_socket.settimeout(1.0)
        while self.running:
            try:
                data, addr = self.routing_socket.recvfrom(1024)  # Smaller buffer for routing updates
                routing_data = json.loads(data.decode())
                
                if routing_data.get('type') == 'routing_update':
                    self.update_routing_table(routing_data['routing_table'])
            except socket.timeout:
                continue
            except json.JSONDecodeError as e:
                log(f"Error decoding routing message: {e}")
            except Exception as e:
                log(f"Error in routing listener: {e}")

    def send_periodic_routing_table_updates(self):
        while self.running:
            for neighbor, (ip, port) in self.neighbors.items():
                self.send_routing_table(ip, port)
            time.sleep(5)  # Send updates every 5 seconds

    def send_routing_table(self, ip, port):
        """Send routing table updates to neighbors"""
        message = {
            'type': 'routing_update',
            'routing_table': self.routing_table
        }
        data = json.dumps(message).encode()
        self.routing_socket.sendto(data, (ip, port + 1))

    def update_routing_table(self, neighbor_table):
        with self.lock:
            updated = False
            for dest, (dist, _) in neighbor_table.items():
                if dest not in self.routing_table or dist + 1 < self.routing_table[dest][0]:
                    self.routing_table[dest] = (dist + 1, next(iter(neighbor_table)))
                    updated = True
            if updated:
                log(f"Node {self.node_id} updated routing table:")
                self.print_routing_table()

    def print_routing_table(self):
        log(f"Routing table for node {self.node_id}:")
        for dest, (dist, next_hop) in self.routing_table.items():
            log(f"  Destination: {dest}, Distance: {dist}, Next Hop: {next_hop}")

    def stop(self):
        """Clean shutdown of the node"""
        self.running = False
        self.detection_socket.close()
        self.routing_socket.close()
        log(f"Node {self.node_id} shutting down...")