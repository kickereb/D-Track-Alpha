import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import cv2
import os
from os import listdir
from os.path import isfile, join
from xml.dom import minidom
from xml.etree import ElementTree
import matplotlib.pyplot as plt
import glob

GRID_SIZE = (320, 240)

def load_all_camera_matricies(parent_folder):
    """
    Loads all camera matrices from a folder.

    Raises:
        FileNotFoundError: see _load_content_lines
        ValueError: see _load_content_lines

    :param _lst_files: [str] path of a file listing all the calibration file
    :return: 
    """
    rvec, tvec, camera_matrices, dist_coef = [], [], [], []
    for folder in sorted(glob.glob(parent_folder + 'Cam_*_calibration.yml')):
        fs = cv2.FileStorage(folder, cv2.FILE_STORAGE_READ)
        rvec.append(fs.getNode('extrinsic').getNode('rvec').mat())
        tvec.append(fs.getNode('extrinsic').getNode('tvec').mat())
        camera_matrices.append(fs.getNode('intrinsic').getNode('camera_matrix').mat())
        dist_coef.append(fs.getNode('intrinsic').getNode('distortion_vector').mat())
        fs.release()
    return np.array(rvec), np.array(tvec),np.array(camera_matrices), np.array(dist_coef)
    
def load_all_annotations(path='data/annotations/'):
    list_of_files = [join(path, f) for f in listdir(path) if isfile(join(path, f)) and f.endswith('.json')]
    annotation_files = sorted(list_of_files)
    annotations = []
    for _file in annotation_files:
        with open(_file, 'r') as f:
            annotations.append(json.load(f))
    return annotations

def calibrate_views(camera_matrices, dist_coef, rvec, tvec, debug=False):
    view_calibration = {
        0: {"start_pixel": (0, 1080), "end_pixel": (1920, 1080), "start_true_coord": (0, 0), "end_true_coord": (320, 150)},
        1: {"start_pixel": (0, 1080), "end_pixel": (1920, 1080), "start_true_coord": (60, 150), "end_true_coord": (360, 60)},
    }
    
    for view in range(len(camera_matrices)):
        start_pixel = view_calibration[view]["start_pixel"]
        end_pixel = view_calibration[view]["end_pixel"]
        start_true_coord = np.array(view_calibration[view]["start_true_coord"])
        end_true_coord = np.array(view_calibration[view]["end_true_coord"])

        if debug:
            print(f"View {view} has start pixel at {start_pixel} and end pixel at {end_pixel}")
            print(f"View {view} has start true coord at {start_true_coord} and end true coord at {end_true_coord}")

        projected_start = image_to_world(start_pixel[0], start_pixel[1], camera_matrices[view], dist_coef[view], rvec[view], tvec[view], y=0)
        projected_end = image_to_world(end_pixel[0], end_pixel[1], camera_matrices[view], dist_coef[view], rvec[view], tvec[view], y=0)

        if debug:
            print(f"View {view} has projected start at {projected_start} and projected end at {projected_end}")

        # Calculate scaling factors
        scale_x = (end_true_coord[0] - start_true_coord[0]) / (projected_end[0] - projected_start[0])
        scale_z = (end_true_coord[1] - start_true_coord[1]) / (projected_end[1] - projected_start[1])

        # Calculate offsets
        offset_x = start_true_coord[0] - (projected_start[0] * scale_x)
        offset_z = start_true_coord[1] - (projected_start[1] * scale_z)

        view_calibration[view].update({
            "scale_x": scale_x,
            "scale_z": scale_z,
            "offset_x": offset_x,
            "offset_z": offset_z
        })

        if debug:
            print(f"View {view} calibration: scale_x={scale_x}, scale_z={scale_z}, offset_x={offset_x}, offset_z={offset_z}")
    
    return view_calibration

