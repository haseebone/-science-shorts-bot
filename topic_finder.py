"""
YouTube Shorts Topic Finder — "Science Explained" (USA audience), no Reddit.
------------------------------------------------------------
Sources, in order:
  1. Saved pool (static list + generated_topics.json)
  2. Gemini generates new topics when the pool runs low
  3. Offline template generator (no network needed)

Guarantee: never picks a topic that exactly or closely matches anything
in used_topics.json. The chosen topic is written to used_topics.json
immediately. Exits with an error only if every source is exhausted.

Output: topics.json
Side effects: updates used_topics.json, may grow generated_topics.json
(commit both back to the repo in your workflow)
"""

import requests
import json
import re
import os
import sys
import random
import time
from datetime import datetime, timezone

GENERATED_TOPICS_FILE = "generated_topics.json"
USED_TOPICS_FILE = "used_topics.json"
GEMINI_MODELS = ["gemini-2.5-flash", "gemini-flash-latest", "gemini-2.0-flash"]
LOW_POOL_THRESHOLD = 10   # ask Gemini for more when fewer unused topics remain
GEMINI_BATCH_SIZE = 40

FALLBACK_TOPICS = [
    "Why is the sky blue",
    "How do vaccines actually work",
    "Why do we dream when we sleep",
    "How do black holes form",
    "Why does ice float instead of sink",
    "How do airplanes actually stay in the air",
    "Why do we get goosebumps",
    "How does the internet actually work",
    "Why is the ocean salty",
    "How do our eyes see color",
    "What causes lightning and thunder",
    "Why do leaves change color in autumn",
    "How does your brain store memories",
    "Why can't we tickle ourselves",
    "How do GPS satellites know your location",
    "Why do we yawn when others yawn",
    "How does anesthesia actually work",
    "Why does time seem to speed up as we age",
    "How do magnets actually work",
    "Why is space completely silent",
    "How do bees know where flowers are",
    "Why do we get brain freeze",
    "How does your immune system fight viruses",
    "Why do cats always land on their feet",
    "How do rainbows form",
    "Why does the moon look bigger near the horizon",
    "How do submarines control their depth",
    "Why do we get hiccups",
    "How does WiFi actually send data through walls",
    "Why do onions make you cry",
    "How do birds know when to migrate",
    "Why does your voice sound different recorded",
    "How do noise cancelling headphones work",
    "Why do stars twinkle but planets don't",
    "How does your body know when you're full",
    "Why do we have fingerprints",
    "How do volcanoes actually erupt",
    "Why does metal feel colder than wood",
    "How do octopuses change color so fast",
    "Why do we blush when embarrassed",
    "How does a compass actually work",
    "Why do some people get motion sick",
    "How do plants know which way is up",
    "Why does popcorn pop",
    "How do sharks detect blood from so far away",
    "Why do we lose taste when we have a cold",
]

# ---- Offline last-resort generator -----------------------------------------
HOW_SUBJECTS = [
    "a microwave oven", "a refrigerator", "a rocket engine", "a nuclear reactor",
    "a solar panel", "a lithium battery", "a touchscreen", "a camera sensor",
    "an MRI machine", "a pacemaker", "a smoke detector", "a hot air balloon",
    "a parachute", "a seismograph", "a laser", "a 3D printer",
    "a hydrogen fuel cell", "a wind turbine", "a hydroelectric dam", "a jet engine",
    "a helicopter", "a barcode scanner", "a QR code", "a fingerprint scanner",
    "a human heart", "a kidney", "a lung", "a muscle", "a bone heal",
    "a scab form", "a spider web", "a chameleon", "a firefly glow",
    "a bat echolocate", "a snake sense heat", "a camel store water",
    "a hummingbird hover", "a whale dive so deep", "a tornado form",
    "a hurricane form", "a glacier move", "an earthquake happen",
    "a geyser erupt", "a coral reef grow", "a diamond form", "a pearl form",
    "a comet tail form", "a supernova explode", "a neutron star spin",
    "a telescope see the past",
]
WHY_PHRASES = [
    "do we get deja vu", "do we have eyebrows", "do we sneeze", "do we get sunburned",
    "does coffee keep us awake", "does alcohol make us dizzy", "do fingers get wrinkly in water",
    "do we get dizzy when we spin", "do we have a blind spot", "do humans need sleep",
    "does the sun look red at sunset", "is the dead sea so salty", "is lightning zigzag shaped",
    "is the ocean blue", "is Mars red", "does Saturn have rings", "does the moon have phases",
    "do we have leap years", "is the sky dark at night", "does salt melt ice",
    "does bread rise", "does soap kill germs", "do we have different blood types",
    "does spicy food feel hot", "do cats purr", "do dogs tilt their heads",
    "do flamingos stand on one leg", "do zebras have stripes", "do owls turn their heads so far",
    "do mosquitoes bite some people more", "do we get tired after a big meal",
    "does your stomach growl",
]


