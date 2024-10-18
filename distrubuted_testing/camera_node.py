import threading
import time
import socket
import json
import select
import sys
import queue


def log(message):
    print(f"[{time.strftime('%H:%M:%S')}] {message}")
    sys.stdout.flush()

class CameraNode:
    def __init__(self, node_id, ip, port, neighbors):
        self.node_id = node_id
        self.ip = ip
        self.port = port
        self.neighbors = neighbors  # Dictionary of neighbor_id: (ip, port, distance)
        self.routing_table = {node_id: (0, node_id)}  # Format: destination: (distance, next_hop)
        self.lock = threading.Lock()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((ip, port))
        self.running = True
        self.command_queue = queue.Queue()

    def start(self):
        threading.Thread(target=self.listen_for_updates, daemon=True).start()
        threading.Thread(target=self.send_periodic_updates, daemon=True).start()
        threading.Thread(target=self.process_commands, daemon=True).start()

    def listen_for_updates(self):
        self.socket.settimeout(1.0)
        while self.running:
            try:
                data, addr = self.socket.recvfrom(1024)
                neighbor_table = json.loads(data.decode())
                self.update_routing_table(neighbor_table)
            except socket.timeout:
                continue
            except Exception as e:
                log(f"Error in listen_for_updates: {e}")

    def send_periodic_updates(self):
        while self.running:
            for neighbor, (ip, port) in self.neighbors.items():
                self.send_routing_table(ip, port)
            time.sleep(5)  # Send updates every 5 seconds

    def send_routing_table(self, ip, port):
        data = json.dumps(self.routing_table).encode()
        self.socket.sendto(data, (ip, port))

    def update_routing_table(self, neighbor_table):
        with self.lock:
            updated = False
            for dest, (dist, _) in neighbor_table.items():
                if dest not in self.routing_table or dist + 1 < self.routing_table[dest][0]:
                    self.routing_table[dest] = (dist + 1, next(iter(neighbor_table)))
                    updated = True
            if updated:
                log(f"Node {self.node_id} updated routing table:")
                self.print_routing_table()

    def print_routing_table(self):
        log(f"Routing table for node {self.node_id}:")
        for dest, (dist, next_hop) in self.routing_table.items():
            log(f"  Destination: {dest}, Distance: {dist}, Next Hop: {next_hop}")

    def process_commands(self):
        while self.running:
            try:
                command = self.command_queue.get(timeout=1.0)
                log(f"Processing command: {command}")
                if command == 'print':
                    self.print_routing_table()
                elif command == 'quit':
                    self.stop()
                else:
                    log(f"Unknown command: {command}")
            except queue.Empty:
                continue

    def stop(self):
        self.running = False

def user_input_handler(node):
    while node.running:
        try:
            command = input("Enter command: ").strip().lower()
            log(f"Received command: {command}")
            node.command_queue.put(command)
        except EOFError:
            log("EOFError encountered. Shutting down...")
            node.stop()
        except KeyboardInterrupt:
            log("KeyboardInterrupt encountered. Shutting down...")
            node.stop()