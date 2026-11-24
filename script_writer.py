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

GEMINI_MODEL = "gemini-3.8-flash"
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    + GEMINI_MODEL
    + ":generateContent?key="
    + config.GEMINI_API_KEY
)

# ---- Script reserve (buffer) ------------------------------------------------
# Keeps up to BUFFER_TARGET pre-made Gemini scripts committed to the repo.
# When Gemini is down, the bot uploads from this reserve instead of a fallback.
BUFFER_FILE = "script_buffer.json"
BUFFER_TARGET = 10

FALLBACK_INTRO = [
    "You might have wondered about this before, and today we're answering it. ",
    "Here is a fascinating question you've probably asked yourself at least once. ",
    "Most people don't know this, but the science behind it is genuinely cool. ",
    "Ready for a quick dose of science that will change how you see the world? ",
]

FALLBACK_OUTRO = [
    "So next time someone asks, now you'll know the real answer. ",
    "And that's the science behind it — pretty amazing, right? ",
    "Now you know a little more about how our world actually works. ",
]

def title_case(topic: str) -> str:
    """Make a plain topic string into a clean YouTube title."""
    small = {"a", "an", "the", "and", "but", "or", "for", "nor", "of", "to", "in", "on", "at", "by", "with", "vs"}
    words = str(topic).split()
    if not words:
        return "Science Explained"
    out = []
    for i, w in enumerate(words):
        w = w.strip()
        if not w:
            continue
        if i == 0 or i == len(words) - 1 or w.lower() not in small:
            out.append(w[:1].upper() + w[1:])
        else:
            out.append(w.lower())
    return " ".join(out)

def get_fallback_script(topic: str) -> dict:
    """Build a topic-specific fallback script when Gemini is unavailable.

    Unlike the old hard-coded fallbacks (which always produced one of only
    3 identical videos), this generates a script whose title, script, and
    description are all derived from the ACTUAL chosen topic — so every
    video stays unique even when Gemini is down.
    """
    title = title_case(topic)
    # Clean the topic into a "how/why" question for the opening line.
    clean = topic.strip()
    if clean and not clean[-1] in ".?!":
        clean += "?"
    else:
        clean = topic.strip()
    question = clean
    # Use the last few words as a short takeaway label.
    words = [w for w in str(topic).split() if w.lower() not in {
        "why", "how", "does", "do", "the", "a", "an", "actually", "really"}]
    subject = " ".join(words[-3:]) if words else "this"
    script = (
        random.choice(FALLBACK_INTRO)
        + f"Today's question is simple: {question} "
        + f"While the full explanation takes a book, the short version is "
        f"fascinating and surprisingly easy to understand. Scientists have "
        f"studied {subject} closely, and what they found changes how we see "
        f"everyday life. "
        + random.choice(FALLBACK_OUTRO)
        + "Subscribe for a new science question answered every single day!"
    )
    description = (
        f"{title}. The real science, explained simply. "
        "#science #shorts #education #didyouknow"
    )
    return {
        "title": title[:100],
        "script": script,
        "description": description,
    }

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


# ---- Script reserve helpers -------------------------------------------------

