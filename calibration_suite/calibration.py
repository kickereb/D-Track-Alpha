import numpy as np
import cv2 as cv2
import glob
import matplotlib.pyplot as plt
import yaml
import os

# ChArUco board parameters
CHARUCO_BOARD_SIZE = (5, 5)
SQUARE_LENGTH = 0.04
MARKER_LENGTH = 0.02
ARUCO_DICT = cv2.aruco.DICT_6X6_250

# Create ChArUco board object
dictionary = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)
board = cv2.aruco.CharucoBoard(CHARUCO_BOARD_SIZE, SQUARE_LENGTH, MARKER_LENGTH, dictionary)

# Termination criteria
criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.00001)

def draw_axis(img, camera_matrix, dist_coeffs, rvec, tvec, length):
    axis_points = np.float32([[0,0,0], [length,0,0], [0,length,0], [0,0,length]])
    imgpts, _ = cv2.projectPoints(axis_points, rvec, tvec, camera_matrix, dist_coeffs)
    imgpts = imgpts.astype(int)
    img = cv2.line(img, tuple(imgpts[0].ravel()), tuple(imgpts[1].ravel()), (0, 0, 255), 3)
    img = cv2.line(img, tuple(imgpts[0].ravel()), tuple(imgpts[2].ravel()), (0, 255, 0), 3)
    img = cv2.line(img, tuple(imgpts[0].ravel()), tuple(imgpts[3].ravel()), (255, 0, 0), 3)
    
    return img

def calculate_reprojection_error(object_points, image_points, rvecs, tvecs, camera_matrix, dist_coeffs):
    total_error = 0
    total_points = 0
    
    for i in range(len(object_points)):
        projected_points, _ = cv2.projectPoints(object_points[i], rvecs[i], tvecs[i], camera_matrix, dist_coeffs)
        if projected_points.shape[0] != image_points[i].shape[0]:
            print(f"Error: {projected_points.shape[0]} != {image_points[i].shape[0]}")
            continue
        error = cv2.norm(image_points[i], projected_points, cv2.NORM_L2) / len(projected_points)
        total_error += error
        total_points += len(object_points[i])
    
    return total_error / len(object_points), total_points

def calibrate_camera(folder_path):
    all_corners = []
    all_ids = []
    image_size = None
    images = sorted(glob.glob(os.path.join(folder_path, '*.jpg')))
    print(f"Found {len(images)} images in {folder_path}")
    
    for fname in images:
        print(f"Processing {fname}")
        img = cv2.imread(fname)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        if image_size is None:
            image_size = gray.shape[::-1]
        corners, ids, rejected = cv2.aruco.detectMarkers(gray, dictionary)
        print(f"Detected {len(corners)} markers")
        
        if len(corners) > 0:
            response, charuco_corners, charuco_ids = cv2.aruco.interpolateCornersCharuco(
                corners, ids, gray, board, minMarkers=2
            )
            print(f"Interpolation response: {response}")
            
            if response > 0:
                all_corners.append(charuco_corners)
                all_ids.append(charuco_ids)
                print(f"Added {len(charuco_corners)} corners")
                cv2.aruco.drawDetectedCornersCharuco(img, charuco_corners, charuco_ids)
                cv2.imshow('charuco_corners', img)
                cv2.waitKey(100)
            else:
                print("Failed to interpolate corners")
        else:
            print("No markers detected in this image")
    
    print(f"Successfully processed images: {len(all_corners)}")
    
    if len(all_corners) > 0:
        ret, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.aruco.calibrateCameraCharuco(
            all_corners, all_ids, board, image_size, None, None
        )
    
        # Calculate reprojection error
        object_points = [board.getChessboardCorners() for _ in range(len(all_corners))]
        mean_error, total_points = calculate_reprojection_error(object_points, all_corners, rvecs, tvecs, camera_matrix, dist_coeffs)
        print("Camera matrix:\n", camera_matrix)
        print("\nDistortion coefficients:\n", dist_coeffs)
        print(f"\nMean reprojection error: {mean_error:.4f} pixels")
        print(f"Total points used: {total_points}")
        return camera_matrix, dist_coeffs, rvecs, tvecs, image_size, mean_error, total_points, images
    else:
        print("No successful corner detections. Unable to calibrate.")
        return None

