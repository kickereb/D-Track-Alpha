import argparse
import time
from camera_node import CameraNode
from utils.logger import log
import numpy as np
from utils.network import get_ip_address, discover_dtrack_hosts

def get_dummy_calibration(image_width: int = 1280, image_height: int = 720):
    """
    Creates dummy camera calibration data for testing
    
    These values are rough approximations for a typical wide-angle camera
    at 1280x720 resolution. They should only be used for testing.
    
    Args:
        image_width: Width of the camera image in pixels
        image_height: Height of the camera image in pixels
        
    Returns:
        tuple: (camera_matrix, dist_coeffs)
    """
    # Focal length approximation (rough estimate for 90° FOV)
    focal_length = image_width * 0.8
    
    # Principal point (usually close to image center)
    cx = image_width / 2
    cy = image_height / 2
    
    # Create camera matrix
    # [[fx,  0, cx],
    #  [ 0, fy, cy],
    #  [ 0,  0,  1]]
    camera_matrix = np.array([
        [focal_length, 0, cx],
        [0, focal_length, cy],
        [0, 0, 1]
    ], dtype=np.float32)
    
    # Distortion coefficients [k1, k2, p1, p2, k3]
    # Using minimal distortion for dummy values
    dist_coeffs = np.array([0.1, 0.01, 0, 0, 0.001], dtype=np.float32)
    
    return camera_matrix, dist_coeffs

def print_calibration_info(camera_matrix: np.ndarray, dist_coeffs: np.ndarray):
    """
    Prints readable information about the calibration parameters
    """
    print("\n=== Camera Calibration Parameters (DUMMY) ===")
    print("WARNING: These are dummy values for testing only!")
    print("\nCamera Matrix:")
    print(f"Focal Length: {camera_matrix[0,0]:.1f} pixels")
    print(f"Principal Point: ({camera_matrix[0,2]:.1f}, {camera_matrix[1,2]:.1f})")
    print("\nDistortion Coefficients:")
    print(f"k1: {dist_coeffs[0]:.3f}")
    print(f"k2: {dist_coeffs[1]:.3f}")
    print(f"p1: {dist_coeffs[2]:.3f}")
    print(f"p2: {dist_coeffs[3]:.3f}")
    print(f"k3: {dist_coeffs[4]:.3f}")
    print("\nNOTE: Please replace with actual calibration values")
    print("=" * 45 + "\n")

def main(node_id, ip, port, neighbors):
    # Create and start node
    camera_matrix, dist_coeffs = get_dummy_calibration()
    node = CameraNode(node_id, ip, port, neighbors, camera_matrix, dist_coeffs)
    
    try:
        node.start()
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        node.stop()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start a camera node in the network.")
    # TODO: When formatting pi make hostname in format dtrack-A, dtrack-B etc. to uniquely name a node.
    parser.add_argument("node_id", help="ID of this node")
    parser.add_argument("port", type=int, help="Port number of this node")
    parser.add_argument("--discover", action="store_true", 
                       help="Enable automatic neighbor discovery")
    parser.add_argument("--neighbors", 
                       help="Manual neighbors in format 'id1,ip1,port1;id2,ip2,port2;...'",
                       default="")
    
    args = parser.parse_args()


    neighbors = {}
    
    # Automatic discovery if enabled
    if args.discover:
        discovered_neighbors = discover_dtrack_hosts()
        neighbors.update(discovered_neighbors)
        print(f"Discovered {len(discovered_neighbors)} dtrack nodes")
    
    # Add manually specified neighbors if any
    if args.neighbors:
        for neighbor in args.neighbors.split(';'):
            if neighbor:  # Skip empty strings
                n_id, n_ip, n_port = neighbor.split(',')
                neighbors[n_id] = (n_ip, int(n_port), 1)
    
    ip = get_ip_address()

    main(args.node_id, ip, args.port, neighbors)