def offline_topics():
    out = [f"How does {s} actually work" for s in HOW_SUBJECTS]
    out += [f"Why {p}" for p in WHY_PHRASES]
    random.shuffle(out)
    return out


# ---- Duplicate detection ---------------------------------------------------
STOPWORDS = {
    "why", "how", "what", "does", "do", "did", "is", "are", "the", "a", "an",
    "we", "you", "your", "our", "it", "its", "to", "of", "in", "on", "at",
    "and", "or", "actually", "really", "so", "can", "cant", "when", "that",
    "this", "with", "for", "from", "by", "as", "be", "i", "my", "us", "they",
    "their", "work", "works", "get", "gets", "cause", "causes", "instead",
    "even", "much", "many", "every", "single", "if", "than", "then",
}


def normalize(topic: str) -> str:
    t = str(topic).lower().replace("-", " ")
    t = re.sub(r"[^\w\s]", "", t)
    return re.sub(r"\s+", " ", t).strip()


def stem(w: str) -> str:
    """Crude stemmer so 'geysers'/'geyser', 'freezing'/'freeze' match."""
    if len(w) > 4 and w.endswith("ies"):
        w = w[:-3] + "y"
    elif len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        w = w[:-1]
    if len(w) > 5 and w.endswith("ing"):
        w = w[:-3]
    elif len(w) > 4 and w.endswith("ed"):
        w = w[:-2]
    if len(w) > 3 and w.endswith("e"):
        w = w[:-1]
    if len(w) > 3 and w[-1] == w[-2]:
        w = w[:-1]
    return w


def keywords(topic: str) -> set:
    return {stem(w) for w in normalize(topic).split() if w not in STOPWORDS}


class DuplicateChecker:
    """Exact match, OR sharing at least 2 key words that make up 60%+ of the
    shorter topic's key words (catches reworded versions of the same question)."""

    THRESHOLD = 0.6

    def __init__(self, used_topics):
        self.norms = {normalize(t) for t in used_topics}
        self.kws = [keywords(t) for t in used_topics]

    def is_duplicate(self, topic: str) -> bool:
        if normalize(topic) in self.norms:
            return True
        k = keywords(topic)
        if not k:
            return False
        for u in self.kws:
            shared = len(k & u)
            smaller = min(len(k), len(u))
            if smaller >= 2 and shared >= 2 and shared / smaller >= self.THRESHOLD:
                return True
        return False

    def add(self, topic: str):
        self.norms.add(normalize(topic))
        self.kws.append(keywords(topic))


# ---- File helpers ----------------------------------------------------------
def load_json_list(path):
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                data = json.load(f)
            if isinstance(data, list):
                return [str(x) for x in data]
        except Exception as e:
            print(f"  [!] Could not read {path}: {e}")
    return []


def save_generated_topics(topics_list):
    with open(GENERATED_TOPICS_FILE, "w") as f:
        json.dump(topics_list, f, indent=2)


def record_used_topic(topic: str):
    """Write the chosen topic to used_topics.json right away, so it can
    never be picked again even if a later pipeline step fails."""
    used = load_json_list(USED_TOPICS_FILE)
    if normalize(topic) not in {normalize(u) for u in used}:
        used.append(topic)
        with open(USED_TOPICS_FILE, "w") as f:
            json.dump(used, f, indent=2)
        print(f"  [+] Recorded '{topic}' in {USED_TOPICS_FILE}")


# ---- Gemini ----------------------------------------------------------------
def generate_topics_with_gemini(avoid_topics, count=GEMINI_BATCH_SIZE):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("  [!] GEMINI_API_KEY not set — cannot auto-generate topics.")
        return []

    prompt = (
        f"Generate {count} short, curiosity-driven science/education topics "
        f"suitable for 60-second YouTube Shorts explainers, aimed at a US "
        f"general audience. Style examples: 'Why is the sky blue', "
        f"'How do vaccines actually work'. Cover varied subjects: physics, "
        f"biology, space, chemistry, psychology, everyday technology, animals, "
        f"the human body, weather, geology. Every topic must be clearly "
        f"different from each other. Do NOT repeat, reword, or closely "
        f"resemble any of these already-used topics (a reworded version of "
        f"the same question counts as a repeat): {avoid_topics}. "
        f"Reply with ONLY a JSON array of {count} plain topic strings."
    )
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}

    for model in GEMINI_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        for attempt in range(3):
            try:
                resp = requests.post(url, json=body, headers=headers, timeout=45)
                if resp.status_code in (429, 500, 502, 503, 504):
                    wait = 5 * (2 ** attempt)
                    print(f"  [!] {model} returned {resp.status_code} "
                          f"(attempt {attempt + 1}/3) — retrying in {wait}s")
                    time.sleep(wait)
                    continue
                if resp.status_code != 200:
                    print(f"  [!] {model} error {resp.status_code}: {resp.text[:200]}")
                    break
                text = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
