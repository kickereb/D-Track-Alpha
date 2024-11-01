import matplotlib.pyplot as plt
import json
import numpy as np
from scipy.spatial import distance
import os
from natsort import natsorted

def calculate_lower_midpoint(view):
    if view['xmax'] == -1 or view['xmin'] == -1 or view['ymax'] == -1 or view['ymin'] == -1:
        return None
    x_mid = (view['xmax'] + view['xmin']) / 2
    y_lower = view['ymin']
    return np.array([x_mid, y_lower])

def get_positions_from_frame(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    positions = []
    for person in data:
        midpoints = [calculate_lower_midpoint(view) for view in person['views'] if calculate_lower_midpoint(view) is not None]
        if midpoints:
            avg_position = np.mean(midpoints, axis=0)
            positions.append(avg_position)
    return np.array(positions)

def plot_trajectories_from_folder(folder_path, num_frames_to_analyze):
    files = natsorted([os.path.join(folder_path, file) for file in os.listdir(folder_path) if file.endswith('.json')])
    files = files[:num_frames_to_analyze] 

    plt.figure(figsize=(8, 8))
    trajectories = []

    for i in range(len(files) - 1):
        positions_frame1 = get_positions_from_frame(files[i])
        positions_frame2 = get_positions_from_frame(files[i + 1])

        if i == 0:
            trajectories = [[pos] for pos in positions_frame1]

        for pos2 in positions_frame2:
            distances = distance.cdist([pos2], positions_frame1, 'euclidean')
            nearest_idx = np.argmin(distances)

            if nearest_idx < len(trajectories):
                trajectories[nearest_idx].append(pos2)
            else:
                trajectories.append([pos2])

    for traj in trajectories:
        traj = np.array(traj)
        plt.plot(traj[:, 0], traj[:, 1], marker='o')

    plt.xlabel('X-axis')
    plt.ylabel('Y-axis')
    plt.title(f'Trajectories across {num_frames_to_analyze} frames')
    plt.grid(True)
    plt.show()

folder_path = '/content/annotations_positions'
num_frames_to_analyze = 5
plot_trajectories_from_folder(folder_path, num_frames_to_analyze)
