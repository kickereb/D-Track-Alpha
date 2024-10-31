import threading
import time
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
        """
        self.node_id = node_id
        self.is_synchronized = False
        self.running = True
        self.expected_nodes = len(nodes)
        
        # Initialize nodes dictionary with provided nodes
        self.nodes: Dict[str, NodeInfo] = {}
        for nid, (ip, port) in nodes.items():
            self.nodes[nid] = NodeInfo(ip=ip, port=port, ready=False)
        
        # Threading components
        self.sync_lock = threading.Lock()
        self.sync_condition = threading.Condition(self.sync_lock)

    def _check_synchronization(self) -> bool:
        """Check if synchronization conditions are met"""
        with self.sync_lock:
            ready_count = sum(1 for info in self.nodes.values() if info.ready)
            if ready_count >= self.expected_nodes:
                log(f"Node {self.node_id}: All nodes synchronized ({ready_count}/{self.expected_nodes})")
                return True
            else:
                log(f"Node {self.node_id}: Waiting for nodes ({ready_count}/{self.expected_nodes})")
                return False

    def node_ready(self, node_id: str):
        """Mark a node as ready for synchronization."""
        with self.sync_lock:
            if node_id in self.nodes:
                self.nodes[node_id].ready = True
                ready_count = sum(1 for info in self.nodes.values() if info.ready)
                log(f"Node {self.node_id}: Node {node_id} ready. Total ready: {ready_count}/{self.expected_nodes}")
                
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
        with self.sync_lock:
            self.sync_condition.notify_all()

    def synchronize_start(self):
        """Initialize synchronization process"""
        self.node_ready(self.node_id)

    def get_active_nodes(self) -> Dict[str, Tuple[str, int]]:
        """Get all active nodes and their connection information."""
        with self.sync_lock:
            return {
                node_id: (info.ip, info.port)
                for node_id, info in self.nodes.items()
                if info.ready
            }