def visualize_calibration(camera_matrix, dist_coeffs, rvecs, tvecs, images):
    images_with_axes = []
    
    for i, image_path in enumerate(images):
        img = cv2.imread(image_path)
        img_with_axis = draw_axis(img.copy(), camera_matrix, dist_coeffs, rvecs[i], tvecs[i], 0.1)
        # Add label with rvec and tvec information
        label = f"Image {i+1}: {os.path.basename(image_path)}\nrvec: {rvecs[i].flatten()}\ntvec: {tvecs[i].flatten()}"
        y0, dy = 50, 30
    
        for j, line in enumerate(label.split('\n')):
            y = y0 + j*dy
            cv2.putText(img_with_axis, line, (50, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
        images_with_axes.append(img_with_axis)
    
    # Display all images with axes in a grid
    rows = int(np.ceil(len(images_with_axes) / 3))
    cols = min(len(images_with_axes), 3)
    fig, axs = plt.subplots(rows, cols, figsize=(20, 5*rows))
    axs = axs.ravel() if rows > 1 else [axs]
    
    for i, img in enumerate(images_with_axes):
        axs[i].imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        axs[i].axis('off')
        axs[i].set_title(f"Image {i+1}")
    
    plt.tight_layout()
    plt.show()
    return images_with_axes

if __name__ == '__main__':
    base_folder = ''
    calibration_results = {}
    
    for folder in sorted(glob.glob(base_folder + 'Cam_*')):
        camera_name = os.path.basename(folder)
        print(f"\nCalibrating {camera_name}")
        result = calibrate_camera(folder)
    
        if result is not None:
            camera_matrix, dist_coeffs, rvecs, tvecs, image_size, mean_error, total_points, images = result
            # Visualize the calibration results
            images_with_axes = visualize_calibration(camera_matrix, dist_coeffs, rvecs, tvecs, images)
            calibration_results[camera_name] = {
                "camera_matrix": camera_matrix,
                "dist_coeffs": dist_coeffs,
                # "rvecs": rvecs,
                # "tvecs": tvecs,
                "image_size": image_size,
                "mean_reprojection_error": mean_error,
                "total_points": total_points,
                "images_with_axes": images_with_axes,
                "original_images": images
            }
    
            # Ask user which image to save
            selected_index = int(input(f"Enter the number of the image you want to save for {camera_name} (1-{len(images_with_axes)}): ")) - 1
            selected_image = images_with_axes[selected_index]
            selected_original_image = images[selected_index]
    
            # Save the image with axes
            cv2.imwrite(f"data/calibrations/{camera_name}_selected_calibration.jpg", selected_image)
            print(f"Selected image with axes saved as 'data/calibrations/{camera_name}_selected_calibration.jpg'")
    
            # Save the original image
            cv2.imwrite(f"data/calibrations/{camera_name}_selected_original.jpg", cv2.imread(selected_original_image))
            print(f"Selected original image saved as 'data/calibrations/{camera_name}_selected_original.jpg'")
    
            # add the selected rvec and tvec to the calibration results
            calibration_results[camera_name]["rvec"] = rvecs[selected_index]
            calibration_results[camera_name]["tvec"] = tvecs[selected_index]

    # Save calibration results
    for camera_name, data in calibration_results.items():
        yaml_filename = f"data/calibrations/{camera_name}_calibration.yml"
        calibration_data = {
            "intrinsic": {
                "camera_matrix": {
                    "rows": 3,
                    "cols": 3,
                    "dt": "d",
                    "data": data["camera_matrix"].flatten().tolist()
                },
                "distortion_vector": {
                    "rows": 1,
                    "cols": 5,
                    "dt": "d",
                    "data": data["dist_coeffs"].flatten().tolist()
                },
                "distortion_type": 0,
                "camera_group": 0,
                "img_width": data["image_size"][0],
                "img_height": data["image_size"][1]
            },
            "extrinsic": {
                "distortion_type": 0,
                "camera_group": 0,
                "img_width": data["image_size"][0],
                "img_height": data["image_size"][1],
                "rvec": {
                    "rows": 3,
                    "cols": 1,
                    "dt": "d",
                    "data": data["rvec"].flatten().tolist()
                },
                "tvec": {
                    "rows": 3,
                    "cols": 1,
                    "dt": "d",
                    "data": data["tvec"].flatten().tolist()
                }
            },
            "accuracy": {
                "mean_reprojection_error": data["mean_reprojection_error"],
                "total_points": data["total_points"]
            }
        }
        
        with open(yaml_filename, 'w') as yaml_file:
            yaml_file.write("%YAML:1.0\n---\n")
            yaml.dump(calibration_data, yaml_file, default_flow_style=None)
        
        print(f"Calibration results for {camera_name} saved to '{yaml_filename}'")
        print(f"Mean reprojection error: {data['mean_reprojection_error']:.4f} pixels")
        print(f"Total points used: {data['total_points']}")
    
    cv2.destroyAllWindows