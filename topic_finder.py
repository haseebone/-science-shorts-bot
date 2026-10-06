"""
YouTube Shorts Topic Finder — "Science Explained" (USA audience), no Reddit.
------------------------------------------------------------
Sources, in order:
  1. Saved pool (static list + generated_topics.json)
  2. Gemini generates new topics when the pool runs low
  3. Offline template generator (no network needed)

Guarantee: never picks a topic that exactly or closely matches anything
in used_topics.json. Exits with an error only if every source is exhausted.

Output: topics.json (same format as before)
Side effect: grows generated_topics.json (commit it back to the repo)
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
    "their", "work", "works",
}


def normalize(topic: str) -> str:
    t = str(topic).lower()
    t = re.sub(r"[^\w\s]", "", t)
    return re.sub(r"\s+", " ", t).strip()


def keywords(topic: str) -> set:
    return {w for w in normalize(topic).split() if w not in STOPWORDS}


class DuplicateChecker:
    """Exact match, or one topic's keywords almost fully contained in another's."""

    def __init__(self, used_topics):
        self.norms = {normalize(t) for t in used_topics}
        self.kws = [keywords(t) for t in used_topics]

    def is_duplicate(self, topic: str) -> bool:
        n = normalize(topic)
        if n in self.norms:
            return True
        k = keywords(topic)
        if len(k) < 2:
            return False
        for u in self.kws:
            if len(u) < 2:
                continue
            overlap = len(k & u) / min(len(k), len(u))
            if overlap >= 0.8:
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


# ---- Gemini ----------------------------------------------------------------
def generate_topics_with_gemini(used_topics, count=GEMINI_BATCH_SIZE):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("  [!] GEMINI_API_KEY not set — cannot auto-generate topics.")
        return []

    sample = random.sample(used_topics, min(80, len(used_topics))) if used_topics else []
    prompt = (
        f"Generate {count} short, curiosity-driven science/education topics "
        f"suitable for 60-second YouTube Shorts explainers, aimed at a US "
        f"general audience. Style examples: 'Why is the sky blue', "
        f"'How do vaccines actually work'. Cover varied subjects: physics, "
        f"biology, space, chemistry, psychology, everyday technology, animals, "
        f"the human body, weather, geology. Every topic must be clearly "
        f"different from each other. Do NOT repeat or closely resemble any of "
        f"these already-used topics: {sample}. "
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
                topics = json.loads(text)
                if isinstance(topics, list):
                    cleaned = [str(t).strip() for t in topics if str(t).strip()]
                    if cleaned:
                        print(f"  [+] Gemini ({model}) returned {len(cleaned)} topics.")
                        return cleaned
                print(f"  [!] {model} returned unusable output.")
                break
            except Exception as e:
                print(f"  [!] {model} attempt {attempt + 1} failed: {e}")
                time.sleep(3)
        print(f"  [i] Moving on from {model}...")
    return []


# ---- Main ------------------------------------------------------------------
def main():
    print("Finding a fresh science topic...\n")

    used = load_json_list("used_topics.json")
    checker = DuplicateChecker(used)
    generated_pool = load_json_list(GENERATED_TOPICS_FILE)

    pool = FALLBACK_TOPICS + generated_pool
    available = [t for t in pool if not checker.is_duplicate(t)]
    print(f"  Used topics: {len(used)} | Unused in saved pool: {len(available)}")

    source = "saved pool"

    # Top up from Gemini when the pool is running low
    if len(available) < LOW_POOL_THRESHOLD:
        print("\n  [i] Pool is low — asking Gemini for new topics...\n")
        new_topics = generate_topics_with_gemini(used + pool)

        accepted = []
        pool_checker = DuplicateChecker(used + pool)  # also avoid duplicating the pool
        for t in new_topics:
            if not pool_checker.is_duplicate(t):
                accepted.append(t)
                pool_checker.add(t)  # avoid near-duplicates within the batch too

        if accepted:
            save_generated_topics(generated_pool + accepted)
            available += accepted
            source = "gemini"
            print(f"  [+] Saved {len(accepted)} new topics for future runs.\n")

    # Offline last resort
    if not available:
        print("  [!] Gemini gave nothing — using offline generator.\n")
        available = [t for t in offline_topics() if not checker.is_duplicate(t)]
        source = "offline generator"

    if not available:
        print("  [!] Every source is exhausted. Stopping WITHOUT a duplicate topic.")
        sys.exit(1)

    chosen = random.choice(available)
    final_topics = [{"topic": chosen, "source": source, "upvotes": 0, "url": ""}]

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "audience": "USA",
        "niche": "science_explained",
        "topics": final_topics,
    }
    with open("topics.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"Done! Chosen topic: {chosen}  (from {source})")


if __name__ == "__main__":
    main()
