# D-Track Alpha: Mobile and Wireless Systems

<pre>
Team Members:
Tom Zhu         a1770422
Lennox Avdiu    a1774765
Evam Kaushik    a1909167
</pre>

D-Track Alpha is a distributed, multi-object tracking system designed to leverage multiple camera-equipped Raspberry Pi devices to monitor individuals across non-overlapping fields of view in indoor environments. This system enables real-time trajectory tracking and enhances situational awareness, offering applications in security monitoring, space management, and behavioral analysis.

---

## Project Overview

This project focuses on a low-cost, real-time, scalable solution for tracking objects (people) across non-overlapping fields of view (FoV) using a distributed network of camera-equipped Raspberry Pis. The main objective is to track individuals as they move across different camera views, reconstruct trajectories, and maintain identity consistency through advanced data fusion techniques. 

### Key Elements

1. **Pi Camera Setup**: Each Raspberry Pi device is equipped with a camera module to detect and track individuals within its FoV.
2. **Field of View Management**: D-Track Alpha manages non-overlapping FoVs across multiple cameras, effectively tracking individuals through sequential data association.
3. **Centralized Processing**: Each device sends data to a backend server for real-time processing, fusion, and visualization of trajectories across the monitored space.

## Setup Instructions

To begin, please set up each Raspberry Pi camera by running the following script on a fresh Raspberry Pi:

```bash
./setup_pi_camera.sh
```

This will install necessary dependencies and configure the camera. The script will automatically reboot each Raspberry Pi upon completion.

### Prerequisites

Ensure you have the following Python packages installed for trajectory visualization and data processing:

- `matplotlib`
- `numpy`
- `scipy`
- `natsort`

Install packages with:

```bash
pip install matplotlib numpy scipy natsort
```

## Usage

1. Clone the repository:

   ```bash
   git clone https://github.com/your-username/D-Track-Alpha.git
   cd D-Track-Alpha
   ```

2. Set the `folder_path` variable in `tracking_script.py` to the directory containing the JSON files.

3. Set `num_frames_to_analyze` to the desired number of frames to process. For example:

   ```python
   folder_path = 'path_to_json_folder'
   num_frames_to_analyze = 5
   ```

4. Run the tracking script to visualize trajectories:

   ```bash
   python tracking_script.py
   ```

## System Design

+--------------------------------------------------------+
|                    D-Track Alpha System                |
+--------------------------------------------------------+
|                                                        |
|  +-----------------------------------------------+     |
|  |               Raspberry Pi Nodes              |     |
|  +-----------------------------------------------+     |
|                                                        |
|   +------------------+    +------------------+    +------------------+  
|   | Raspberry Pi #1  |    | Raspberry Pi #2  |    | Raspberry Pi #3  |
|   +------------------+    +------------------+    +------------------+
|   |  - YOLOv4        |    |  - YOLOv4        |    |  - YOLOv4        |
|   |  - April Tag     |    |  - April Tag     |    |  - April Tag     |
|   |    Calibration   |    |    Calibration   |    |    Calibration   |
|   |  - Transform to  |    |  - Transform to  |    |  - Transform to  |
|   |    Global Coords |    |    Global Coords |    |    Global Coords |
|   +------------------+    +------------------+    +------------------+
|             |                     |                     |             
|             +---------------------+---------------------+             
|                               |                                       
+-------------------------------v----------------------------------------+
|                         Aggregation Hub                               |
+-----------------------------------------------------------------------+
|                                                                       |
|  - DBSCAN Clustering for Duplicate Resolution                         |
|  - Unique ID Assignment for Each Person                               |
|  - Kalman Filter for Frame-by-Frame Tracking                          |
|                                                                       |
+-----------------------------------------------------------------------+
                                |
                                v
+-----------------------------------------------------------------------+
|                           Web Application                             |
+-----------------------------------------------------------------------+
|                                                                       |
|  - Real-Time Visualization of Person Trajectories                     |
|  - Alerts & Notifications for Specified Events                        |
|  - Data Logging for Historical Analysis                               |
|                                                                       |
+-----------------------------------------------------------------------+



### Edge Detection and Tracking

D-Track Alpha employs each Raspberry Pi as an edge device for detecting and tracking individuals in its FoV. Without using unique identifiers, the system relies on spatial proximity and movement patterns to link individuals across frames and cameras. Each device captures bounding boxes of detected objects and calculates the midpoint of each box’s lower edge for tracking consistency.

### Backend Processing

The backend server collects data from each Raspberry Pi, applies data fusion techniques, and reconstructs trajectories across non-overlapping views. Data association is handled using nearest-neighbor matching and Kalman filters, which smooth transitions and manage occlusions across frames.

### Mobile and Web Applications

- **Mobile Interface**: Allows for live monitoring, system configuration, and receiving alerts.
- **Web Dashboard**: Provides administrators with visualization of trajectories, analysis of space utilization, and control over individual camera settings.

## Tracking and Visualization

The core tracking algorithm utilizes nearest-neighbor matching to associate detections between consecutive frames. Each object’s trajectory is updated based on its spatial proximity to detections in the following frame. Visualizations show paths across frames, representing the system's capacity to track individuals seamlessly across non-overlapping cameras.

## Future Work

The D-Track Alpha system could be extended with the following features:

1. **Increased Camera Coverage**: Supporting a larger network of cameras for wider area tracking.
2. **Enhanced Mobile Notifications**: Real-time alerts for specific events, such as unauthorized entry or crossing into restricted zones.
3. **Machine Learning for Data Fusion**: Using advanced machine learning models to improve the accuracy and efficiency of the tracking system.
