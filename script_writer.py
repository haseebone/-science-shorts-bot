"""
Piece 2: Script Writer — Science Explained
------------------------------------------------------------
Reads topics.json and writes an explainer-style Shorts script
using Google Gemini's FREE API tier.

Output: script.json
"""

import json
import requests
import time
import random
import os
import config

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-flash-latest:generateContent?key=" + config.GEMINI_API_KEY
)

FALLBACK_SCRIPTS = [
    {
        "title": "Why Is the Sky Blue?",
        "script": "Ever wonder why the sky is blue and not, say, purple or green? "
                   "Sunlight looks white, but it's actually made of every color "
                   "mixed together. As it hits our atmosphere, blue light waves "
                   "are shorter and bounce around way more than red or yellow "
                   "light. That scattered blue light is what reaches your eyes "
                   "from every direction. That's why the whole sky looks blue, "
                   "not just the spot where the sun is.",
        "description": "The real science behind why the sky is blue. "
                        "#science #shorts #education"
    },
    {
        "title": "Why Does Ice Float?",
        "script": "Most solids sink in their own liquid, but ice floats. Here's "
                   "why. When water freezes, its molecules lock into a hexagonal "
                   "pattern that actually takes up more space than liquid water, "
                   "not less. That makes ice slightly less dense, so it floats "
                   "instead of sinking. This one weird property is actually why "
                   "lakes freeze from the top down, letting fish survive winter "
                   "underneath.",
        "description": "Ice floats because of one weird property of water. "
                        "#science #shorts #education"
    },
    {
        "title": "How Do Airplanes Actually Fly?",
        "script": "A 90-ton airplane defying gravity seems impossible, but it "
                   "comes down to wing shape. As air flows over the curved top "
                   "of a wing and flatter bottom, it creates a pressure "
                   "difference, pushing the wing upward. Combine that with "
                   "engines pushing the plane forward fast enough, and that "
                   "upward force, called lift, becomes strong enough to hold "
                   "tons of metal in the sky.",
        "description": "The real physics behind how planes fly. "
                        "#science #shorts #education"
    },
]

def get_fallback_script(topic: str) -> dict:
    chosen = random.choice(FALLBACK_SCRIPTS)
    result = dict(chosen)
    result["source_topic"] = topic
    result["source_url"] = ""
    result["used_fallback"] = True
    return result

PROMPT_TEMPLATE = """You are writing a 30-45 second YouTube Shorts script for an \
educational "Science Explained" channel targeting a USA audience. The topic/question is:

"{topic}"

Write:
1. A clear, curiosity-driven TITLE (under 60 characters, phrased as a question or \
"How/Why X" statement)
2. A VOICEOVER SCRIPT (spoken, friendly teacher tone, 70-100 words, starts by posing \
the question or hook, explains the real science simply, ends with a clear takeaway — \
NO jargon without explaining it)
3. A short YouTube DESCRIPTION (1-2 sentences + 3 relevant hashtags)

Respond ONLY in this exact JSON format, nothing else:
{{
  "title": "...",
  "script": "...",
  "description": "..."
}}
"""

def load_next_topic():
    with open("topics.json", "r") as f:
        data = json.load(f)
    if not data["topics"]:
        raise ValueError("No topics found. Run topic_finder.py first.")
    return data["topics"][0]

def call_gemini(prompt: str) -> str:
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    last_error = None
    for attempt in range(4):
        try:
            resp = requests.post(GEMINI_URL, json=body, timeout=90)
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            last_error = e
            print(f"  [!] Gemini attempt {attempt + 1} failed: {e}")
            if attempt < 3:
                wait = 10 * (attempt + 1)
                print(f"      Waiting {wait}s before retrying...")
                time.sleep(wait)
    raise last_error

def clean_json_response(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        text = text.replace("json", "", 1).strip()
    return json.loads(text)

def main():
    topic = load_next_topic()
    print(f"Writing script for topic: {topic['topic']}")

    prompt = PROMPT_TEMPLATE.format(topic=topic["topic"])
    try:
        raw = call_gemini(prompt)
        result = clean_json_response(raw)
        result["used_fallback"] = False
    except Exception as e:
        print(f"\n  [!] Gemini unavailable after all retries: {e}")
        print("  [!] Using a backup pre-written script instead.\n")
        result = get_fallback_script(topic["topic"])

    result["source_topic"] = topic["topic"]
    result["source_url"] = topic.get("url", "")

    with open("script.json", "w") as f:
        json.dump(result, f, indent=2)

    print("\nTitle:", result["title"])
    print("\nScript:\n", result["script"])
    print("\nSaved to script.json")

if __name__ == "__main__":
    main()
