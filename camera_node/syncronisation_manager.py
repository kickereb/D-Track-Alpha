import threading
import time
import socket
import json
from typing import Dict, Tuple
from dataclasses import dataclass
from utils.logger import log

@dataclass
class NodeInfo:
    """Store information about connected nodes"""
    ip: str
    port: int
    ready: bool = False

class SyncManager:
    def __init__(self, node_id: str, nodes: Dict[str, Tuple[str, int]]):
        """
        Initialize the SyncManager with a predefined set of nodes.
        
        Args:
            node_id (str): Unique identifier for this node
            nodes (Dict[str, Tuple[str, int]]): Dictionary of node_id -> (ip, port) for all nodes
            listen_port (int): Port to listen for status updates
        """
        self.node_id = node_id
        self.listen_port = 5000
        self.is_synchronized = False
        self.running = True
        self.expected_nodes = len(nodes)
        
        # Initialize nodes dictionary with provided nodes
        self.nodes: Dict[str, NodeInfo] = {}
        for nid, (ip, port, _) in nodes.items():
            self.nodes[nid] = NodeInfo(ip=ip, port=port, ready=False)
        
        # Threading components
        self.sync_lock = threading.Lock()
        self.sync_condition = threading.Condition(self.sync_lock)
        
        # Network components
        self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.listen_socket.bind(('0.0.0.0', self.listen_port))
        self.listen_socket.settimeout(1.0)  # 1 second timeout for clean shutdown
        self.listener_thread = threading.Thread(target=self._listen_for_updates, daemon=True)

    def _check_synchronization(self) -> bool:
        """Check if synchronization conditions are met"""
        with self.sync_lock:
            ready_count = sum(1 for info in self.nodes.values() if info.ready)
            log(f"ready count: {ready_count}")
            if ready_count >= self.expected_nodes:
                log(f"Node {self.node_id}: All nodes synchronized ({ready_count}/{self.expected_nodes})")
                return True
            else:
                log(f"Node {self.node_id}: Waiting for nodes ({ready_count}/{self.expected_nodes})")
                return False

    def _broadcast_status(self, status: bool):
        """Broadcast ready status to all other nodes."""
        message = {
            'node_id': self.node_id,
            'status': status
        }
        encoded_message = json.dumps(message).encode('utf-8')
        
        for node_id, info in self.nodes.items():
            if node_id != self.node_id:  # Don't send to self
                try:
                    log(f"sending broadcast message to {self.node_id} with info {info}")
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sock.sendto(encoded_message, (info.ip, info.port))
                except Exception as e:
                    log(f"Node {self.node_id}: Error sending status to {node_id}: {e}")
                finally:
                    sock.close()

    def _listen_for_updates(self):
        """Listen for status updates from other nodes."""
        while self.running:
            try:
                data, addr = self.listen_socket.recvfrom(1024)
                message = json.loads(data.decode('utf-8'))
                
                node_id = message.get('node_id')
                status = message.get('status')
                
                if node_id and status is not None:
                    if status:
                        self.node_ready(node_id)
                    else:
                        self.node_disconnected(node_id)
                        
            except socket.timeout:
                continue  # Timeout allows checking self.running
            except Exception as e:
                log(f"Node {self.node_id}: Error receiving status update: {e}")

    def node_ready(self, node_id: str):
        """Mark a node as ready for synchronization."""
        log(f"marking node {node_id} as ready")
        if node_id in self.nodes or node_id == self.node_id:
            self.nodes[node_id].ready = True
            
            if self._check_synchronization():
                self.is_synchronized = True
                self.sync_condition.notify_all()

    def node_disconnected(self, node_id: str):
        """Handle node disconnection."""
        with self.sync_lock:
            if node_id in self.nodes:
                del self.nodes[node_id]
                self.expected_nodes -= 1
                log(f"Node {self.node_id}: Node {node_id} disconnected. Adjusting expected nodes to {self.expected_nodes}")
                self._broadcast_status(False)

    def wait_for_sync(self, timeout: float = None) -> bool:
        """Wait for synchronization to complete."""
        with self.sync_condition:
            if timeout is not None:
                end_time = time.time() + timeout
                while not self.is_synchronized and time.time() < end_time:
                    remaining = end_time - time.time()
                    if remaining <= 0:
                        break
                    self.sync_condition.wait(timeout=remaining)
            else:
                while not self.is_synchronized:
                    self.sync_condition.wait()
                    
            return self.is_synchronized

    def stop(self):
        """Stop the synchronization manager and cleanup resources"""
        self.running = False
        
        # Send disconnect status to other nodes
        self._broadcast_status(False)
        
        # Stop listener thread
        if self.listener_thread and self.listener_thread.is_alive():
            self.listener_thread.join(timeout=1.0)
            
        # Close socket
        if self.listen_socket:
            self.listen_socket.close()
            
        with self.sync_lock:
            self.sync_condition.notify_all()

    def synchronise_start(self):
        """Initialize synchronization process"""
        # Start listening for updates from other nodes
        self.listener_thread.start()
        
        # Mark self as ready and broadcast status
        self.node_ready(self.node_id)
        self._broadcast_status(True)

    def get_active_nodes(self) -> Dict[str, Tuple[str, int]]:
        """Get all active nodes and their connection information."""
        with self.sync_lock:
            return {
                node_id: (info.ip, info.port)
                for node_id, info in self.nodes.items()
                if info.ready
            }