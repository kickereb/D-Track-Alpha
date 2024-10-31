import threading
import time
from typing import Set
from utils.logger import log

class SyncManager:
    def __init__(self, node_id: str, expected_nodes: int):
        """
        Initialise the SyncManager.
        
        Args:
            node_id (str): Unique identifier for this node
            expected_nodes (int): Expected number of nodes in the network
        """
        self.node_id = node_id
        self.expected_nodes = expected_nodes
        self.ready_nodes: Set[str] = set()
        self.is_synchronized = False
        self.running = True
        
        # Threading components
        self.sync_lock = threading.Lock()
        self.sync_condition = threading.Condition(self.sync_lock)
        self.timer_reset_event = threading.Event()
        self.timer_thread = None

    def start_timer(self):
        """Start the synchronisation timer thread"""
        self.timer_thread = threading.Thread(target=self._timer_loop, daemon=True)
        self.timer_thread.start()

    def _timer_loop(self):
        """Main timer loop that checks for synchronisation conditions"""
        while self.running:
            # Wait for 5 seconds or until reset event is triggered
            self.timer_reset_event.wait(timeout=5.0)
            
            with self.sync_lock:
                if len(self.ready_nodes) >= self.expected_nodes:
                    log(f"Node {self.node_id}: All nodes synchronized")
                    self.is_synchronized = True
                    self.sync_condition.notify_all()
                    break
                else:
                    log(f"Node {self.node_id}: Still waiting for {self.expected_nodes - len(self.ready_nodes)} nodes")
                    
            # Clear the reset event for the next iteration
            self.timer_reset_event.clear()

    def node_ready(self, node_id: str):
        """
        Mark a node as ready for synchronization.
        
        Args:
            node_id (str): ID of the node that is ready
        """
        with self.sync_lock:
            self.ready_nodes.add(node_id)
            log(f"Node {self.node_id}: Node {node_id} ready. Total ready: {len(self.ready_nodes)}/{self.expected_nodes}")
            
            # Reset timer when a new node connects
            self.timer_reset_event.set()

    def node_disconnected(self, node_id: str):
        """
        Handle node disconnection.
        
        Args:
            node_id (str): ID of the disconnected node
        """
        with self.sync_lock:
            if node_id in self.ready_nodes:
                self.ready_nodes.remove(node_id)
                self.expected_nodes -= 1
                log(f"Node {self.node_id}: Node {node_id} disconnected. Adjusting expected nodes to {self.expected_nodes}")

    def wait_for_sync(self, timeout: float = None) -> bool:
        """
        Wait for synchronization to complete.
        
        Args:
            timeout (float, optional): Maximum time to wait in seconds
            
        Returns:
            bool: True if synchronized, False if timeout occurred
        """
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
        self.timer_reset_event.set()  # Wake up timer thread
        
        if self.timer_thread and self.timer_thread.is_alive():
            self.timer_thread.join(timeout=1.0)
            
        with self.sync_lock:
            self.sync_condition.notify_all()  # Wake up any waiting threads

    def synchronise_start(self):
        """Initialize synchronization process"""
        self.node_ready(self.node_id)  # Mark self as ready
        self.start_timer()  # Start the timer thread