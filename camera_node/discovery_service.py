import socket
import json
import threading
from typing import Dict, Any, Tuple
from utils.logger import log

class DiscoveryService:
    """
    Service to handle node discovery requests and responses.
    Listens for discovery broadcasts and responds with node information.
    """
    
    def __init__(self, node_id: str, ip: str, port: int):
        self.node_id = node_id
        self.ip = ip
        self.port = port
        self.discovery_port = 5000  # Default port for discovery service
        self.running = True
        self.lock = threading.Lock()
        
    def get_node_info(self) -> Dict[str, Any]:
        """Generate node information packet for discovery responses."""
        return {
            'node_id': self.node_id,
            'ip': self.ip,
            'port': self.port,
            'type': 'dtrack',  # Identifies this as a distributed tracking node
            'status': 1  # 1 indicates active
        }

    def send_discovery_request(self, ip: str) -> Tuple[str, Dict]:
        """
        Send a discovery request to a specific IP
        
        Args:
            ip: IP address to send discovery request to
            
        Returns:
            Tuple of (IP, response_data) if successful, (IP, None) if failed
        """
        try:
            # Create UDP socket for discovery request
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(self.discovery_timeout)
                
                # Prepare discovery request
                request = {
                    'type': 'discovery_request'
                }
                
                # Send request
                sock.sendto(
                    json.dumps(request).encode('utf-8'),
                    (ip, self.discovery_port)
                )
                
                # Wait for response
                try:
                    data, _ = sock.recvfrom(1024)
                    response = json.loads(data.decode('utf-8'))
                    
                    if response.get('type') == 'discovery_response':
                        log(f"Received discovery response from {ip}")
                        return ip, response.get('node')
                except socket.timeout:
                    pass
                except json.JSONDecodeError:
                    pass
                    
        except Exception as e:
            log(f"Error sending discovery request to {ip}: {str(e)}")
            
        return ip, None
        
    def _handle_discovery_request(self, data: bytes, addr: tuple) -> None:
        """
        Handle incoming discovery requests.
        
        Args:
            data: Raw received data
            addr: Address tuple (ip, port) of sender
        """
        try:
            request = json.loads(data.decode('utf-8'))
            print(request)
            
            # Only respond to discovery requests
            if request.get('type') == 'discovery_request':
                # Prepare response
                response = {
                    'type': 'discovery_response',
                    'node': self.get_node_info()
                }
                
                # Send response back to requester
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    sock.sendto(json.dumps(response).encode('utf-8'), addr)
                log(f"Sent discovery response to {addr[0]}:{addr[1]}")
                
        except json.JSONDecodeError:
            log(f"Received invalid discovery request from {addr[0]}:{addr[1]}")
        except Exception as e:
            log(f"Error handling discovery request: {str(e)}")
            
    def run_discovery_listener(self) -> None:
        """
        Run the discovery listener thread.
        Listens for UDP broadcasts and responds with node information.
        """
        try:
            # Create UDP socket for discovery
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                # Allow socket reuse and broadcast
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                
                # Bind to discovery port
                sock.bind(('', self.discovery_port))
                log(f"Discovery service listening on port {self.discovery_port}")
                
                # Set socket timeout to allow checking running flag
                sock.settimeout(1.0)
                
                while self.running:
                    try:
                        data, addr = sock.recvfrom(1024)
                        threading.Thread(
                            target=self._handle_discovery_request,
                            args=(data, addr)
                        ).start()
                    except socket.timeout:
                        continue
                    except Exception as e:
                        log(f"Error in discovery listener: {str(e)}")
                        
        except Exception as e:
            log(f"Fatal error in discovery service: {str(e)}")
        finally:
            log("Discovery service stopped")
            
    def stop(self) -> None:
        """Stop the discovery service."""
        with self.lock:
            self.running = False