import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import paho.mqtt.client as mqtt
import json
import io
import paramiko
import cv2
import numpy as np
import time

# MQTT broker settings
BROKER_ADDR = "localhost"
BROKER_PORT = 1883

# List of hosts
HOSTS = ["192.168.65.51", "192.168.65.52"]  # Add or remove hosts as needed

# ChArUco board parameters
CHARUCO_BOARD_SIZE = (5, 5)  # (number_x_square, number_y_square)
SQUARE_LENGTH = 0.04  # length_square
MARKER_LENGTH = 0.03  # length_marker
ARUCO_DICT = cv2.aruco.DICT_6X6_250  # This is a default, adjust if needed

# Additional parameters (not directly used in OpenCV functions, but may be useful)
RESOLUTION = (2000, 2000)  # (resolution_x, resolution_y)
NUMBER_BOARD = 1
BOARDS_INDEX = []
SQUARE_SIZE_CM = 5.7  # square_size in cm

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker")
    else:
        print(f"Failed to connect, return code {rc}")

class CameraControlGUI:
    def __init__(self, master):
        self.image_counter = 0
        
        self.master = master
        master.title("Camera Control")
        
        # Make the window fullscreen
        master.attributes('-fullscreen', True)

        # Create MQTT client
        self.client = mqtt.Client()
        self.client.on_connect = on_connect
        self.client.connect(BROKER_ADDR, BROKER_PORT)
        self.client.loop_start()

        # SSH setup
        self.ssh_configs = [
            {"hostname": host, "username": "dtrack", "password": "dtrack"}
            for host in HOSTS
        ]

        # Main frame to hold all elements
        main_frame = ttk.Frame(master)
        main_frame.pack(expand=True, fill=tk.BOTH)

        # Control frame for buttons
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(side=tk.TOP, fill=tk.X, pady=10)

        self.capture_button = ttk.Button(control_frame, text="Capture Images", command=self.capture_images)
        self.capture_button.pack(side=tk.LEFT, padx=10)

        self.exit_button = ttk.Button(control_frame, text="Exit", command=self.on_closing)
        self.exit_button.pack(side=tk.RIGHT, padx=10)

        # Frame to hold image labels
        self.image_frame = ttk.Frame(main_frame)
        self.image_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        # Create image labels for each host
        self.image_labels = []
        self.name_labels = []
        self.quality_labels = []

        for i, host in enumerate(HOSTS):
            frame = ttk.Frame(self.image_frame)
            frame.grid(row=0, column=i, sticky="nsew", padx=5, pady=5)
            
            self.image_frame.grid_columnconfigure(i, weight=1)
            
            image_label = ttk.Label(frame)
            image_label.pack(expand=True, fill=tk.BOTH)
            self.image_labels.append(image_label)
            
            name_label = ttk.Label(frame, text=f"Camera {i+1} ({host})")
            name_label.pack()
            self.name_labels.append(name_label)

            quality_label = ttk.Label(frame, text="Quality: N/A")
            quality_label.pack()
            self.quality_labels.append(quality_label)

        self.image_frame.grid_rowconfigure(0, weight=1)

        self.status_label = ttk.Label(main_frame, text="")
        self.status_label.pack(pady=5)

        # Create ChArUco board object
        self.dictionary = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)
        self.board = cv2.aruco.CharucoBoard(CHARUCO_BOARD_SIZE, SQUARE_LENGTH, MARKER_LENGTH, self.dictionary)

    def capture_images(self):
        time.sleep(1)
        # fps = 2
        # sleep_time = 1 / fps
        # for i in range(10):
        image_name = f"{self.image_counter:05}"
        self.status_label.config(text="Capturing images...")
        self.client.publish("dtrack/take_photo", json.dumps({"frame": image_name}))
        self.image_counter += 1
            # time.sleep(sleep_time)

        for i, config in enumerate(self.ssh_configs):
            image_path = f"/home/dtrack/dev/dtrack/data/photos/{image_name}.jpg"
            self.download_and_display_image(image_path, config, i)

        self.image_counter += 1

    def download_and_display_image(self, remote_path, ssh_config, index):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(**ssh_config)

            sftp = ssh.open_sftp()
            with sftp.file(remote_path, 'rb') as remote_file:
                image_data = remote_file.read()

            sftp.close()
            ssh.close()

            # Convert image data to numpy array for OpenCV processing
            nparr = np.frombuffer(image_data, np.uint8)
            cv_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            # Detect ChArUco board
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            corners, ids, rejected = cv2.aruco.detectMarkers(gray, self.dictionary)

            if len(corners) > 0:
                response, charuco_corners, charuco_ids = cv2.aruco.interpolateCornersCharuco(
                    corners, ids, gray, self.board
                )
                if response > 0:
                    cv2.aruco.drawDetectedCornersCharuco(cv_image, charuco_corners, charuco_ids)
                    quality = f"Good ({response} corners)"
                else:
                    quality = "Poor (No charuco corners)"
            else:
                quality = "Poor (No markers detected)"

            # Convert OpenCV image to PIL Image
            image = Image.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))
            
            # Get the size of the image label
            label_width = self.image_labels[index].winfo_width()
            label_height = self.image_labels[index].winfo_height()
            
            # Resize image to fit the label while maintaining aspect ratio
            image.thumbnail((label_width, label_height), Image.LANCZOS)
            
            photo = ImageTk.PhotoImage(image)
            self.image_labels[index].config(image=photo)
            self.image_labels[index].image = photo  # Keep a reference
            self.quality_labels[index].config(text=f"Quality: {quality}")
            self.status_label.config(text=f"Frame {remote_path} displayed successfully")
        except Exception as e:
            self.status_label.config(text=f"Error displaying image from {ssh_config['hostname']}: {str(e)}")

    def on_closing(self):
        self.client.loop_stop()
        self.client.disconnect()
        self.master.destroy()

root = tk.Tk()
gui = CameraControlGUI(root)
root.mainloop()