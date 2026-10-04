"""
logger.py
---------
Minimal timestamped logger. Prints to the console and appends every
line to logs/pipeline.log so a run can be inspected afterwards.
"""

from datetime import datetime
from pathlib import Path

LOG_FILE = Path("logs/pipeline.log")


def _emit(line: str):
    print(line)

    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now():%Y-%m-%d} {line}\n")
    except OSError:
        # Logging must never break the pipeline.
        pass


def _stamp() -> str:
    return datetime.now().strftime("%H:%M:%S")


def log(message: str):
    _emit(f"[{_stamp()}] {message}")


def log_error(message: str):
    _emit(f"[{_stamp()}] ERROR: {message}")


def log_success(message: str):
    _emit(f"[{_stamp()}] OK: {message}")
