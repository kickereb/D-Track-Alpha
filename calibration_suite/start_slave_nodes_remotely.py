import argparse
import os
import threading
import logging
from fabric import Connection

PATH_TO_MAIN = "/home/dtrack/dev/dtrack"

def setup_logging():
    logging.basicConfig(filename='mqtt_subscribers.log', level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')

def ping(host):
    response = os.system(f"ping -c 1 {host}")
    return response == 0

def start_subscriber(host):
    if not ping(host):
        logging.warning(f"Host {host} is not reachable")
        return

    logging.info(f"Starting subscriber on {host}")
    try:
        connection = Connection(host, user="dtrack", connect_kwargs={"password": "dtrack"})
        result = connection.run(f"cd {PATH_TO_MAIN} && python mqtt_subscriber.py", pty=True)
        logging.info(f"Subscriber on {host} output: {result.stdout}")
    except Exception as e:
        logging.error(f"Error starting subscriber on {host}: {str(e)}")

def start_subscribers(hosts):
    threads = []
    for host in hosts:
        thread = threading.Thread(target=start_subscriber, args=(host,))
        thread.start()
        threads.append(thread)

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

def main():
    parser = argparse.ArgumentParser(description="Start MQTT subscribers on Raspberry Pis")
    parser.add_argument("hosts", nargs="+", help="List of host IPs")
    args = parser.parse_args()

    setup_logging()
    start_subscribers(args.hosts)

if __name__ == "__main__":
    main()