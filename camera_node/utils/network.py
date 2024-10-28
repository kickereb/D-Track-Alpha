import netifaces as ni
import argparse
import socket
import subprocess
import platform
import threading
import time
from typing import Dict, Tuple

def get_ip_address(interface='eth0'):
    return ni.ifaddresses(interface)[ni.AF_INET][0]['addr']

def discover_dtrack_hosts() -> Dict[str, Tuple[str, int, int]]:
    """
    Discover hosts with 'dtrack' in their hostname on the local network.
    
    Returns:
        Dict[str, Tuple[str, int, int]]: Dictionary of neighbors in the format 
        {node_id: (ip, port, status)}
    """
    neighbors = {}
    base_port = 5050  # Default starting port for discovered nodes
    
    # Get the local IP to determine network range
    local_ip = get_ip_address()
    ip_parts = local_ip.split('.')
    network_prefix = '.'.join(ip_parts[:-1])
    
    # Perform the network scan
    print("Discovering dtrack nodes on the network...")
    _scan_network(network_prefix, neighbors, base_port, local_ip)
    return neighbors

def _ping_host(ip: str) -> bool:
    """
    Private method to ping a host and check if it's reachable.
    
    Args:
        ip: IP address to ping
        
    Returns:
        bool: True if host is reachable, False otherwise
    """
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    command = ['ping', param, '1', ip]
    return subprocess.call(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0

def _check_hostname(ip: str) -> str:
    """
    Private method to get the hostname of an IP address.
    
    Args:
        ip: IP address to check
        
    Returns:
        str: Hostname if found, empty string otherwise
    """
    try:
        hostname = socket.gethostbyaddr(ip)[0]
        return hostname.lower()
    except (socket.herror, socket.gaierror):
        return ""

def _scan_host(ip: str, neighbors: Dict[str, Tuple[str, int, int]], base_port: int, local_ip: str) -> None:
    """
    Private method to scan a single host and add to neighbors if it's a dtrack node.
    
    Args:
        ip: IP address to scan
        neighbors: Dictionary to store discovered neighbors
        base_port: Starting port number for discovered nodes
        local_ip: Local machine's IP address to skip
    """
    if ip != local_ip and _ping_host(ip):
        hostname = _check_hostname(ip)
        if 'dtrack' in hostname:
            # Extract node ID from hostname if possible, otherwise use IP
            try:
                node_id = hostname.split('-')[1]  # Assuming format: dtrack-{node_id}
            except IndexError:
                node_id = ip.split('.')[-1]
            
            # Assign sequential ports starting from base_port
            with threading.Lock():
                port = base_port + len(neighbors)
                neighbors[node_id] = (ip, port, 1)  # Status 1 indicates active

def _scan_network(network_prefix: str, neighbors: Dict[str, Tuple[str, int, int]], 
                 base_port: int, local_ip: str) -> None:
    """
    Private method to scan the network for hosts.
    
    Args:
        network_prefix: First three octets of the IP range to scan
        neighbors: Dictionary to store discovered neighbors
        base_port: Starting port number for discovered nodes
        local_ip: Local machine's IP address to skip
    """
    threads = []
    for i in range(1, 255):
        ip = f"{network_prefix}.{i}"
        thread = threading.Thread(
            target=_scan_host, 
            args=(ip, neighbors, base_port, local_ip)
        )
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
