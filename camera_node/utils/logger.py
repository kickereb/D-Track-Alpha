import sys
import time

def log(message):
    timestamp = datetime.now().strftime('%H:%M:%S.%f')
    print(f"[{timestamp}] {message}")
    sys.stdout.flush()