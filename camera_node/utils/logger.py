import sys
import time

def log(message):
    print(f"[{time.strftime('%H:%M:%S')}] {message}")
    sys.stdout.flush()