import sys
import timefrom datetime import datetime

def log(message):
    timestamp = datetime.now().strftime('%H:%M:%S.%f')
    print(f"[{timestamp}] {message}")
    sys.stdout.flush()