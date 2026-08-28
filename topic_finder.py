"""
YouTube Shorts Topic Finder — "Science Explained" Niche (USA audience)
------------------------------------------------------------
Pulls interesting science/education questions and explainer topics
from Reddit, with a built-in fallback list so it never gets stuck.

Output: topics.json
"""

import requests
import json
import re
import os
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
]

def clean_title(title: str) -> str:
    title = re.sub(r'^\s*(TIL|ELI5)\s*[:\-]?\s*(that\s+)?', '', title, flags=re.IGNORECASE)
    return title.strip()

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
    if os.path.exists("used_topics.json"):
        with open("used_topics.json", "r") as f:
            return set(t.lower() for t in json.load(f))
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
        key = t["topic"].lower()
        if key in seen or key in used_topics:
            continue
        seen.add(key)
        final_topics.append(t)
        if len(final_topics) >= 20:
            break

    if not final_topics:
        print("\n  [!] No fresh Reddit topics — checking backup topic list.\n")
        import random
        available_fallbacks = [t for t in FALLBACK_TOPICS if t.lower() not in used_topics]
        if not available_fallbacks:
            print("  [!] All backup topics used — reusing the list from scratch.\n")
            available_fallbacks = FALLBACK_TOPICS
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
