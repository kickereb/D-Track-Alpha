# Install necessary python packages
apt-get update
sudo apt install -y python3-venv python3-pip libcap-dev
python3 -m venv --system-site-packages camera-node
source camera-node/bin/activate
pip install paho-mqtt picamera2