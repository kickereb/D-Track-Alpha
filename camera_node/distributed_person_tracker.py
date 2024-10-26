from dataclasses import dataclass
from typing import Dict, List, Optional
import threading
import time
import socket
import json
from enum import Enum, auto
from collections import defaultdict
from utils.logger import log

# Debug flag to control verbose logging
DEBUG = True

def _log_phase_separator(phase: str):
    """Helper function to create visually distinct phase separators in logs"""
    separator = "-" * 20
    log(f"\n{separator} {phase} PHASE {separator}")

@dataclass
class Detection:
    """
    Represents a single object detection in a frame
    
    Attributes:
        bbox: Bounding box coordinates [x1, y1, x2, y2]
        confidence: Detection confidence score (0-1)
        tracking_id: Unique identifier for tracking the object across frames
    """
    bbox: List[float]
    confidence: float
    tracking_id: int

@dataclass
class FrameData:
    """
    Contains all detection data for a single frame across all nodes
    
    Attributes:
        frame_number: Sequential identifier for the frame
        detections: Dictionary mapping node IDs to their respective detections
        start_time: Timestamp when frame processing began
    """
    frame_number: int
    detections: Dict[str, List[Detection]]  # node_id -> detections
    start_time: float

class CycleState(Enum):
    """
    Represents the different states in the frame processing cycle
    
    States:
        DETECT: Local detection creation and broadcasting
        COLLECT: Gathering detections from other nodes
        PROCESS: Processing all collected detections
    """
    DETECT = auto()
    COLLECT = auto()
    PROCESS = auto()
    COMPLETE = auto()

