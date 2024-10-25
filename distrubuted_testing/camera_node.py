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

        # Add detection buffer and tracking
        self.detection_buffer = {}  # Format: {frame_number: {node_id: detection_data}}
        self.total_nodes = len(self.routing_table)  # Total number of nodes in network (including self)
        self.processed_frames = set()  # Keep track of which frames we've already processed
        self.detection_buffer_lock = threading.Lock()  # Thread safety for buffer access

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
        # self.detect_people_in_frame()
        self.send_view_to_all_nodes()
        self.frame_number = self.frame_number + 1

    def take_photo(self):
        filename = os.path.join(PHOTOS_DIR, f"{self.frame_number:05d}.jpg")
        picam2.capture_file(filename)
        print(f"Photo taken: {filename}")

    def send_view_to_all_nodes(self):
        """Send detection results to all nodes"""
        # Get detections from the current frame
        detections = self.detect_people_in_frame()
        current_time = time.time()
        
        # Store our own detections in the buffer
        with self.detection_buffer_lock:
            if self.frame_number not in self.detection_buffer:
                self.detection_buffer[self.frame_number] = {}
            
            self.detection_buffer[self.frame_number][self.node_id] = {
                'detections': detections,
                'timestamp': current_time
            }
            
            log(f"Stored own detections for frame {self.frame_number}. " +
                f"Now have {len(self.detection_buffer[self.frame_number])}/{self.total_nodes} nodes")
        
        # Prepare the detection message
        message = {
            'type': 'detection',
            'source_node': self.node_id,
            'frame_number': self.frame_number,
            'timestamp': current_time,
            'detections': detections
        }

        # Send to each destination node in routing table
        for dest_node in self.routing_table:
            if dest_node == self.node_id:
                continue
                
            dist, next_hop = self.routing_table[dest_node]
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
                'tracking_id': self.frame_number
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
        frame_number = message['frame_number']
        source_node = message['source_node']
        
        # Process detections if we're the destination
        if message['destination_node'] == self.node_id:
            with self.detection_buffer_lock:
                # Initialise buffer for this frame if it doesn't exist
                if frame_number not in self.detection_buffer:
                    self.detection_buffer[frame_number] = {}
                
                # Store the detection in our buffer
                self.detection_buffer[frame_number][source_node] = {
                    'detections': message['detections'],
                    'timestamp': message['timestamp']
                }
                
                # Check if we have all detections for this frame
                if (len(self.detection_buffer[frame_number]) == self.total_nodes and 
                    frame_number not in self.processed_frames):
                    self.process_complete_frame_detection_buffer(frame_number)
                    
                log(f"Received detections from node {source_node} for frame {frame_number}. " +
                    f"Have {len(self.detection_buffer[frame_number])}/{self.total_nodes} nodes")
        
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
                    log(f"Forwarded detections for frame {frame_number} to node {dest_node} via {next_hop}")
    
    def process_complete_frame_detection_buffer(self, frame_number):
        """Process detections once we have them from all nodes"""
        frame_data = self.detection_buffer[frame_number]
        
        # Verify we really have all nodes
        if len(frame_data) != self.total_nodes:
            log(f"Warning: Processing frame {frame_number} with incomplete data. " +
                f"Have {len(frame_data)}/{self.total_nodes} nodes")
            return
            
        # Collect all detections for this frame
        all_detections = {
            node_id: data['detections'] 
            for node_id, data in frame_data.items()
        }
        
        # Get timestamps for synchronization analysis
        timestamps = {
            node_id: data['timestamp'] 
            for node_id, data in frame_data.items()
        }
        
        # Calculate time differences for synchronization analysis
        base_time = min(timestamps.values())
        time_offsets = {
            node_id: timestamp - base_time 
            for node_id, timestamp in timestamps.items()
        }
        
        log(f"Processing complete frame {frame_number}")
        log(f"Time offsets between nodes (seconds): {time_offsets}")
        
        # Process the complete set of detections
        self.process_detections(
            all_detections,
            frame_number,
            timestamps
        )
        
        # Mark this frame as processed
        self.processed_frames.add(frame_number)
        
        # Clean up old frames from the buffer
        self.cleanup_old_frames(frame_number)

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
                self.total_nodes = len(self.routing_table)
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