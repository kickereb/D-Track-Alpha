import threading
import time
import json
import socket
from utils.logger import log

# Debug flags
DEBUG = {
    'NETWORK': False,     # Network operations (send/receive)
    'ROUTING': False,     # Routing table updates and calculations
    'THREADS': False,     # Thread operations and status
    'ALL': False         # Enable all debug output
}

def debug_log(category: str, message: str):
    """
    Debug logging utility that respects debug flags
    
    Args:
        category: The debug category ('NETWORK', 'ROUTING', 'THREADS')
        message: The message to log
    """
    if DEBUG['ALL'] or DEBUG.get(category, False):
        log(f"[DEBUG:{category}] {message}")

class RoutingTableManager:
    def __init__(self, node_id, ip, port, neighbors):
        self.node_id = node_id
        self.ip = ip
        self.port = port
        self.neighbors = neighbors
        self.routing_table = {node_id: (0, node_id)}
        self.total_nodes = 1
        self.frame_number = 0
        self.lock = threading.Lock()

        debug_log('THREADS', f"Initializing RoutingTableManager for node {node_id}")
        debug_log('NETWORK', f"Setting up socket on {ip}:{port+1}")

        self.routing_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.routing_socket.bind((ip, port + 1))

        self.running = True
        self.threads = []

        debug_log('ROUTING', f"Initial routing table for node {node_id}: {self.routing_table}")
        debug_log('ROUTING', f"Initial neighbors for node {node_id}: {self.neighbors}")

    def start(self):
        debug_log('THREADS', f"Starting threads for node {self.node_id}")
        
        self.threads = [
            threading.Thread(target=self.listen_for_routing_updates, daemon=True, name=f"{self.node_id}_RoutingListener"),
            threading.Thread(target=self.send_periodic_routing_table_updates, daemon=True, name=f"{self.node_id}_RoutingBroadcaster")
        ]
        
        for thread in self.threads:
            debug_log('THREADS', f"Starting thread {thread.name}")
            thread.start()

        debug_log('NETWORK', f"Broadcasting initial routing table for node {self.node_id}")
        self.broadcast_routing_table()
        log(f"Node {self.node_id} started and broadcast initial routing table")

    def listen_for_routing_updates(self):
        self.routing_socket.settimeout(1.0)
        debug_log('THREADS', f"Routing listener started for node {self.node_id}")
        
        while self.running:
            try:
                debug_log('NETWORK', f"Node {self.node_id} waiting for routing updates")
                data, addr = self.routing_socket.recvfrom(1024)
                debug_log('NETWORK', f"Node {self.node_id} received data from {addr}")
                
                routing_data = json.loads(data.decode())
                
                if routing_data.get('type') == 'routing_update':
                    sender_table = routing_data['routing_table']
                    debug_log('ROUTING', f"Node {self.node_id} processing routing update:")
                    debug_log('ROUTING', f"Sender's routing table: {json.dumps(sender_table, indent=2)}")
                    
                    if self.update_routing_table(sender_table):
                        debug_log('NETWORK', f"Node {self.node_id} broadcasting updated table")
                        self.broadcast_routing_table()
                    
            except socket.timeout:
                debug_log('NETWORK', f"Listen timeout on node {self.node_id}")
                continue
            except json.JSONDecodeError as e:
                log(f"Error decoding routing message: {e}")
            except Exception as e:
                log(f"Error in routing listener: {e}")

    def send_periodic_routing_table_updates(self):
        debug_log('THREADS', f"Periodic update thread started for node {self.node_id}")
        
        while self.running:
            try:
                debug_log('NETWORK', f"Node {self.node_id} sending periodic update")
                self.broadcast_routing_table()
                time.sleep(5)
            except Exception as e:
                log(f"Error in periodic update: {e}")

    def broadcast_routing_table(self):
        with self.lock:
            current_table = dict(self.routing_table)
        
        debug_log('ROUTING', f"Node {self.node_id} preparing broadcast with table: {current_table}")
        
        message = {
            'type': 'routing_update',
            'routing_table': current_table
        }
        data = json.dumps(message).encode()
        
        for neighbor_id, (ip, port, _) in self.neighbors.items():
            try:
                debug_log('NETWORK', 
                    f"Node {self.node_id} sending to neighbor {neighbor_id} at {ip}:{port+1}")
                self.routing_socket.sendto(data, (ip, port + 1))
                debug_log('NETWORK', f"Successfully sent to {neighbor_id}")
            except Exception as e:
                log(f"Error sending to neighbor {neighbor_id}: {e}")

    def update_routing_table(self, neighbor_table):
        with self.lock:
            updated = False
            neighbor_node = next(iter(neighbor_table))
            
            debug_log('ROUTING', 
                f"Node {self.node_id} processing update from {neighbor_node}")
            debug_log('ROUTING', 
                f"Current table: {json.dumps(self.routing_table, indent=2)}")
            debug_log('ROUTING', 
                f"Neighbor table: {json.dumps(neighbor_table, indent=2)}")

            # Handle direct neighbor route
            if neighbor_node in self.neighbors:
                _, _, direct_distance = self.neighbors[neighbor_node]
                if (neighbor_node not in self.routing_table or 
                    direct_distance < self.routing_table[neighbor_node][0]):
                    old_route = self.routing_table.get(neighbor_node, None)
                    self.routing_table[neighbor_node] = (direct_distance, neighbor_node)
                    updated = True
                    debug_log('ROUTING', 
                        f"Updated direct route to {neighbor_node}: {old_route} -> {self.routing_table[neighbor_node]}")

            # Process routes through neighbor
            for dest, (dist, next_hop) in neighbor_table.items():
                total_distance = dist + self.neighbors[neighbor_node][2]
                
                if (dest not in self.routing_table or 
                    total_distance < self.routing_table[dest][0]):
                    old_route = self.routing_table.get(dest, None)
                    self.routing_table[dest] = (total_distance, neighbor_node)
                    updated = True
                    debug_log('ROUTING', 
                        f"Updated route to {dest}: {old_route} -> {self.routing_table[dest]}")

            if updated:
                self.total_nodes = len(self.routing_table)
                debug_log('ROUTING', f"Node {self.node_id} routing table updated:")
                self.print_routing_table()
                return True
            
            debug_log('ROUTING', "No updates needed for routing table")
            return False

    def print_routing_table(self):
        debug_log('ROUTING', f"\n=== Routing table for node {self.node_id} ===")
        debug_log('ROUTING', f"Total nodes known: {self.total_nodes}")
        for dest, (dist, next_hop) in sorted(self.routing_table.items()):
            debug_log('ROUTING', f"  → {dest}: distance={dist}, next_hop={next_hop}")
        debug_log('ROUTING', "=" * 40)

    def stop(self):
        debug_log('THREADS', f"Initiating shutdown for node {self.node_id}")
        
        self.running = False
        
        for thread in self.threads:
            debug_log('THREADS', f"Stopping thread {thread.name}")
            thread.join(timeout=3.0)
            if thread.is_alive():
                log(f"Warning: Thread {thread.name} didn't shutdown gracefully")
        
        debug_log('NETWORK', f"Closing routing socket for node {self.node_id}")
        self.routing_socket.close()
        debug_log('THREADS', f"Routing table manager stopped for node {self.node_id}")