#!/bin/bash

# Check if script is run as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root"
   exit 1
fi

# Function to install NTP if not present
install_ntp() {
    if ! command -v ntpd &> /dev/null; then
        echo "Installing NTP..."
        if command -v apt-get &> /dev/null; then
            apt-get update && apt-get install -y ntp
        elif command -v yum &> /dev/null; then
            yum install -y ntp
        else
            echo "Unsupported package manager. Please install NTP manually."
            exit 1
        fi
    fi
}

# Function to backup existing config
backup_config() {
    if [ -f /etc/ntp.conf ]; then
        cp /etc/ntp.conf /etc/ntp.conf.backup.$(date +%Y%m%d_%H%M%S)
    fi
}

# Function to configure master node (stratum 0)
configure_master() {
    cat > /etc/ntp.conf << EOL
# Master NTP Server Configuration (Stratum 0)
restrict default kod nomodify notrap nopeer noquery
restrict -6 default kod nomodify notrap nopeer noquery
restrict 127.0.0.1
restrict -6 ::1

# Local clock as reference
server 127.127.1.0
fudge 127.127.1.0 stratum 0

# Drift file
driftfile /var/lib/ntp/drift

# Logging
logfile /var/log/ntp.log
EOL
}

# Function to configure client node (stratum 1)
configure_client() {
    local master_ip=$1
    if [ -z "$master_ip" ]; then
        echo "Error: Master IP address is required for client configuration"
        exit 1
    fi

    cat > /etc/ntp.conf << EOL
# Client NTP Configuration (Stratum 1)
restrict default kod nomodify notrap nopeer noquery
restrict -6 default kod nomodify notrap nopeer noquery
restrict 127.0.0.1
restrict -6 ::1

# Master server
server $master_ip prefer iburst

# Drift file
driftfile /var/lib/ntp/drift

# Logging
logfile /var/log/ntp.log
EOL
}

# Parse command line arguments
MASTER_FLAG=false
MASTER_IP=""

while getopts ":m:i:" opt; do
    case $opt in
        m)
            MASTER_FLAG=true
            ;;
        i)
            MASTER_IP="$OPTARG"
            ;;
        \?)
            echo "Invalid option: -$OPTARG"
            echo "Usage: $0 [-m] [-i master_ip]"
            echo "  -m: Configure as master node"
            echo "  -i: Specify master node IP address (required for client nodes)"
            exit 1
            ;;
    esac
done

# Main execution
install_ntp
backup_config

if [ "$MASTER_FLAG" = true ]; then
    echo "Configuring as master node (stratum 0)..."
    configure_master
else
    if [ -z "$MASTER_IP" ]; then
        echo "Error: Master IP address (-i) is required for client configuration"
        exit 1
    fi
    echo "Configuring as client node (stratum 1)..."
    configure_client "$MASTER_IP"
fi

# Restart NTP service
if systemctl is-active --quiet ntp; then
    systemctl restart ntp
elif systemctl is-active --quiet ntpd; then
    systemctl restart ntpd
else
    echo "Warning: Could not detect NTP service. Please restart it manually."
fi

echo "NTP configuration completed successfully!"