def image_to_world(u, v, mtx, dist, rvec, tvec, y=0):
    # Extract rotation matrix and its inverse
    R, _ = cv2.Rodrigues(rvec)
    R_inv = R.T

    ww, hh = GRID_SIZE[0], GRID_SIZE[1]
    
    # Compute optimal camera matrix and its inverse
    optimalMtx, roi = cv2.getOptimalNewCameraMatrix(mtx, dist, (ww, hh), 0, (ww, hh))
    
    # Undistort the pixel coordinates
    uv_1 = np.array([[[u, v]]], dtype=np.float32)
    uv_undistorted = cv2.undistortPoints(uv_1, mtx, dist, None, optimalMtx)
    
    # Create a ray from the camera center through the undistorted point
    ray = np.array([uv_undistorted[0, 0, 0], uv_undistorted[0, 0, 1], 1.0])
    
    # Transform ray to world coordinates
    ray = np.linalg.inv(optimalMtx) @ ray
    ray = ray / np.linalg.norm(ray)
    
    # Calculate the scaling factor to reach the plane at y
    t = (y - tvec[1]) / (R_inv @ ray)[1]
    
    # Calculate the 3D point
    world_point = R_inv @ (t * ray - tvec)
    
    # Project world coordinates to image coordinates for verification
    points_2d, _ = cv2.projectPoints(np.array([world_point]), rvec, tvec, mtx, dist)

    return points_2d[0][0]

def project_positions_to_grid(annotations, rvec, tvec, camera_matrices, dist_coef):
    projected = {}

    view_calibration = calibrate_views(camera_matrices, dist_coef, rvec, tvec, debug=True)

    for frame_num, frame in enumerate(annotations):
        for person in frame:
            personID = person['personID']
            if personID not in projected:
                projected[personID] = {}
            
            valid_world_coords = []
            
            for view in person['views']:
                viewNum, xmin, ymin, xmax, ymax = view.values()
                print(f"View {viewNum} has xmin={xmin}, xmax={xmax}, ymin={ymin}, ymax={ymax}")
                if xmin == -1:
                    continue
                
                # Get the foot of the person
                uvCoord = np.array([(xmin + xmax) / 2, ymax, 1])
                mtx = camera_matrices[viewNum]
                dist = dist_coef[viewNum]
                r = np.asarray(rvec[viewNum])
                t = np.asarray(tvec[viewNum])
                
                worldCoord = image_to_world(uvCoord[0], uvCoord[1], mtx, dist, r, t, y=0)
                # Apply scaling and offset
                calibrated_x = worldCoord[0] * view_calibration[viewNum]["scale_x"] + view_calibration[viewNum]["offset_x"]
                calibrated_z = worldCoord[1] * view_calibration[viewNum]["scale_z"] + view_calibration[viewNum]["offset_z"]
                calibrated_worldCoord = np.array([calibrated_x, calibrated_z])

                # Check if the world coordinate is within the grid bounds
                # if grid_origin[0] <= worldCoord[0] <= grid_origin[0] + grid_size[0] and \
                #    grid_origin[1] <= worldCoord[2] <= grid_origin[1] + grid_size[1]:  # Note: using z for second comparison
                # if 0 <= worldCoord[0] <= GRID_SIZE[0] and 0 <= worldCoord[1] <= GRID_SIZE[1]:
                # if viewNum == 0:
                valid_world_coords.append(calibrated_worldCoord)
            
            if valid_world_coords:
                # Average the world coordinates from all valid views
                print(f"Person {personID} at frame {frame_num} has {len(valid_world_coords)} valid views")
                for coord in valid_world_coords:
                    print(f"Person {personID} at frame {frame_num} has valid view at {coord}")
                avg_world_coord = np.mean(valid_world_coords, axis=0)
                
                # Apply the grid transformation
                grid_coord = (avg_world_coord)
                
                projected[personID][frame_num] = grid_coord
                
                print(f"Person {personID} at frame {frame_num} projected to {grid_coord}")
            else:
                print(f"Person {personID} at frame {frame_num} has no valid views")
                projected[personID][frame_num] = None

    return projected

