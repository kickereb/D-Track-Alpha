import argparse
import queue
import threading
import sys
import json
import select
import time
from camera_node import CameraNode

def log(message):
    print(f"[{time.strftime('%H:%M:%S')}] {message}")
    sys.stdout.flush()

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

def main(node_id, ip, port, neighbors):
    node = CameraNode(node_id, ip, port, neighbors)
    node.start()
    
    log("Node started. Enter 'print' to show routing table or 'quit' to exit.")
    
    input_thread = threading.Thread(target=user_input_handler, args=(node,), daemon=True)
    input_thread.start()
    
    try:
        while node.running:
            time.sleep(0.1)
    except KeyboardInterrupt:
        log("Main thread interrupted. Shutting down...")
    finally:
        node.stop()
        log("Node shutting down...")
        node.socket.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start a camera node in the network.")
    parser.add_argument("node_id", help="ID of this node")
    parser.add_argument("ip", help="IP address of this node")
    parser.add_argument("port", type=int, help="Port number of this node")
    parser.add_argument("neighbors", help="Neighbors in format 'id1,ip1,port1;id2,ip2,port2;...'")
    
    args = parser.parse_args()
    
    neighbors = {}
    for neighbor in args.neighbors.split(';'):
        n_id, n_ip, n_port = neighbor.split(',')
        neighbors[n_id] = (n_ip, int(n_port))
    
    main(args.node_id, args.ip, args.port, neighbors)