"""
YouTube Shorts Topic Finder — "Science Explained" Niche (USA audience)
------------------------------------------------------------
Pulls interesting science/education questions and explainer topics
from Reddit, with a built-in fallback list so it never gets stuck.

Guarantee: this script will NEVER output a topic that's already in
used_topics.json. If Reddit has nothing fresh AND the fallback list
is fully used up, it stops the run instead of repeating a topic.

Output: topics.json
"""

import requests
import json
import re
import os
import sys
import random
from datetime import datetime, timezone

SUBREDDITS = [
    "askscience",
    "explainlikeimfive",
    "everythingscience",
    "space",
    "todayilearned",
]

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

def clean_title(title: str) -> str:
    """Strip TIL/ELI5 prefixes and normalize punctuation so matching is reliable."""
    title = re.sub(r'^\s*(TIL|ELI5)\s*[:\-]?\s*(that\s+)?', '', title, flags=re.IGNORECASE)
    title = title.strip()
    return title

def normalize(topic: str) -> str:
    """Used ONLY for comparison, not for display/storage. Strips punctuation,
    collapses whitespace, lowercases — so 'Why is the sky blue?' and
    'why is the sky blue' are correctly treated as the same topic."""
    t = topic.lower()
    t = re.sub(r'[^\w\s]', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def fetch_subreddit_hot(subreddit: str, limit: int = 10):
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  [!] Could not fetch r/{subreddit}: {e}")
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
            "source": f"r/{subreddit}",
            "upvotes": score,
            "url": f"https://reddit.com{post.get('permalink', '')}"
        })
    return posts

def load_used_topics():
    """Returns a set of NORMALIZED used topics for safe comparison."""
    if os.path.exists("used_topics.json"):
        with open("used_topics.json", "r") as f:
            raw = json.load(f)
        return set(normalize(t) for t in raw)
    return set()

def main():
    print("Fetching science/education topics for US audience...\n")
    used_topics = load_used_topics()
    all_topics = []

    for sub in SUBREDDITS:
        print(f"  -> Checking r/{sub} ...")
        posts = fetch_subreddit_hot(sub, limit=10)
        all_topics.extend(posts)

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
        print("\n  [!] No fresh Reddit topics — checking backup topic list.\n")
        available_fallbacks = [
            t for t in FALLBACK_TOPICS if normalize(t) not in used_topics
        ]

        if not available_fallbacks:
            # Every Reddit topic AND every fallback topic has already been
            # posted. Do NOT reuse an old topic — stop the run instead.
            print("  [!] All Reddit and fallback topics have been used.")
            print("  [!] Add more topics to FALLBACK_TOPICS to keep the channel running.")
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
