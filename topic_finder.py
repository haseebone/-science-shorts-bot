"""
YouTube Shorts Topic Finder — "Science Explained" Niche (USA audience)
------------------------------------------------------------
Order of attempts, each one free:
  1. Reddit (hot + new + top:week + top:month) across 5 subreddits
  2. Saved fallback topics (static list + auto-grown list from step 3)
  3. Gemini generates a fresh batch of topics on the fly (free tier)

Guarantee: never outputs a topic already in used_topics.json.
Only stops the run if ALL THREE sources are exhausted (extremely rare).

Output: topics.json
Side effect: may grow generated_topics.json (new AI-made topics saved
for reuse later — commit this file back to the repo, same as used_topics.json)
"""

import requests
import json
import re
import os
import sys
import random
import time
from datetime import datetime, timezone

SUBREDDITS = [
    "askscience",
    "explainlikeimfive",
    "everythingscience",
    "space",
    "todayilearned",
]

LISTINGS = ["hot", "new", "top"]          # pull all three
TOP_TIME_WINDOWS = ["week", "month"]       # only used for the "top" listing

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

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

GENERATED_TOPICS_FILE = "generated_topics.json"
GEMINI_MODEL = "gemini-1.5-flash"  # free-tier model


def clean_title(title: str) -> str:
    title = re.sub(r'^\s*(TIL|ELI5)\s*[:\-]?\s*(that\s+)?', '', title, flags=re.IGNORECASE)
    return title.strip()


def normalize(topic: str) -> str:
    t = topic.lower()
    t = re.sub(r'[^\w\s]', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def fetch_listing(subreddit: str, listing: str, time_window: str = None, limit: int = 15):
    url = f"https://www.reddit.com/r/{subreddit}/{listing}.json?limit={limit}"
    if listing == "top" and time_window:
        url += f"&t={time_window}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  [!] Could not fetch r/{subreddit} ({listing}{'/' + time_window if time_window else ''}): {e}")
        return []

    posts = []
    for child in data.get("data", {}).get("children", []):
        post = child.get("data", {})
        title = post.get("title", "")
        score = post.get("score", 0)
        if post.get("stickied"):
            continue
        if len(title) < 15 or len(title) > 150:
            continue
        posts.append({
            "topic": clean_title(title),
            "source": f"r/{subreddit} ({listing}{'/' + time_window if time_window else ''})",
            "upvotes": score,
            "url": f"https://reddit.com{post.get('permalink', '')}"
        })
    return posts


def fetch_all_reddit_topics():
    all_topics = []
    for sub in SUBREDDITS:
        for listing in LISTINGS:
            if listing == "top":
                for window in TOP_TIME_WINDOWS:
                    print(f"  -> Checking r/{sub} (top/{window}) ...")
                    all_topics.extend(fetch_listing(sub, "top", window))
                    time.sleep(0.5)  # be polite to Reddit's servers
            else:
                print(f"  -> Checking r/{sub} ({listing}) ...")
                all_topics.extend(fetch_listing(sub, listing))
                time.sleep(0.5)
    return all_topics


def load_used_topics():
    if os.path.exists("used_topics.json"):
        with open("used_topics.json", "r") as f:
            raw = json.load(f)
        return set(normalize(t) for t in raw)
    return set()


def load_generated_topics():
    """Previously AI-generated topics saved from earlier runs."""
    if os.path.exists(GENERATED_TOPICS_FILE):
        with open(GENERATED_TOPICS_FILE, "r") as f:
            return json.load(f)
    return []


def save_generated_topics(topics_list):
    with open(GENERATED_TOPICS_FILE, "w") as f:
        json.dump(topics_list, f, indent=2)


def generate_topics_with_gemini(used_topics: set, count: int = 20):
    """Ask Gemini (free tier) to invent a fresh batch of short-form science
    explainer topics that avoid everything already used. Returns a list of
    plain topic strings, or [] on any failure (never crashes the pipeline)."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("  [!] GEMINI_API_KEY not set — cannot auto-generate topics.")
        return []

    avoid_sample = list(used_topics)[:60]  # keep prompt a reasonable size
    prompt = (
        f"Generate {count} short, curiosity-driven science/education topics "
        f"suitable for 60-second YouTube Shorts explainers, aimed at a US "
        f"general audience. Style examples: 'Why is the sky blue', "
        f"'How do vaccines actually work'. Cover varied subjects: physics, "
        f"biology, space, chemistry, psychology, everyday technology, animals, "
        f"the human body, weather, geology. Do NOT repeat or closely resemble "
        f"any of these already-used topics: {avoid_sample}. "
        f"Reply with ONLY a JSON array of {count} plain topic strings, no "
        f"markdown, no numbering, no extra text."
    )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={api_key}"
    body = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        resp = requests.post(url, json=body, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        text = text.strip()
        text = re.sub(r'^```json\s*|\s*```$', '', text, flags=re.MULTILINE).strip()
        topics = json.loads(text)
        if isinstance(topics, list):
            return [str(t).strip() for t in topics if str(t).strip()]
        return []
    except Exception as e:
        print(f"  [!] Gemini topic generation failed: {e}")
        return []


def main():
    print("Fetching science/education topics for US audience...\n")
    used_topics = load_used_topics()
    all_topics = fetch_all_reddit_topics()
    all_topics.sort(key=lambda x: x["upvotes"], reverse=True)

    seen = set()
    final_topics = []
    for t in all_topics:
        key = normalize(t["topic"])
        if key in seen or key in used_topics:
            continue
        seen.add(key)
        final_topics.append(t)
        if len(final_topics) >= 20:
            break

    if not final_topics:
        print("\n  [!] No fresh Reddit topics — checking saved fallback list.\n")

        generated_pool = load_generated_topics()
        combined_fallbacks = FALLBACK_TOPICS + generated_pool
        available_fallbacks = [t for t in combined_fallbacks if normalize(t) not in used_topics]

        if not available_fallbacks:
            print("  [!] Static + saved fallback topics exhausted.")
            print("  [!] Asking Gemini to generate new topics (free tier)...\n")
            new_topics = generate_topics_with_gemini(used_topics, count=20)
            new_topics = [t for t in new_topics if normalize(t) not in used_topics]

            if new_topics:
                # Save the newly generated batch so future runs can reuse it too
                updated_pool = generated_pool + new_topics
                save_generated_topics(updated_pool)
                available_fallbacks = new_topics
                print(f"  [+] Generated {len(new_topics)} new topics and saved them for future runs.\n")
            else:
                print("  [!] Gemini generation also failed or returned nothing usable.")
                print("  [!] Stopping this run WITHOUT producing a duplicate topic.\n")
                sys.exit(1)

        chosen = random.choice(available_fallbacks)
        final_topics = [{"topic": chosen, "source": "fallback list", "upvotes": 0, "url": ""}]

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "audience": "USA",
        "niche": "science_explained",
        "topics": final_topics
    }

    with open("topics.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nDone! Saved {len(final_topics)} topics to topics.json\n")
    print("Top 5 picks:")
    for i, t in enumerate(final_topics[:5], 1):
        print(f"  {i}. {t['topic']}  (from {t['source']}, {t['upvotes']} upvotes)")


if __name__ == "__main__":
    main()
