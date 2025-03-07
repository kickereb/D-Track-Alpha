#!/bin/bash

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Update and upgrade system packages on fresh PI
apt-get update
apt-get upgrade

# Create a temporary directory for downloads
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

# Get necessary scripts for ArduCAM
wget -O install_pivariety_pkgs.sh https://github.com/ArduCAM/Arducam-Pivariety-V4L2-Driver/releases/download/install_script/install_pivariety_pkgs.sh
chmod +x install_pivariety_pkgs.sh
./install_pivariety_pkgs.sh -p libcamera_dev
./install_pivariety_pkgs.sh -p libcamera_apps

CONFIG_FILE="/boot/firmware/config.txt"
# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: $CONFIG_FILE not found"
    exit 1
fi

# Check if the line already exists
if grep -q "^dtoverlay=arducam-64mp" "$CONFIG_FILE"; then
    echo "dtoverlay=arducam-64mp already exists in config.txt"
    # Cleanup before exit
    cd /
    rm -rf "$TEMP_DIR"
    exit 0
fi

# Create a backup of the original file
cp "$CONFIG_FILE" "${CONFIG_FILE}.backup"

# Add the new line after [all]
sed -i '/\[all\]/a dtoverlay=arducam-64mp' "$CONFIG_FILE"

if [ $? -eq 0 ]; then
    echo "Successfully added dtoverlay=arducam-64mp to config.txt"
    echo "A backup was created at ${CONFIG_FILE}.backup"
    
    # Cleanup downloaded files
    cd /
    rm -rf "$TEMP_DIR"
    
    echo "Cleaned up temporary installation files"
    echo "System needs to be rebooted for changes to take effect"
    read -p "Would you like to reboot now? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        reboot
    fi
else
    echo "Error: Failed to modify config.txt"
    # Cleanup even if there was an error
    cd /
    rm -rf "$TEMP_DIR"
    exit 1
fi