import yt_dlp
import os
import uuid

class DownloadError(Exception):
    pass

def download_video(url: str, download_dir: str) -> str:
    """
    Downloads video from the given URL using yt-dlp.
    Returns the path to the downloaded file.
    Raises DownloadError on failure.
    """
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    filename = f"video_{uuid.uuid4().hex}.mp4"
    output_path = os.path.join(download_dir, filename)
    ydl_opts = {
        'outtmpl': output_path,
        'format': 'mp4/bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        'quiet': True,
        'noplaylist': True,
        'progress_hooks': [],
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
        # Sometimes yt-dlp changes the filename
        if 'requested_downloads' in info and info['requested_downloads']:
            output_path = info['requested_downloads'][0]['filepath']
        elif 'filepath' in info:
            output_path = info['filepath']
        return output_path
    except Exception as e:
        raise DownloadError(str(e))