def visualize_grid(positions, grid_size):
    # # Create annotations
    # max_frames = max([len(personTracks) for personTracks in positions.values()])
    # plot_frames = []
    # for frame_num in range(max_frames):
    #     coord = [[tracks[frame_num][0], tracks[frame_num][1]] for tracks in positions.values() if frame_num in tracks.keys()]
    #     text = [f"Person {personID}" for personID, tracks in positions.items() if frame_num in tracks.keys()]
    #     plot_frames.append(go.Frame(
    #         data=[go.Scatter(
    #             x=[c[0] for c in coord],
    #             y=[c[1] for c in coord],
    #             mode='markers+text', 
    #             marker=dict(size=10),
    #             text=text,
    #             textposition="top center",
    #             hoverinfo='text'
    #         )],
    #         name=f"frame{frame_num}",
    #     ))

    # Get all unique person IDs
    all_person_ids = list(positions.keys())
    
    # Create a color map for each person
    colors = plt.cm.rainbow(np.linspace(0, 1, len(all_person_ids)))
    color_map = {person_id: f'rgb({int(color[0]*255)},{int(color[1]*255)},{int(color[2]*255)})' 
                 for person_id, color in zip(all_person_ids, colors)}

    # Find the maximum number of frames
    print(positions)
    max_frames = max([list(tracks.keys())[-1] for tracks in positions.values() if len(tracks.keys()) > 0])

    # Create base traces for each person
    traces = []
    for person_id in all_person_ids:
        traces.append(go.Scatter(
            x=[],
            y=[],
            mode='markers+text',
            marker=dict(size=10, color=color_map[person_id]),
            text=f"Person {person_id}",
            textposition="top center",
            name=f"Person {person_id}",
            hoverinfo='text',
            visible=True
        ))

    # Create frames
    frames = []
    for frame_num in range(max_frames + 1):
        frame_data = []
        for i, person_id in enumerate(all_person_ids):
            if frame_num in positions[person_id]:
                position = positions[person_id][frame_num]
                if position is not None:
                    x, y = position
                    frame_data.append(go.Scatter(
                        x=[x],
                        y=[y],
                        mode='markers+text',
                        marker=dict(size=10, color=color_map[person_id]),
                        text=f"Person {person_id}",
                        textposition="top center",
                        name=f"Person {person_id}",
                        hoverinfo='text',
                        visible=True
                    ))
                else:
                    # Handle the case where position is None
                    frame_data.append(go.Scatter(x=[], y=[]))
            else:
                frame_data.append(go.Scatter(x=[], y=[]))
        frames.append(go.Frame(data=frame_data, name=f"frame{frame_num}"))

    fig = go.Figure(
        data=[*traces],
        layout=go.Layout(
            xaxis=dict(range=[0, grid_size[0]], autorange=False),
            yaxis=dict(range=[0, grid_size[1]], autorange=False),
            title="Tracks over time",
            xaxis_title="X",
            yaxis_title="Z",
            updatemenus=[{
                "type": "buttons",
                "direction": "right",
                "x": -0.01,
                "y": -0.05,
                "buttons": [
                    {"label": "Play", "method": "animate", "args": [None, {"frame": {"duration": 300, "redraw": True}, "fromcurrent": True, "transition": {"duration": 300}}]},
                    {"label": "Pause", "method": "animate", "args": [[None], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate", "transition": {"duration": 0}}]},
                ]
            }],
            sliders=[{
                "active": 0,
                "yanchor": "top",
                "xanchor": "left",
                "currentvalue": {
                    "font": {"size": 20},
                    "prefix": "Frame:",
                    "visible": True,
                    "xanchor": "right"
                },
                "steps": [{"args": [[f"frame{i}"], {"frame": {"duration": 300, "redraw": True}, "mode": "immediate", "transition": {"duration": 300}}],
                           "label": i,
                           "method": "animate"} for i in range(max_frames + 1)]
            }]
        ),
        frames=frames
    )

    fig.show()

def main():
    camera_matricies_parent_folder = "data/calibrations/"
    rvecs, tvecs, camera_matrices, dist_coef = load_all_camera_matricies(camera_matricies_parent_folder)

    annotations = load_all_annotations(path="data/annotations/test_set/")[0:10]

    # Project annotations to grid
    projected_postitions = project_positions_to_grid(annotations,
                                                     rvecs, 
                                                     tvecs, 
                                                     camera_matrices, 
                                                     dist_coef)
    # Visualize the grid with annotations
    visualize_grid(projected_postitions, GRID_SIZE)

if __name__ == "__main__":
    main()