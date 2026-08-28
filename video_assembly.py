"""
Piece 4: Video Assembly
------------------------------------------------------------
Combines: free stock video clips (Pexels) + voiceover.mp3 + captions
into one finished vertical (1080x1920) Shorts video using FFmpeg
(free, open-source, no cost).

Requires FFmpeg installed on your system (free):
  Windows: https://ffmpeg.org/download.html  (or `winget install ffmpeg`)
  Mac:     brew install ffmpeg
  Linux:   sudo apt install ffmpeg

Output: final_video.mp4
"""

import json
import subprocess
import requests
import os
import config

def get_audio_duration(audio_file: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", audio_file],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())

def fetch_stock_clip(query: str, out_path: str = "stock_clip.mp4"):
    """Pull one free vertical-friendly stock clip from Pexels matching the topic."""
    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": config.PEXELS_API_KEY}
    params = {"query": query, "orientation": "portrait", "per_page": 5}
    resp = requests.get(url, headers=headers, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if not data.get("videos"):
        # fallback to a generic "abstract background" clip if no match
        params["query"] = "abstract background"
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        data = resp.json()

    video = data["videos"][0]
    # pick a decent-quality vertical file
    video_file = sorted(
        video["video_files"],
        key=lambda f: f.get("height", 0),
        reverse=True
    )[0]

    video_url = video_file["link"]
    r = requests.get(video_url, stream=True, timeout=60)
    with open(out_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)

    return out_path

def build_caption_srt(script_text: str, duration: float, out_path: str = "captions.srt"):
    """Split script into short caption chunks timed evenly across the audio."""
    words = script_text.split()
    chunk_size = 6  # words per caption line
    chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
    per_chunk = duration / max(len(chunks), 1)

    def fmt(t):
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = int(t % 60)
        ms = int((t - int(t)) * 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    with open(out_path, "w") as f:
        for i, chunk in enumerate(chunks):
            start = i * per_chunk
            end = start + per_chunk
            f.write(f"{i+1}\n{fmt(start)} --> {fmt(end)}\n{chunk}\n\n")

    return out_path

def assemble_video(clip_path: str, audio_path: str, srt_path: str,
                    out_path: str = "final_video.mp4"):
    """Loop/trim the stock clip to match audio length, burn in captions, add voiceover."""
    duration = get_audio_duration(audio_path)

    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1", "-i", clip_path,   # loop clip if shorter than audio
        "-i", audio_path,
        "-t", str(duration),
        "-vf",
        f"scale={config.VIDEO_WIDTH}:{config.VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={config.VIDEO_WIDTH}:{config.VIDEO_HEIGHT},"
        f"subtitles={srt_path}:force_style='FontName=Arial,FontSize=16,"
        f"PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,BorderStyle=1,Outline=2,Alignment=2'",
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-c:a", "aac",
        "-shortest",
        out_path
    ]
    subprocess.run(cmd, check=True)
    return out_path

def main():
    with open("script.json", "r") as f:
        script_data = json.load(f)

    topic = script_data["source_topic"]
    script_text = script_data["script"]

    print("Fetching free stock clip...")
    clip = fetch_stock_clip(topic)

    duration = get_audio_duration("voiceover.mp3")
    print(f"Voiceover duration: {duration:.1f}s")

    print("Building captions...")
    srt = build_caption_srt(script_text, duration)

    print("Assembling final video (this may take a minute)...")
    assemble_video(clip, "voiceover.mp3", srt)

    print("Done! Saved to final_video.mp4")

if __name__ == "__main__":
    main()
