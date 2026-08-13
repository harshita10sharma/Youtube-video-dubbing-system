from pathlib import Path
from yt_dlp import YoutubeDL

from src.logger import log

def download_video(url: str) -> str:
    Path("data/videos").mkdir(parents=True, exist_ok=True)

    options = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": "data/videos/source.%(ext)s",
        "merge_output_format": "mp4",
        "quiet": True,
        "progress_hooks": [_progress_hook],
    }

    log("Connecting to YouTube and starting download...")

    with YoutubeDL(options) as ydl:
        ydl.extract_info(url, download=True)

    final_path = "data/videos/source.mp4"

    if not Path(final_path).exists():
        raise FileNotFoundError(f"Expected downloaded video at {final_path}")

    log(f"Video downloaded successfully -> {final_path}")
    return final_path

def _progress_hook(d):
    if d["status"] == "downloading":
        percent = d.get("_percent_str", "").strip()
        print(f"      downloading: {percent}", end="\r")
    elif d["status"] == "finished":
        print("      download finished, merging audio+video streams...")