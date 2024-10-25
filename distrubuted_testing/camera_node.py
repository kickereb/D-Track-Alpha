import threading
import time
import socket
import json
import select
import sys
import queue

from picamera2 import Picamera2
from datetime import datetime
import os
from libcamera import controls

# Ensure the photos directory exists
PHOTOS_DIR = "./data/photos"
os.makedirs(PHOTOS_DIR, exist_ok=True)

# Initialize the camera
picam2 = Picamera2()
capture_config = picam2.create_still_configuration(main={"size": (1920, 1080)})
picam2.configure(capture_config)

# Set focus mode to auto
picam2.set_controls({"AfMode": controls.AfModeEnum.Continuous})

# Set exposure mode to normal (auto)
picam2.set_controls({"AeEnable": True})

picam2.start()
time.sleep(2)  # Warm-up time

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
        self.frame_number = 0
        self.lock = threading.Lock()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((ip, port))
        self.running = True
        self.command_queue = queue.Queue()

    def start(self):
        threading.Thread(target=self.listen_for_routing_table_updates, daemon=True).start()
        threading.Thread(target=self.send_periodic_routing_table_updates, daemon=True).start()
        threading.Thread(target=self.run_person_tracking_pipeline, daemon=True).start()

    def run_person_tracking_pipeline(self):
        # Block this thread from progressing until we fully process this frame.
        while self.frame_number != 3:
            self.take_snapshot_of_scene()
            # self.update_global_view()
            time.sleep(5)

        self.stop()

    def update_global_view(self):
        self.receive_view_from_all_nodes()
        # self.create_global_view()

    def take_snapshot_of_scene(self):
        self.take_photo()
        self.detect_people_in_frame()
        self.send_view_to_all_nodes()
        self.frame_number = self.frame_number + 1

    def take_photo(self):
        filename = os.path.join(PHOTOS_DIR, f"{self.frame_number}.jpg")
        picam2.capture_file(filename)
        print(f"Photo taken: {filename}")

    def detect_people_in_frame(self):
        pass

    def send_view_to_all_nodes(self):
        for neighbor, (ip, port) in self.neighbors.items():
            print(neighbor, ip, port)
            # self.send_routing_table(ip, port)

    def listen_for_routing_table_updates(self):
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

    def send_periodic_routing_table_updates(self):
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

    def stop(self):
        self.running = False

    def destroy_node(self):
        log("Node shutting down...")
        picam2.stop()
        self.socket.close()