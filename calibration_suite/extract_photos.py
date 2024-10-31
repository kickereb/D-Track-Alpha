import os
import argparse
import subprocess
import platform
import shutil
from fabric import Connection

def ping(host):
    """
    Returns True if host responds to a ping request
    """
    # Option for the number of packets as a function of
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    
    # Building the command. Ex: "ping -c 1 google.com"
    command = ['ping', param, '1', host]
    
    return subprocess.call(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0


def download_photos(connection, camera_name, remote_path, local_path):
    try:
        print(f"Downloading photos from {camera_name}")
        # Create local directory if it doesn't exist
        local_camera_path = os.path.join(local_path, camera_name)
        if os.path.exists(local_camera_path):
            print(f"Deleting existing photos in {local_camera_path}")
            shutil.rmtree(local_camera_path)
        os.makedirs(local_camera_path, exist_ok=True)

        # Expand the remote path
        expanded_remote_path = connection.run(f"echo {remote_path}", hide=True).stdout.strip()
        print(f"Expanded remote path: {expanded_remote_path}")
        
        # print(f"Listing contents of remote directory: {expanded_remote_path}")
        result = connection.run(f"ls {expanded_remote_path}", hide=True)
        files = result.stdout.strip().split()
        print(f"Files found: {files}")
        
        for file_name in files:
            remote_file_path = f"{expanded_remote_path}/{file_name}"
            local_file_path = os.path.join(local_camera_path, file_name)
            
            # print(f"Attempting to download: {remote_file_path} to {local_file_path}")
            try:
                connection.get(remote_file_path, local=local_file_path)
                # print(f"Successfully downloaded: {file_name}")
            except Exception as e:
                print(f"Error downloading {file_name}: {str(e)}")
        
        print(f"Finished processing {camera_name}")
    except Exception as e:
        print(f"Error downloading from {camera_name}: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="Download photos from Raspberry Pis")
    parser.add_argument("hosts", nargs="+", help="List of host IPs")
    parser.add_argument("--remote-path", default="/home/dtrack/D-Track-Alpha/calibration_suite/data/photos", help="Remote path on Raspberry Pis")
    parser.add_argument("--local-path", default="~/dev/personal/D-Track-Alpha/calibration_suite/data/photos", help="Local path to save photos")
    parser.add_argument("--password", default="dtrack", help="SSH password for Raspberry Pis")
    args = parser.parse_args()

    # Expand user directory in local path
    local_path = os.path.expanduser(args.local_path)
    
    # Create main local directory if it doesn't exist
    os.makedirs(local_path, exist_ok=True)
    
    # Download photos from each Raspberry Pi
    for i, host in enumerate(args.hosts):
        if not ping(host):
            print(f"Host {host} is not reachable. Skipping...")
            continue
        
        camera_name = f"Cam_{i+1:03d}"
        try:
            with Connection(host, user="dtrack", connect_kwargs={"password": args.password}) as conn:
                print(f"Connected to {host}")
                download_photos(conn, camera_name, args.remote_path, local_path)
        except Exception as e:
            print(f"Failed to connect to {host}: {str(e)}")

if __name__ == "__main__":
    main()