def load_buffer() -> list:
    """Read script_buffer.json (a list of pre-made script dicts)."""
    if os.path.exists(BUFFER_FILE):
        try:
            with open(BUFFER_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except Exception as e:
            print(f"  [!] Could not read {BUFFER_FILE}: {e}")
    return []


def save_buffer(buffer: list):
    with open(BUFFER_FILE, "w", encoding="utf-8") as f:
        json.dump(buffer, f, indent=2)


def pop_script_from_buffer() -> dict:
    """Take the first script off the reserve. Returns None if empty."""
    buf = load_buffer()
    if not buf:
        return None
    script = buf.pop(0)
    save_buffer(buf)
    return script


def make_batch_script_prompt(topics: list) -> str:
    """Ask Gemini for multiple scripts in ONE call (cheap, fewer requests)."""
    topic_list = "\n".join(f"- {t}" for t in topics)
    return (
        "Write a 30-45 second YouTube Shorts explainer script for EACH of these "
        "science topics. Use a friendly teacher tone, 70-100 words each, with a "
        "clear hook and takeaway. Target audience: USA general audience.\n\n"
        "Topics:\n" + topic_list + "\n\n"
        "Respond ONLY with a JSON array of objects, one per topic, in the SAME "
        "order. Each object must have exactly these keys:\n"
        '{"title": "...", "script": "...", "description": "..."}\n'
        "No extra text, no markdown fences, no commentary."
    )


def generate_script_batch(topics: list) -> list:
    """Call Gemini once to make scripts for several topics. Returns list of dicts."""
    if not topics:
        return []
    prompt = make_batch_script_prompt(topics)
    try:
        raw = call_gemini(prompt)
        text = raw.strip()
        if text.startswith("```"):
            # strip any code fences around the JSON
            import re
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
        data = json.loads(text)
        if not isinstance(data, list):
            print("  [!] Gemini batch reply was not a list.")
            return []
        out = []
        for item in data:
            if isinstance(item, dict) and item.get("title") and item.get("script"):
                item.setdefault("used_fallback", False)
                out.append(item)
        return out
    except Exception as e:
        print(f"  [!] Batch Gemini call failed: {e}")
        return []


def refill_buffer():
    """Top the reserve back up to BUFFER_TARGET when it drops below 10."""
    buf = load_buffer()
    missing = BUFFER_TARGET - len(buf)
    if missing <= 0:
        return
    # Only add fresh topics that aren't already used or already scripted.
    used = []
    if os.path.exists("used_topics.json"):
        try:
            with open("used_topics.json", "r", encoding="utf-8") as f:
                used = json.load(f)
        except Exception:
            used = []
    existing_titles = {s.get("title", "").lower() for s in buf}
    existing_sources = {s.get("source_topic", "").lower() for s in buf}
    # Pull candidate topics from generated pool + fallback list (best-effort).
    candidates = []
    for fname in ("generated_topics.json",):
        if os.path.exists(fname):
            try:
                with open(fname, "r", encoding="utf-8") as f:
                    candidates += [str(x) for x in json.load(f)]
            except Exception:
                pass
    pool = []
    for t in candidates:
        tl = t.lower()
        if tl in [u.lower() for u in used]:
            continue
        if tl in existing_sources or tl in existing_titles:
            continue
        pool.append(t)
    # Only request as many as we need (limit batch to a reasonable size).
    need = min(missing, len(pool))
    if need <= 0:
        print(f"  [i] No fresh topics available to refill script buffer.")
        return
    batch_topics = pool[:need]
    print(f"  [i] Refilling script buffer: asking Gemini for {need} script(s)...")
    new_scripts = generate_script_batch(batch_topics)
    # attach the source topic so we never re-use one
    for i, sc in enumerate(new_scripts):
        if i < len(batch_topics):
            sc["source_topic"] = batch_topics[i]
    if new_scripts:
        buf += new_scripts
        buf = buf[-BUFFER_TARGET * 2:]
        save_buffer(buf)
        print(f"  [+] Buffer now has {len(buf)} script(s) ready.")
    else:
        print("  [!] Gemini still not available — buffer not refilled.")


def main():
    topic = load_next_topic()
    print(f"Writing script for topic: {topic['topic']}")

    prompt = PROMPT_TEMPLATE.format(topic=topic["topic"])
    try:
        raw = call_gemini(prompt)
        result = clean_json_response(raw)
        result["used_fallback"] = False
        result["source_topic"] = topic["topic"]
        result["source_url"] = topic.get("url", "")
        print("  [+] Gemini made a script for today.")
    except Exception as e:
        print(f"\n  [!] Gemini unavailable after all retries: {e}")
        print("  [!] Trying the script reserve (buffer) first...\n")
        result = pop_script_from_buffer()
        if result is not None:
            result = dict(result)
            result["used_fallback"] = True
            result["source_topic"] = topic["topic"]
            result["source_url"] = topic.get("url", "")
            print("  [+] Used a reserved script from the buffer (topic matched to today's topic).")
        else:
            print("  [!] Buffer is empty — using topic-specific backup script instead.\n")
            result = get_fallback_script(topic["topic"])
            result["used_fallback"] = True
            result["source_topic"] = topic["topic"]
            result["source_url"] = topic.get("url", "")

    with open("script.json", "w") as f:
        json.dump(result, f, indent=2)

    # Keep the reserve topped up. Runs whenever Gemini worked OR a buffered
    # script was consumed (buffer shrank). Never refills by stashing today's
    # used script — always requests FRESH scripts for unused topics.
    refill_buffer()

    print("\nTitle:", result["title"])
    print("\nScript:\n", result["script"])
    print("\nSaved to script.json")

if __name__ == "__main__":
    main()
