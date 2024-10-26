import threading
import time
import json
import socket
from utils.logger import log

class RoutingTableManager:
    def __init__(self, node_id, ip, port, neighbors):
        self.node_id = node_id
        self.ip = ip
        self.port = port
        self.neighbors = neighbors  # Dictionary of neighbor_id: (ip, port, distance)
        self.routing_table = {node_id: (0, node_id)}  # Format: destination: (distance, next_hop)
        self.total_nodes = 1
        self.frame_number = 0
        self.lock = threading.Lock()

        self.routing_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.routing_socket.bind((ip, port + 1))

        self.running = True
        self.threads = []

    def start(self):
        """Start the routing manager threads and send initial updates"""
        self.threads = [
            threading.Thread(target=self.listen_for_routing_updates, daemon=True, name="RoutingListener"),
            threading.Thread(target=self.send_periodic_routing_table_updates, daemon=True, name="RoutingBroadcaster")
        ]
        
        for thread in self.threads:
            thread.start()

        # Send immediate initial routing update to all neighbors
        self.broadcast_routing_table()
        log(f"Node {self.node_id} started and broadcast initial routing table")

    def listen_for_routing_updates(self):
        """Dedicated thread for handling routing table updates"""
        self.routing_socket.settimeout(1.0)
        log(f"Node {self.node_id} started listening for routing updates")
        
        while self.running:
            try:
                data, addr = self.routing_socket.recvfrom(1024)
                routing_data = json.loads(data.decode())
                
                if routing_data.get('type') == 'routing_update':
                    sender_table = routing_data['routing_table']
                    log(f"Node {self.node_id} received routing update from {addr}")
                    log(f"Received table: {sender_table}")
                    
                    self.update_routing_table(sender_table)
                    # Broadcast updates immediately when we receive new information
                    self.broadcast_routing_table()
            except socket.timeout:
                continue
            except json.JSONDecodeError as e:
                log(f"Error decoding routing message: {e}")
            except Exception as e:
                log(f"Error in routing listener: {e}")

    def send_periodic_routing_table_updates(self):
        """Dedicated thread for periodically sending routing table to neighbour nodes"""
        log(f"Node {self.node_id} started periodic routing updates")
        while self.running:
            try:
                self.broadcast_routing_table()
                time.sleep(5)  # Send updates every 5 seconds
            except Exception as e:
                log(f"Error in periodic update: {e}")

    def broadcast_routing_table(self):
        """Broadcast routing table to all neighbors"""
        with self.lock:
            current_table = dict(self.routing_table)  # Make a copy under lock
        
        message = {
            'type': 'routing_update',
            'routing_table': current_table
        }
        data = json.dumps(message).encode()
        
        for neighbor_id, (ip, port, _) in self.neighbors.items():
            try:
                log(f"Node {self.node_id} sending routing table to neighbor {neighbor_id} at {ip}:{port+1}")
                self.routing_socket.sendto(data, (ip, port + 1))
            except Exception as e:
                log(f"Error sending to neighbor {neighbor_id}: {e}")

    def update_routing_table(self, neighbor_table):
        """Update routing table with new information from a neighbor"""
        with self.lock:
            updated = False
            neighbor_node = next(iter(neighbor_table))  # Get the neighbor's node ID
            
            log(f"Node {self.node_id} processing update from {neighbor_node}")
            log(f"Current table: {self.routing_table}")
            log(f"Neighbor table: {neighbor_table}")

            # First, update the direct route to the neighbor
            if neighbor_node in self.neighbors:
                _, _, direct_distance = self.neighbors[neighbor_node]
                if (neighbor_node not in self.routing_table or 
                    direct_distance < self.routing_table[neighbor_node][0]):
                    self.routing_table[neighbor_node] = (direct_distance, neighbor_node)
                    updated = True
                    log(f"Updated direct route to {neighbor_node}")

            # Then process routes to other nodes through this neighbor
            for dest, (dist, next_hop) in neighbor_table.items():
                total_distance = dist + self.neighbors[neighbor_node][2]  # Add distance to neighbor
                
                if (dest not in self.routing_table or 
                    total_distance < self.routing_table[dest][0]):
                    self.routing_table[dest] = (total_distance, neighbor_node)
                    updated = True
                    log(f"Updated route to {dest} through {neighbor_node}")

            if updated:
                self.total_nodes = len(self.routing_table)
                log(f"Node {self.node_id} updated routing table:")
                self.print_routing_table()
                return True
            return False

    def print_routing_table(self):
        """Print current routing table state"""
        log(f"\n=== Routing table for node {self.node_id} ===")
        log(f"Total nodes known: {self.total_nodes}")
        for dest, (dist, next_hop) in sorted(self.routing_table.items()):
            log(f"  → {dest}: distance={dist}, next_hop={next_hop}")
        log("=" * 40)

    def stop(self):
        """Stop all routing manager threads"""
        log(f"Stopping routing table manager for node {self.node_id}...")
        
        self.running = False
        
        for thread in self.threads:
            thread.join(timeout=3.0)
            if thread.is_alive():
                log(f"Warning: Thread {thread.name} didn't shutdown gracefully")
        
        self.routing_socket.close()
        log(f"Routing table manager for node {self.node_id} stopped")