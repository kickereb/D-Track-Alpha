#!/bin/bash

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Install necessary python packages
apt-get update
sudo apt install -y python3-venv python3-pip libcap-dev
python3 -m venv --system-site-packages camera-node
source camera-node/bin/activate
pip install paho-mqtt picamera2