import threading
import time
import json
from utils.logger import log

class SyncManager:
    def __init__(self, network_manager, total_nodes):
        self.network_manager = network_manager
        self.total_nodes = total_nodes
        self.ready_nodes = set()
        self.sync_lock = threading.Lock()
        self.sync_condition = threading.Condition()
        self.is_synchronized = False
        self.start_frame = 0

    def synchronise_start(self):
        """Synchronise start frame with all nodes"""
        # Start listening for sync messages
        threading.Thread(target=self.listen_for_sync, daemon=True).start()
        
        # Send ready message to all nodes
        self.broadcast_ready()
        
        # Wait until we have all nodes ready
        while not self.is_synchronized:
            with self.sync_lock:
                total_nodes = self.get_total_nodes()
                if len(self.ready_nodes) == total_nodes:
                    # All nodes are ready, broadcast start message
                    self.broadcast_start()
                    self.is_synchronized = True
                    with self.sync_condition:
                        self.sync_condition.notify_all()
            time.sleep(0.1)

    def broadcast_ready(self):
        message = {
            'type': 'sync',
            'status': 'ready',
            'source_node': self.network_manager.node_id,
            'timestamp': time.time()
        }
        self.network_manager.broadcast_sync_message(message)
    
    def broadcast_start(self):
        """Broadcast start message to all nodes"""
        start_frame = int(time.time() * 10)  # Use timestamp to ensure all nodes start at same frame
        message = {
            'type': 'sync',
            'status': 'start',
            'source_node': self.node_id,
            'start_frame': start_frame,
            'timestamp': time.time()
        }
        
        self.broadcast_sync_message(message)
        self.start_frame = start_frame
        self.frame_number = start_frame
        log(f"Broadcasted start message. Beginning at frame {start_frame}")

    def broadcast_sync_message(self, message):
        """Send sync message to all nodes in routing table"""
        json_data = json.dumps(message).encode()
        
        for dest_node in self.routing_table:
            if dest_node == self.node_id:
                continue
                
            dist, next_hop = self.routing_table[dest_node]
            if next_hop not in self.neighbors:
                continue
                
            next_hop_ip, next_hop_port = self.neighbors[next_hop]
            try:
                self.sync_socket.sendto(json_data, (next_hop_ip, next_hop_port + 2))
            except Exception as e:
                log(f"Error sending sync message to node {dest_node}: {e}")

    def handle_sync_message(self, message):
        if message['status'] == 'ready':
            with self.sync_lock:
                self.ready_nodes.add(message['source_node'])
                if len(self.ready_nodes) == self.total_nodes:
                    self.broadcast_start()
        elif message['status'] == 'start':
            self.start_frame = message['start_frame']
            self.is_synchronized = True
            with self.sync_condition:
                self.sync_condition.notify_all()
