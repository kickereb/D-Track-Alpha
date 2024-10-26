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
        self.frame_number = 0
        self.lock = threading.Lock()

        self.routing_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.routing_socket.bind((ip, port + 1))

        self.running = True

    def start(self):
        self.threads = [
            threading.Thread(target=self.listen_for_routing_updates, daemon=True),
            threading.Thread(target=self.send_periodic_routing_table_updates, daemon=True),
        ]
        
        for thread in self.threads:
            thread.start()

    def listen_for_routing_updates(self):
        """Dedicated thread for handling routing table updates"""
        self.routing_socket.settimeout(1.0)
        while self.running:
            try:
                data, addr = self.routing_socket.recvfrom(1024)  # Smaller buffer for routing updates
                routing_data = json.loads(data.decode())
                
                if routing_data.get('type') == 'routing_update':
                    self.update_routing_table(routing_data['routing_table'])
            except socket.timeout:
                continue
            except json.JSONDecodeError as e:
                log(f"Error decoding routing message: {e}")
            except Exception as e:
                log(f"Error in routing listener: {e}")

    def send_periodic_routing_table_updates(self):
        """Dedicated thread for periodically sending routing table to neighbour nodes"""
        for neighbor, (ip, port) in self.neighbors.items():
            self.send_routing_table(ip, port)
        time.sleep(5)  # Send updates every 5 seconds

    def send_routing_table(self, ip, port):
        """Send routing table updates to neighbors"""
        message = {
            'type': 'routing_update',
            'routing_table': self.routing_table
        }
        data = json.dumps(message).encode()
        self.routing_socket.sendto(data, (ip, port + 1))

    def update_routing_table(self, neighbor_table):
        with self.lock:
            updated = False
            for dest, (dist, _) in neighbor_table.items():
                if dest not in self.routing_table or dist + 1 < self.routing_table[dest][0]:
                    self.routing_table[dest] = (dist + 1, next(iter(neighbor_table)))
                    updated = True
            if updated:
                self.total_nodes = len(self.routing_table)
                log(f"Node {self.node_id} updated routing table:")
                self.print_routing_table()

    def print_routing_table(self):
        log(f"Routing table for node {self.node_id}:")
        for dest, (dist, next_hop) in self.routing_table.items():
            log(f"  Destination: {dest}, Distance: {dist}, Next Hop: {next_hop}")

    def stop(self):
        """Stop all routing manager threads"""
        log("Stopping routing table manager...")
        
        self.running = False  # Signal threads to stop
        
        # Wait for all threads to complete
        for thread in self.threads:
            thread.join(timeout=3.0)
            if thread.is_alive():
                log(f"Warning: Routing thread {thread.name} didn't shut down gracefully")
        
        self.threads.clear()