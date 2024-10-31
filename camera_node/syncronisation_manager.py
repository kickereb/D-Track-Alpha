import threading
import time
from typing import Dict, Tuple
from dataclasses import dataclass
from utils.logger import log
from utils.network import discover_dtrack_hosts, _scan_host

@dataclass
class NodeInfo:
    """Store information about connected nodes"""
    ip: str
    port: int
    ready: bool = False
    last_seen: float = 0.0

class SyncManager:
    def __init__(self, node_id: str, self_ip: str, self_port: int, discovery_service):
        """
        Initialize the SyncManager with automatic node discovery.
        
        Args:
            node_id (str): Unique identifier for this node
            self_ip (str): IP address of this node
            self_port (int): Port number of this node
        """
        self.node_id = node_id
        self.ip = self_ip
        self.is_synchronized = False
        self.running = True
        self.expected_nodes = 1  # Start with 1 (self), will be updated during discovery
        self.discovery_service = discovery_service
        
        # Node tracking
        self.nodes: Dict[str, NodeInfo] = {
            node_id: NodeInfo(ip=self_ip, port=self_port, ready=False, last_seen=time.time())
        }
        
        # Threading components
        self.sync_lock = threading.Lock()
        self.sync_condition = threading.Condition(self.sync_lock)
        self.discovery_thread = None
        self.timer_thread = None
        
        # Timer control
        self.timer_start = 0.0
        self.timer_running = False

    def discover_nodes(self) -> int:
        """
        Discover other dtrack nodes on the network and register them.
        
        Returns:
            int: Number of nodes discovered
        """
        try:
            neighbors = {}
            threads = []
            for i in range(1, 255):
                network_prefix = (".").join(self.ip.split(".")[:2])
                ip = f"{network_prefix}.{i}"
                thread = threading.Thread(
                    target=_scan_host, 
                    args=(ip, neighbors, 5000, self.ip)
                )
                threads.append(thread)
                thread.start()
            
            for thread in threads:
                thread.join()

            print(neighbors)
            exit(0)
            # discovered = self.discovery_service.send_discovery_request(neighbors)
            
            with self.sync_lock:
                new_nodes = False
                for node_id, (ip, port, status) in discovered.items():
                    if node_id != self.node_id:  # Don't register self
                        if self.register_node(node_id, ip, port):
                            new_nodes = True
                
                if new_nodes:
                    self._reset_timer()
                    
                self.expected_nodes = len(self.nodes)
                return len(discovered)
                
        except Exception as e:
            log(f"Node {self.node_id}: Error during node discovery: {e}")
            return 0

    def _periodic_discovery(self):
        """Periodically scan for new nodes"""
        while self.running and not self.is_synchronized:
            nodes_found = self.discover_nodes()
            log(f"Node {self.node_id}: Discovery found {nodes_found} nodes")
            time.sleep(2)  # Wait before next discovery attempt

    def register_node(self, node_id: str, ip: str, port: int) -> bool:
        """
        Register a new node in the network.
        
        Args:
            node_id (str): ID of the new node
            ip (str): IP address of the new node
            port (int): Port number of the new node
            
        Returns:
            bool: True if this is a new node, False if already registered
        """
        with self.sync_lock:
            if node_id not in self.nodes:
                self.nodes[node_id] = NodeInfo(ip=ip, port=port, last_seen=time.time())
                log(f"Node {self.node_id}: Registered new node {node_id} at {ip}:{port}")
                self._reset_timer()  # Reset timer for new node
                return True
            else:
                # Update last_seen timestamp for existing node
                self.nodes[node_id].last_seen = time.time()
                return False

    def _reset_timer(self):
        """Reset the 5-second timer"""
        log(f"Node {self.node_id}: Resetting 5-second timer")
        self.timer_start = time.time()
        self.timer_running = True

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

    def _timer_loop(self):
        """Main timer loop that enforces 5-second synchronization window"""
        while self.running and not self.is_synchronized:
            if self.timer_running:
                current_time = time.time()
                elapsed = current_time - self.timer_start
                
                if elapsed >= 5.0:  # 5-second window elapsed
                    with self.sync_lock:
                        # Remove stale nodes
                        stale_nodes = [
                            node_id for node_id, info in self.nodes.items()
                            if node_id != self.node_id and current_time - info.last_seen > 10.0
                        ]
                        
                        for node_id in stale_nodes:
                            self.node_disconnected(node_id)
                            
                        # Check if we're synchronized
                        if self._check_synchronization():
                            self.is_synchronized = True
                            self.sync_condition.notify_all()
                            break
                        else:
                            # Not synchronized after 5 seconds, keep timer running
                            self._reset_timer()
                
            time.sleep(0.1)  # Small sleep to prevent busy waiting

    def start_timer(self):
        """Start the synchronization timer thread"""
        # Perform initial discovery
        initial_nodes = self.discover_nodes()
        log(f"Node {self.node_id}: Initial discovery found {initial_nodes} nodes")
        
        # Start the timer
        self._reset_timer()
        
        # Start periodic discovery
        self.discovery_thread = threading.Thread(target=self._periodic_discovery, daemon=True)
        self.discovery_thread.start()
        
        # Start timer thread
        self.timer_thread = threading.Thread(target=self._timer_loop, daemon=True)
        self.timer_thread.start()

    def node_ready(self, node_id: str, ip: str, port: int):
        """Mark a node as ready for synchronization."""
        with self.sync_lock:
            if node_id not in self.nodes:
                self.register_node(node_id, ip, port)
            
            self.nodes[node_id].ready = True
            self.nodes[node_id].last_seen = time.time()
            
            ready_count = sum(1 for info in self.nodes.values() if info.ready)
            log(f"Node {self.node_id}: Node {node_id} ready. Total ready: {ready_count}/{self.expected_nodes}")

    def node_disconnected(self, node_id: str):
        """Handle node disconnection."""
        with self.sync_lock:
            if node_id in self.nodes:
                del self.nodes[node_id]
                self.expected_nodes -= 1
                log(f"Node {self.node_id}: Node {node_id} disconnected. Adjusting expected nodes to {self.expected_nodes}")
                self._reset_timer()  # Reset timer when a node disconnects

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
        
        if self.timer_thread and self.timer_thread.is_alive():
            self.timer_thread.join(timeout=1.0)
            
        if self.discovery_thread and self.discovery_thread.is_alive():
            self.discovery_thread.join(timeout=1.0)
            
        with self.sync_lock:
            self.sync_condition.notify_all()

    def synchronise_start(self):
        """Initialize synchronization process"""
        self.node_ready(self.node_id, self.nodes[self.node_id].ip, self.nodes[self.node_id].port)
        self.start_timer()

    def get_active_nodes(self) -> Dict[str, Tuple[str, int]]:
        """Get all active nodes and their connection information."""
        with self.sync_lock:
            return {
                node_id: (info.ip, info.port)
                for node_id, info in self.nodes.items()
                if info.ready
            }