#!/bin/bash

# Check if script is run as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root"
   exit 1
fi

# Function to install NTPsec if not present
install_ntp() {
    if ! command -v ntpd &> /dev/null; then
        echo "Error: NTPsec is not installed. In an offline environment, please install NTPsec manually using your local package repository."
        exit 1
    fi
}

# Function to backup existing config
backup_config() {
    if [ -f /etc/ntpsec/ntp.conf ]; then
        cp /etc/ntpsec/ntp.conf /etc/ntpsec/ntp.conf.backup.$(date +%Y%m%d_%H%M%S)
    fi
}

# Function to get local network address range
get_local_network() {
    local ip_addr=$(ip route get 1 2>/dev/null | awk '{print $7;exit}')
    local subnet=$(ip -o -f inet addr show | grep "$ip_addr" | awk '{print $4}')
    echo "$subnet"
}

# Function to configure master node (stratum 0)
configure_master() {
    local network=$1
    
    # Ensure directory exists
    mkdir -p /etc/ntpsec
    
    cat > /etc/ntpsec/ntp.conf << EOL
# Master NTP Server Configuration (Stratum 0)
# Restrict access to local network only
restrict default ignore
restrict -6 default ignore
restrict 127.0.0.1
restrict -6 ::1
restrict ${network} mask 255.255.255.0 nomodify notrap

# Local clock as reference
server 127.127.1.0 prefer
fudge 127.127.1.0 stratum 0

# Drift file
driftfile /var/lib/ntpsec/ntp.drift

# Statistics logging
statsdir /var/log/ntpsec/
statistics loopstats peerstats clockstats
filegen loopstats file loopstats type day enable
filegen peerstats file peerstats type day enable
filegen clockstats file clockstats type day enable

# Logging
logfile /var/log/ntpsec/ntp.log

# Disable all pools and default servers
disable pool
disable server
EOL

    # Create stats directory if it doesn't exist
    mkdir -p /var/log/ntpsec/
    chmod 755 /var/log/ntpsec/
}

# Function to configure client node (stratum 1)
configure_client() {
    local master_ip=$1
    local network=$2
    
    # Ensure directory exists
    mkdir -p /etc/ntpsec
    
    cat > /etc/ntpsec/ntp.conf << EOL
# Client NTP Configuration (Stratum 1)
# Restrict access to local network only
restrict default ignore
restrict -6 default ignore
restrict 127.0.0.1
restrict -6 ::1
restrict ${network} mask 255.255.255.0 nomodify notrap

# Master server (local network only)
server $master_ip prefer iburst

# Drift file
driftfile /var/lib/ntpsec/ntp.drift

# Statistics logging
statsdir /var/log/ntpsec/
statistics loopstats peerstats clockstats
filegen loopstats file loopstats type day enable
filegen peerstats file peerstats type day enable
filegen clockstats file clockstats type day enable

# Logging
logfile /var/log/ntpsec/ntp.log

# Disable all pools and default servers
disable pool
disable server
EOL

    # Create stats directory if it doesn't exist
    mkdir -p /var/log/ntpsec/
    chmod 755 /var/log/ntpsec/
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

# Get local network information
LOCAL_NETWORK=$(get_local_network)
if [ -z "$LOCAL_NETWORK" ]; then
    echo "Error: Could not determine local network address"
    exit 1
fi

if [ "$MASTER_FLAG" = true ]; then
    echo "Configuring as master node (stratum 0)..."
    configure_master "$LOCAL_NETWORK"
else
    if [ -z "$MASTER_IP" ]; then
        echo "Error: Master IP address (-i) is required for client configuration"
        exit 1
    fi
    echo "Configuring as client node (stratum 1)..."
    configure_client "$MASTER_IP" "$LOCAL_NETWORK"
fi

# Create and set permissions for log file
mkdir -p /var/log/ntpsec
touch /var/log/ntpsec/ntp.log
chmod 640 /var/log/ntpsec/ntp.log

# Create drift directory
mkdir -p /var/lib/ntpsec
chmod 755 /var/lib/ntpsec

# Restart NTP service
if systemctl is-active --quiet ntpsec; then
    systemctl restart ntpsec
else
    echo "Warning: Could not detect NTPsec service. Please restart it manually."
fi

echo "NTPsec configuration completed successfully!"

# Display status information
echo -e "\nChecking NTPsec status..."
if command -v ntpq &> /dev/null; then
    echo -e "\nPeer status:"
    ntpq -p
    echo -e "\nNTP synchronization status:"
    ntpq -c rv
fi