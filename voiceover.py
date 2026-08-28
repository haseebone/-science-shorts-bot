"""
Piece 3: Voiceover Generator
------------------------------------------------------------
Reads script.json and turns the script text into an MP3
voiceover using Microsoft Edge's free TTS (no API key, no cost,
no signup — completely free and unlimited).

Output: voiceover.mp3
"""

import asyncio
import json
import edge_tts
import config

async def generate_voiceover(text: str, output_file: str = "voiceover.mp3"):
    communicate = edge_tts.Communicate(text, config.EDGE_TTS_VOICE)
    await communicate.save(output_file)

def main():
    with open("script.json", "r") as f:
        script_data = json.load(f)

    text = script_data["script"]
    print("Generating voiceover...")
    asyncio.run(generate_voiceover(text))
    print("Saved to voiceover.mp3")

if __name__ == "__main__":
    main()
