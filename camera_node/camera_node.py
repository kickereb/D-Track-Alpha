import threading

from distributed_person_tracker import DistributedPersonTracker
from routing_table_manager import RoutingTableManager

from syncronisation_manager import SyncManager
from utils.logger import log

class CameraNode:
    def __init__(self, node_id, ip, port, neighbors):
        self.node_id = node_id
        self.distributed_person_tracker = DistributedPersonTracker(node_id, ip, port)
        self.routing_table_manager = RoutingTableManager(node_id, ip, port, neighbors)
        # self.sync_manager = SyncManager(self.network_manager, len(neighbors) + 1)

        # Camera calibration parameters
        # TODO: Initialise matricies properly
        self.camera_matrix = 0  # 3x3 intrinsic matrix
        self.dist_coeffs = 0      # Distortion coefficients
        self.rotation_matrix = 0  # 3x3 rotation matrix (world to camera)
        self.translation_vector = 0  # 3x1 translation vector
        
        # Initialise other attributes
        self.neighbors = neighbors
        self.routing_table = {node_id: (0, node_id)}
        self.frame_number = 0
        self.running = True

    def start(self):
        # TODO: Syncronise nodes at initialisation.
        # First synchronise all of the nodes by waiting until everyone sends a ready signal
        # self.sync_manager.synchronise_start()
        # # Wait until synchronised before starting other threads
        # with self.sync_manager.sync_condition:
        #     while not self.is_synchronized:
        #         self.sync_condition.wait()

        # Start all necessary tasks a camera node needs to acheive in seperate threads
        self.threads = [
            # We need to handle continuous routing table updates to handle drop-outs or high network latency etc.
            # Potential extension task: Utilise network delay as route weighting.
            threading.Thread(target=self.routing_table_manager.start(), daemon=True),
            # A camera node also needs threads for the person tracker pipeline.
            threading.Thread(target=self.distributed_person_tracker.start(), daemon=True),
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