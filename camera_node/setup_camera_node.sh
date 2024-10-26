#!/bin/bash

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Install necessary python packages
apt-get update
sudo apt install python3-venv python3-pip
python3 -m venv camera-node
source camera-node/bin/activate
pip install -y picamera2 paho-mqtt pillow ultralytics