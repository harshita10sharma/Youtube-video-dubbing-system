from datetime import datetime

def log(message: str):
    current_time = datetime.now().strftime("%H:%M:%S")
    print(f"[{current_time}] {message}")

def log_error(message: str):
    current_time = datetime.now().strftime("%H:%M:%S")
    print(f"[{current_time}] ERROR: {message}")

def log_success(message: str):
    current_time = datetime.now().strftime("%H:%M:%S")
    print(f"[{current_time}] {message}")