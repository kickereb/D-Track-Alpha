import threading
import numpy as np

from distributed_person_tracker import DistributedPersonTrackerStateMachine
from routing_table_manager import RoutingTableManager

from discovery_service import DiscoveryService
from syncronisation_manager import SyncManager
from utils.logger import log

class CameraNode:
    def __init__(self, node_id, ip, port, neighbors, camera_matrix: np.ndarray, dist_coeffs: np.ndarray):
        self.node_id = node_id
        self.ip = ip
        self.camera_matrix = camera_matrix
        self.dist_coeffs = dist_coeffs
        # self.routing_table_manager = RoutingTableManager(node_id, ip, port, neighbors)\
        # self.discovery_service = DiscoveryService(node_id, ip, port)
        neighbors[node_id] = (ip, port, 0)
        self.sync_manager = SyncManager(node_id, neighbors)
        
        # Initialise other attributes
        self.neighbors = neighbors
        self.routing_table = {node_id: (0, node_id)}
        self.frame_number = 0
        self.running = True
        self.threads = []

    def start(self):
        # threading.Thread(target=self.discovery_service.run_discovery_listener, daemon=True).start()
        # First synchronize all nodes
        self.sync_manager.synchronise_start()

        # Wait until synchronized before starting other threads
        if not self.sync_manager.wait_for_sync(timeout=10.0):  # 30 second total timeout
            log(f"Node {self.node_id}: Synchronization timeout")

        # Get the final list of active nodes
        active_nodes = self.sync_manager.get_active_nodes()
        log(f"Node {self.node_id}: Synchronized with nodes: {active_nodes}")

        now = datetime.datetime.now()
        log(now)
        
        # Initialize components with discovered nodes
        self.routing_table_manager = RoutingTableManager(
            self.node_id,
            self.sync_manager.nodes[self.node_id].ip,
            self.sync_manager.nodes[self.node_id].port,
            active_nodes
        )
        self.distributed_person_tracker = DistributedPersonTrackerStateMachine(self.node_id, 
                                                                                self.ip, 
                                                                                self.routing_table_manager, 
                                                                                self.camera_matrix, 
                                                                                self.dist_coeffs)

        # Start all necessary tasks a camera node needs to acheive in seperate threads
        self.threads = [
            # We need to handle continuous routing table updates to handle drop-outs or high network latency etc.
            # Potential extension task: Utilise network delay as route weighting.
            threading.Thread(target=self.routing_table_manager.start(), daemon=True),
            # A camera node also needs threads for the person tracker pipeline.
            threading.Thread(target=self.distributed_person_tracker.run_cycle_indefintely(), daemon=True),
        ]
        
        for thread in self.threads:
            thread.start()

    def stop(self):
        """Recursively stop all threads and cleanup resources"""
        log("Initiating camera node shutdown...")
        
        # Signal all components to stop by setting running to False
        self.running = False
        
        try:
            # Stop individual components and their child threads
            self.routing_table_manager.stop()
            self.distributed_person_tracker.stop()
            
            # Wait for main threads to complete
            for thread in self.threads:
                thread.join(timeout=5.0)
                if thread.is_alive():
                    log(f"Warning: Thread {thread.name} didn't shut down gracefully")
            
            self.threads.clear()
            
        except Exception as e:
            log(f"Error during shutdown: {e}")
        finally:
            log(f"Camera node {self.node_id} shutdown complete")