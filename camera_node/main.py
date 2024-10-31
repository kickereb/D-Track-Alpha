import argparse
import time
import yaml
from camera_node import CameraNode
from utils.logger import log
import numpy as np
from utils.network import get_ip_address, discover_dtrack_hosts

def load_calibration(camera_id: str = None):
    """
    Loads camera calibration data from YAML file.
    
    Args:
        camera_id: Optional camera identifier (e.g., 'Cam_001'). If None, 
                  looks for calibration_matrices.yml in current directory
    
    Returns:
        tuple: (camera_matrix, dist_coeffs)
        
    Raises:
        FileNotFoundError: If calibration file is not found
        ValueError: If calibration data is invalid
    """
    filename = "calibration_matrices.yml"
    
    try:
        with open(filename, 'r') as f:
            # Skip the %YAML:1.0 line if it exists
            first_line = f.readline()
            if not first_line.startswith('%YAML'):
                f.seek(0)  # Reset to start if no YAML header
            
            # Load YAML content
            calib_data = yaml.safe_load(f)
            
        # Extract camera matrix
        matrix_data = calib_data['intrinsic']['camera_matrix']['data']
        camera_matrix = np.array(matrix_data).reshape(3, 3)
        
        # Extract distortion coefficients
        dist_data = calib_data['intrinsic']['distortion_vector']['data']
        dist_coeffs = np.array(dist_data)

        # Extract extrinsic parameters
        rvec_data = calib_data['extrinsic']['rvec']['data']
        rvec = np.array(rvec_data)
        
        tvec_data = calib_data['extrinsic']['tvec']['data']
        tvec = np.array(tvec_data)
        
        # Validate data
        if camera_matrix.shape != (3, 3):
            raise ValueError(f"Invalid camera matrix shape: {camera_matrix.shape}")
        if len(dist_coeffs) != 5:
            raise ValueError(f"Invalid distortion coefficients length: {len(dist_coeffs)}")
        
        # Print calibration info
        print_calibration_info(camera_matrix, dist_coeffs, 
                             calib_data['accuracy']['mean_reprojection_error'],
                             calib_data['accuracy']['total_points'])
        
        return camera_matrix, dist_coeffs, rvec, tvec
        
    except FileNotFoundError:
        log(f"Calibration file not found: {filename}")
        log("Falling back to dummy calibration values")
        return get_dummy_calibration()
    except Exception as e:
        log(f"Error loading calibration data: {str(e)}")
        log("Falling back to dummy calibration values")
        return get_dummy_calibration()

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

def print_calibration_info(camera_matrix: np.ndarray, 
                          dist_coeffs: np.ndarray,
                          reprojection_error = None,
                          total_points = None):
    """
    Prints readable information about the calibration parameters
    """
    print("\n=== Camera Calibration Parameters ===")
    print("\nCamera Matrix:")
    print(f"Focal Length X: {camera_matrix[0,0]:.1f} pixels")
    print(f"Focal Length Y: {camera_matrix[1,1]:.1f} pixels")
    print(f"Principal Point: ({camera_matrix[0,2]:.1f}, {camera_matrix[1,2]:.1f})")
    
    print("\nDistortion Coefficients:")
    print(f"k1: {dist_coeffs[0]:.6f}")
    print(f"k2: {dist_coeffs[1]:.6f}")
    print(f"p1: {dist_coeffs[2]:.6f}")
    print(f"p2: {dist_coeffs[3]:.6f}")
    print(f"k3: {dist_coeffs[4]:.6f}")
    
    if reprojection_error is not None:
        print(f"\nCalibration Accuracy:")
        print(f"Mean Reprojection Error: {reprojection_error:.4f} pixels")
    if total_points is not None:
        print(f"Total Calibration Points: {total_points}")
    print("=" * 45 + "\n")

def main(node_id, ip, port, neighbors):
    # Create and start node
    camera_matrix, dist_coeffs, rvec, tvec = load_calibration(node_id)
    node = CameraNode(node_id, ip, port, neighbors, camera_matrix, dist_coeffs, rvec, tvec)
    
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