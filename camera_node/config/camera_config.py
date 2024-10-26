from picamera2 import Picamera2
from libcamera import controls
import time
import os

# Ensure the photos directory exists
PHOTOS_DIR = "./data/photos"
os.makedirs(PHOTOS_DIR, exist_ok=True)

def initialise_camera():
    # Initialise the camera
    picam2 = Picamera2()
    capture_config = picam2.create_still_configuration(main={"size": (1920, 1080)})
    picam2.configure(capture_config)

    # Set focus mode to auto
    picam2.set_controls({"AfMode": controls.AfModeEnum.Continuous})

    # Set exposure mode to normal (auto)
    picam2.set_controls({"AeEnable": True})

    picam2.start()
    time.sleep(2)  # Warm-up time
    
    return picam2