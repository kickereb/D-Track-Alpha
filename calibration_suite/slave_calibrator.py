import paho.mqtt.client as mqtt
from picamera2 import Picamera2
from datetime import datetime
import os
import json
import time
from libcamera import controls
import argparse

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

def take_photo(frame_number):
    # timestamp = int(time.time_ns())
    # filename = os.path.join(PHOTOS_DIR, f"{frame_number}_{timestamp}.jpg")
    filename = os.path.join(PHOTOS_DIR, f"{frame_number}.jpg")
    
    picam2.capture_file(filename)
    print(f"Photo taken: {filename}")

def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    client.subscribe("dtrack/take_photo")

def on_message(client, userdata, msg):
    print(f"Received message: {msg.topic} {str(msg.payload)}")
    if msg.topic == "dtrack/take_photo":
        try:
            frame_data = json.loads(msg.payload)
            frame_number = frame_data['frame']
            take_photo(frame_number)
        except json.JSONDecodeError:
            print(f"Invalid JSON payload: {msg.payload}")
        except KeyError:
            print(f"Missing 'frame' key in payload: {msg.payload}")

def main(broker_ip, broker_port):
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(broker_ip, broker_port, 60)

    try:
        print("Camera initialized")
        print("MQTT client initialized and waiting for commands")
        client.loop_forever()
    except KeyboardInterrupt:
        print("Script terminated by user")
    finally:
        picam2.stop()
        client.disconnect()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start the slave calibration software for a camera node.")
    parser.add_argument("broker_ip", default="192.168.65.1", help="IP address of the MQTT broker")
    parser.add_argument("broker_port", type=int, default=1883, help="Port number of MQTT broker")
    args = parser.parse_args(broker_ip, broker_port)

    main(broker_ip, broker_port)