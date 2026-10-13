"""
Voiceover: tries edge-tts first, falls back to gTTS if Microsoft blocks us.
Reads the script text from script.json and saves the audio to OUTPUT_FILE.
"""

import asyncio
import json
import subprocess
import sys

OUTPUT_FILE = "voiceover.mp3"      # <-- must match the name your video step expects
VOICE = "en-US-AndrewNeural"       # edge-tts voice
SPEED = 1.1                        # gTTS is slow; 1.1 = 10% faster


def load_text():
    with open("script.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    for key in ("script", "text", "voiceover", "narration"):
        if data.get(key):
            return data[key]
    print(f"Could not find the script text. Keys in script.json: {list(data.keys())}")
    sys.exit(1)


async def edge_voiceover(text):
    import edge_tts
    communicate = edge_tts.Communicate(text, VOICE)
    await asyncio.wait_for(communicate.save(OUTPUT_FILE), timeout=60)


def gtts_voiceover(text):
    from gtts import gTTS
    raw = "voiceover_raw.mp3"
    gTTS(text=text, lang="en", tld="com").save(raw)
    # Speed it up a little with ffmpeg (already installed in your workflow)
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", raw, "-filter:a", f"atempo={SPEED}", OUTPUT_FILE],
            check=True, capture_output=True,
        )
    except Exception as e:
        print(f"  [!] Speed-up failed ({e}), using normal speed.")
        subprocess.run(["cp", raw, OUTPUT_FILE], check=True)


def main():
    text = load_text()
    print("Generating voiceover...")
    try:
        asyncio.run(edge_voiceover(text))
        print("  [+] Voiceover made with edge-tts.")
        return
    except Exception as e:
        print(f"  [!] edge-tts failed: {e}")
        print("  [i] Switching to gTTS...")
    gtts_voiceover(text)
    print("  [+] Voiceover made with gTTS.")


if __name__ == "__main__":
    main()
