import threading
import time
import socket
import json
from utils.logger import log

class DistributedPersonTracker:
    def __init__(self, node_id, ip, port):
        self.port = port
        self.detection_buffer = {}
        self.processed_frames = set()
        self.detection_buffer_lock = threading.Lock()
        self.latest_processed_frame = 0
        self.frame_process_condition = threading.Condition()

        self.detection_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.detection_socket.bind((ip, port))

        self.running = True

    def start(self):
        self.threads = [
            # A camera node also needs to passively listen for detections sent for a given frame from another node.
            threading.Thread(target=self.listen_for_detections, daemon=True),
            # Another thread is needed for when a frame is filled with detections from all available camera nodes.
            # threading.Thread(target=self.process_frames_continuously, daemon=True),
        ]
        
        for thread in self.threads:
            thread.start()

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
        
        # Calculate time differences for synchronisation analysis
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


    def is_frame_complete(self, frame_number, total_nodes):
        return (frame_number not in self.processed_frames and 
                len(self.detection_buffer.get(frame_number, {})) == total_nodes)

    def store_detection(self, frame_number, node_id, detections, timestamp):
        with self.detection_buffer_lock:
            if frame_number not in self.detection_buffer:
                self.detection_buffer[frame_number] = {}
            
            self.detection_buffer[frame_number][node_id] = {
                'detections': detections,
                'timestamp': timestamp
            }

    def process_complete_frame(self, frame_number, process_callback):
        with self.detection_buffer_lock:
            if frame_number in self.processed_frames:
                return

            frame_data = self.detection_buffer[frame_number]
            process_callback(frame_data, frame_number)
            
            self.processed_frames.add(frame_number)
            self.latest_processed_frame = max(self.latest_processed_frame, frame_number)
            self.cleanup_old_frames()

    def cleanup_old_frames(self, buffer_size=30):
        with self.detection_buffer_lock:
            cutoff_frame = self.latest_processed_frame - buffer_size
            frames_to_remove = [
                frame for frame in self.detection_buffer.keys()
                if frame < cutoff_frame
            ]
            
            for frame in frames_to_remove:
                del self.detection_buffer[frame]
                if frame in self.processed_frames:
                    self.processed_frames.remove(frame)

    def stop(self):
        """Stop all tracker threads"""
        log("Stopping person tracker...")
        
        self.running = False  # Signal threads to stop
        
        # Wait for all threads to complete
        for thread in self.threads:
            thread.join(timeout=3.0)
            if thread.is_alive():
                log(f"Warning: Tracker thread {thread.name} didn't shut down gracefully")
        
        self.threads.clear()