class DistributedPersonTrackerStateMachine:
    """
    Manages the distributed frame processing cycle across multiple nodes
    
    This class handles the synchronisation and processing of object detections
    across a network of nodes, maintaining temporal consistency and managing
    the collection and fusion of distributed detection data.

    The following phases of this state machine are as follows:
    
    DETECT PHASE - This phase will be the local detection of people within a frame.
    A node will take an image, run a person detection algorithm and finally convert 
    the bbox to world coordinates via camera matricies.

    COLLECT PHASE - Despite passively listening regardless of what state we are in,
    we still enter a collect phase waiting as long as possible until it
    receives as many local detections from the other nodes as possible until a 
    threshold time. Depending on what comes first (all detections or threshold),
    a node will then enter the PROCESS PHASE.

    PROCESS PHASE - This is where a node can start to fuse the local detections each
    node made into a global view given past tracks.
    """
    
    def __init__(self, node_id: str, ip: str, routing_table_manager, 
                 cycle_time_ms: int = 10000, 
                 collection_timeout_ms: int = 5000):
        """
        Initialise the state machine
        
        Args:
            node_id: Unique identifier for this node
            ip: IP address to bind the socket to
            routing_table_manager: Manager object for network routing
            cycle_time_ms: Total time allowed for one complete cycle
            collection_timeout_ms: Maximum time to wait for incoming detections
        """
        self.node_id = node_id
        self.routing_table_manager = routing_table_manager
        self.cycle_time = cycle_time_ms
        self.collection_timeout = collection_timeout_ms
        
        log(f"Initialising DistributedPersonTrackerStateMachine for node {node_id}")
        log(f"Cycle time: {self.cycle_time}ms, Collection timeout: {self.collection_timeout}ms")
        
        # Network setup
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((ip, routing_table_manager.port))
        self.socket.settimeout(0.01)
        log(f"Socket bound to {ip}:{routing_table_manager.port}")
        
        # Frame management
        self.frame_number = 0
        self.current_frame: Optional[FrameData] = None
        self.frame_lock = threading.Lock()
        self.cycle_start_time = 0.0
        
        # Early detection buffer
        self.early_detections = defaultdict(dict)
        self.early_detections_lock = threading.Lock()
        
        # State management
        self.state = CycleState.DETECT
        self.running = True
        
        # Start background listener
        self.listener_thread = threading.Thread(target=self._continuous_listener, daemon=True)
        self.listener_thread.start()
        log(f"DistributedPersonTrackerStateMachine initialised for node {node_id}")

    def run_cycle_indefintely(self):
        """Main cycle loop with strict timing controls"""
        log("Starting frame processing cycle")
        while self.running:
            self.cycle_start_time = time.time()*1000
            log(f"\n=================== NEW CYCLE {self.frame_number + 1} ===================")
            log(f"Cycle started at {time.strftime('%H:%M:%S', time.localtime(self.cycle_start_time))}")
        
            
            try:
                while self.state != CycleState.COMPLETE:
                    if self.state == CycleState.DETECT: 
                        self._handle_detection_phase()
                    elif self.state == CycleState.COLLECT:
                        self._handle_collection_phase()
                    elif self.state == CycleState.PROCESS:
                        self._handle_processing_phase()
                
                # Set state machine back to first phase
                self.state = CycleState.DETECT

                # Try to maintain cycle timing
                elapsed = time.time()*1000 - self.cycle_start_time
                if elapsed < self.cycle_time:
                    sleep_time = self.cycle_time - elapsed
                    log(f"Cycle completed early, sleeping for {sleep_time:.3f}ms\n\n")
                    time.sleep(sleep_time / 1000) # time.sleep() works in seconds
                else:
                    log(f"WARNING: Cycle exceeded target time by {elapsed - self.cycle_time:.3f}ms\n\n")
                
            except Exception as e:
                log(f"Error in cycle: {e}")

    def _handle_detection_phase(self):
        """
        Creates and broadcasts local detections, initialises new frame data,
        and transitions to collection phase
        """
        _log_phase_separator("DETECT")

        with self.frame_lock:
            self.frame_number += 1
            current_frame_num = self.frame_number
            log(f"Starting detection phase [frame {current_frame_num}]")
            
            self.current_frame = FrameData(
                frame_number=current_frame_num,
                detections={},
                start_time=time.time()*1000
            )
            
            # Create and store local detection
            local_detections = self._create_local_detection()
            self.current_frame.detections[self.node_id] = local_detections
            log(f"Created {len(local_detections)} local detections")
            
            # Process any early detections
            with self.early_detections_lock:
                if current_frame_num in self.early_detections:
                    early_count = len(self.early_detections[current_frame_num])
                    log(f"Processing {early_count} early detections")
                    for node_id, detections in self.early_detections[current_frame_num].items():
                        self.current_frame.detections[node_id] = detections
                    del self.early_detections[current_frame_num]
            
            # Broadcast to network
            self._broadcast_detections(local_detections)
            log("Local detections broadcast complete")
            
            self.state = CycleState.COLLECT
            log(f"Starting collection for frame {current_frame_num}")

    def _handle_collection_phase(self):
        """
        Collects detections with a hard cutoff at collection_timeout past cycle start
        """
        _log_phase_separator("COLLECT")

        if not self.current_frame:
            log("No current frame, reverting to DETECT state")
            self.state = CycleState.DETECT
            return
        
        log(f"Starting collection phase [frame {self.frame_number}]")

        collection_start = time.time()*1000
        time_since_cycle_start = (collection_start - self.cycle_start_time) * 1000
        remaining_time_ms = self.collection_timeout - time_since_cycle_start
        
        log(f"Starting collection phase with {remaining_time_ms:.1f}ms")
        
        if remaining_time_ms <= 0:
            log("WARNING: Hard cutoff already exceeded before collection started")
            self.state = CycleState.PROCESS
            return
        
        # Convert remaining time to seconds for sleep operations
        remaining_time = remaining_time_ms
        
        with self.routing_table_manager.lock:
            # Collection loop with hard cutoff
            while (time.time()*1000 - self.cycle_start_time < self.collection_timeout and  # Hard cutoff
                time.time()*1000 - collection_start < remaining_time and  # Remaining time
                not self._check_frame_complete()):  # Completion check
                time.sleep(0.001)  # Small sleep to prevent CPU spinning
                
            # Log collection results
            collection_time = time.time()*1000 - collection_start
            time_since_start = (time.time()*1000 - self.cycle_start_time)
            received = len(self.current_frame.detections)
            total = len(self.routing_table_manager.routing_table)
        
        log(f"\nCollection Results:")
        log(f"✓ Nodes reported: {received}/{total}")
        log(f"✓ Collection time: {collection_time:.3f}ms")
        log(f"✓ Cycle time used: {time_since_start:.1f}ms")
        
        if time_since_start >= self.collection_timeout:
            log(f"❌ WARNING: Collection timeout reached")
        
        self.state = CycleState.PROCESS

    def _handle_processing_phase(self):
        """
        Processes all collected detections to create a global view,
        performs cleanup, and prepares for next cycle
        """
        _log_phase_separator("PROCESS")
        
        log(f"Starting processing phase [frame {self.frame_number}]")
        if self.current_frame:
            received_nodes = len(self.current_frame.detections)
            total_nodes = len(self.routing_table_manager.routing_table)
            
            log(f"Processing frame {self.frame_number} with {received_nodes}/{total_nodes} nodes")
            
            # Process detections
            process_start = time.time()*1000
            self._process_frame(self.current_frame)
            log(f"Frame processing took {time.time()*1000 - process_start:.3f}ms")
            
            # Cleanup old frame data
            with self.early_detections_lock:
                old_frames = [f for f in self.early_detections.keys() if f <= self.frame_number]
                if old_frames:
                    log(f"Cleaning up {len(old_frames)} old frames from buffer")
                for frame in old_frames:
                    del self.early_detections[frame]
            
            self.current_frame = None
            self.state = CycleState.COMPLETE
            log("Processing phase complete")

    def _create_local_detection(self) -> List[Detection]:
        """Create detection for current frame"""
        return [Detection(
            bbox=[0, 0, 100, 100],  # Placeholder detection
            confidence=70,
            tracking_id=self.frame_number
        )]

    def _broadcast_detections(self, detections: List[Detection]):
        """Send detections to all other nodes"""
        message = {
            'type': 'detection',
            'frame_number': self.frame_number,
            'source_node': self.node_id,
            'timestamp': time.time()*1000,
            'detections': [d.__dict__ for d in detections]
        }

        for dest_node in self.routing_table_manager.routing_table:
            if dest_node == self.node_id:
                continue
                
            dist, next_hop = self.routing_table_manager.routing_table[dest_node]
            if next_hop in self.routing_table_manager.neighbors:
                next_hop_ip, next_hop_port = self.routing_table_manager.neighbors[next_hop]
                try:
                    msg_data = json.dumps(message).encode()
                    self.socket.sendto(msg_data, (next_hop_ip, next_hop_port))
                except Exception as e:
                    log(f"Error sending to {dest_node}: {e}")

    def _check_frame_complete(self) -> bool:
        """Check if we have detections from all nodes"""
        if not self.current_frame:
            return False
            
        return len(self.current_frame.detections) == len(self.routing_table_manager.routing_table)

    def _process_frame(self, frame: FrameData):
        """Process all detections to create global view"""
        # TODO: Implement global view creation logic here
        for node_id, detections in frame.detections.items():
            for detection in detections:
                log(f"Node {node_id} detection: {detection}")


    def _continuous_listener(self):
        """
        Background thread that continuously listens for incoming detection messages.
        Handles message parsing and routing to appropriate handlers.
        """
        log("Starting continuous listener thread")
        while self.running:
            try:
                data, addr = self.socket.recvfrom(4096)
                message = json.loads(data.decode())
                
                if message['type'] == 'detection':
                    log(f"Received detection message from {addr}")
                    self._handle_incoming_detection(message)
                    
            except socket.timeout:
                continue
            except json.JSONDecodeError as e:
                log(f"Error decoding message: {e}")
            except Exception as e:
                log(f"Error in listener: {e}")
        log("Continuous listener thread stopped")

    def _handle_incoming_detection(self, message: dict):
        """
        Process an incoming detection message and store it appropriately
        
        Args:
            message: Dictionary containing detection data and metadata
        """
        received_frame = message['frame_number']
        source_node = message['source_node']
        detections = [Detection(**d) for d in message['detections']]
        
        log(f"Processing detection from node {source_node} for frame {received_frame}")
        
        with self.frame_lock:
            current_frame_num = self.frame_number

        # Handle current frame detections
        if received_frame == current_frame_num and self.state == CycleState.COLLECT:
            if self.current_frame:
                self.current_frame.detections[source_node] = detections
                log(f"Added detection from {source_node} for current frame {current_frame_num}")
                log(f"Current frame now has {len(self.current_frame.detections)} node detections")
        
        # Handle future frame detections
        elif received_frame == current_frame_num + 1:
            with self.early_detections_lock:
                self.early_detections[received_frame][source_node] = detections
                log(f"Stored early detection from {source_node} for frame {received_frame}")

    def stop(self):
        """Gracefully stop the cycle manager and cleanup resources"""
        log("Stopping DistributedPersonTrackerStateMachine")
        self.running = False
        self.listener_thread.join(timeout=1.0)
        self.socket.close()
        log(f"DistributedPersonTrackerStateMachine for node {self.node_id} stopped")