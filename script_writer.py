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

GEMINI_MODELS = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash"]
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    + GEMINI_MODELS[0]
    + ":generateContent?key="
    + config.GEMINI_API_KEY
)

# ---- Script reserve (buffer) ------------------------------------------------
# Keeps up to BUFFER_TARGET pre-made Gemini scripts committed to the repo.
# When Gemini is down, the bot uploads from this reserve instead of a fallback.
BUFFER_FILE = "script_buffer.json"
BUFFER_TARGET = 10
PENDING_PARTS_FILE = "pending_parts.json"
MAX_WORDS_PER_VIDEO = 190  # ~60-70s of speech — big topics get split into parts
PART_TITLE_SUFFIX = " | Part {n} of {total}"

FALLBACK_INTRO = [
    "You might have wondered about this before, and today we're answering it. ",
    "Here is a fascinating question you've probably asked yourself at least once. ",
    "Most people don't know this, but the science behind it is genuinely cool. ",
    "Ready for a quick dose of science that will change how you see the world? ",
]

FALLBACK_ANSWERS = [
    "The short answer is: it comes down to the laws of physics and chemistry. ",
    "Scientists have studied this closely, and the short answer is that the "
    "details come down to how the universe actually behaves. ",
    "The science behind it is genuinely elegant, and once you know the short "
    "answer, it clicks: it's all about cause and effect. ",
    "In short, it's not magic — it's how the natural world works, and the "
    "answer is more surprising than you'd think. ",
]

FALLBACK_EXPLANATIONS = [
    "When you break it down, the real mechanism involves energy, matter, and "
    "the rules they follow. Different pieces interact, and the combined effect "
    "is exactly what you observe every single day. ",
    "The key is that several small forces combine into one big result. Each "
    "part on its own is simple, but together they create the effect you're "
    "asking about. ",
    "At its core, it's a balance of competing effects. Change one factor and "
    "the outcome shifts — which is exactly why it works the way it does. ",
    "What makes it fascinating is that the same principle shows up everywhere "
    "in nature, from tiny particles all the way up to huge systems. ",
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
    # The script now actually ANSWERS the question instead of only posing it.
    script = (
        random.choice(FALLBACK_INTRO)
        + f"Today's question is: {question} "
        + random.choice(FALLBACK_ANSWERS)
        + random.choice(FALLBACK_EXPLANATIONS)
        + f"So when you look at {subject}, you're seeing the outcome of those "
        f"forces working together — and now you know exactly why it happens. "
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

PROMPT_TEMPLATE = """You are writing a YouTube Shorts script for an \
educational "Science Explained" channel targeting a USA audience. The topic/question is:

"{topic}"

CRITICAL RULES:
- The script MUST fully answer the question. Do NOT just pose it.
- Length: 140-220 words, spoken at a relaxed pace. That is roughly 55 to 90 \
seconds of video. Shorts can be up to 3 minutes, so you have room to \
actually explain the answer properly.
- If the topic is naturally big, cover the most important, complete \
explanation in one video — do not tease "part 2" inside the script.

Write:
1. A clear, curiosity-driven TITLE (under 60 characters, phrased as a question or \
"How/Why X" statement)
2. A VOICEOVER SCRIPT (spoken, friendly teacher tone, starts by posing the \
question or hook, then ANSWERS it with the real science, ends with a clear \
takeaway — NO jargon without explaining it)
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
    """Call Gemini, trying each model in GEMINI_MODELS with retries.

    Returns the raw text from the first model that answers.
    """
    last_error = None
    for model in GEMINI_MODELS:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            + model
            + ":generateContent?key="
            + config.GEMINI_API_KEY
        )
        for attempt in range(4):
            try:
                resp = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=90)
                if resp.status_code in (429, 500, 502, 503, 504):
                    last_error = Exception(f"{model} returned {resp.status_code}")
                    wait = 5 * (2 ** attempt)
                    print(f"  [!] {model} returned {resp.status_code} "
                          f"(attempt {attempt + 1}/4) — retrying in {wait}s")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                data = resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as e:
                last_error = e
                print(f"  [!] {model} attempt {attempt + 1} failed: {e}")
                if attempt < 3:
                    wait = 5 * (attempt + 1)
                    print(f"      Waiting {wait}s before retrying...")
                    time.sleep(wait)
        print(f"  [i] Moving on from {model}...")
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


def pop_script_from_buffer(topic: str = "") -> dict:
    """Take a script off the reserve. Returns None if empty.

    Prefers a script whose source_topic matches the current topic so the
    uploaded video stays relevant to the topic that was picked today.
    """
    buf = load_buffer()
    if not buf:
        return None
    chosen_idx = 0
    if topic:
        tl = str(topic).lower()
        for i, s in enumerate(buf):
            if str(s.get("source_topic", "")).lower() == tl:
                chosen_idx = i
                break
    script = buf.pop(chosen_idx)
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


def load_pending_parts() -> list:
    """Read pending_parts.json — leftover chunks of big scripts, uploaded one per run."""
    if os.path.exists(PENDING_PARTS_FILE):
        try:
            with open(PENDING_PARTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except Exception as e:
            print(f"  [!] Could not read {PENDING_PARTS_FILE}: {e}")
    return []


def save_pending_parts(parts: list):
    with open(PENDING_PARTS_FILE, "w", encoding="utf-8") as f:
        json.dump(parts, f, indent=2)


def pop_pending_part() -> dict:
    """Take the next queued script part for today's upload. None if empty."""
    parts = load_pending_parts()
    if not parts:
        return None
    part = parts.pop(0)
    save_pending_parts(parts)
    return part


def split_script_into_parts(result: dict) -> list:
    """If a script is too long for one Short, split it into sequential parts.

    Returns a list of part dicts (each a full script.json-shaped record).
    If the script fits in one video, returns [result] unchanged.
    """
    words = str(result.get("script", "")).split()
    if len(words) <= MAX_WORDS_PER_VIDEO:
        return [result]

    total = -(-len(words) // MAX_WORDS_PER_VIDEO)  # ceil division
    base_title = str(result.get("title", "Science Explained")).strip()
    # strip any previous " | Part x of y" suffix so we don't double-append
    if " | Part " in base_title:
        base_title = base_title.split(" | Part ")[0]

    parts = []
    for i in range(total):
        chunk_words = words[i * MAX_WORDS_PER_VIDEO:(i + 1) * MAX_WORDS_PER_VIDEO]
        chunk = " ".join(chunk_words)
        part = {
            "title": f"{base_title}{PART_TITLE_SUFFIX.format(n=i + 1, total=total)}"[:100],
            "script": chunk,
            "description": result.get("description", ""),
            "used_fallback": result.get("used_fallback", False),
            "source_topic": result.get("source_topic", ""),
            "source_url": result.get("source_url", ""),
            "part_of_series": base_title,
        }
        parts.append(part)
    return parts


def main():
    # If a big topic was split earlier, finish its remaining parts FIRST,
    # one per run, before starting a new topic.
    pending = pop_pending_part()
    if pending is not None:
        print(f"  [i] Continuing a big topic: uploading Part: {pending['title']}")
        with open("script.json", "w") as f:
            json.dump(pending, f, indent=2)
        print("\nTitle:", pending["title"])
        print("\nScript:\n", pending["script"])
        print("\nSaved to script.json")
        return

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
        result = pop_script_from_buffer(topic["topic"])
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

    # If the script is too long for one Short, split it: upload Part 1 now,
    # queue the rest so the NEXT runs upload one part at a time.
    parts = split_script_into_parts(result)
    if len(parts) > 1:
        today = parts[0]
        save_pending_parts(parts[1:])
        print(f"  [i] Big topic split into {len(parts)} parts. "
              f"Uploading Part 1 now; {len(parts) - 1} part(s) queued for next runs.")
    else:
        today = parts[0]

    with open("script.json", "w") as f:
        json.dump(today, f, indent=2)

    # Keep the reserve topped up. Only when Gemini is up (today's call
    # succeeded) — if it's down, a refill attempt would just fail and waste
    # the job's time. Never refills by stashing today's used script.
    if not result.get("used_fallback"):
        refill_buffer()

    print("\nTitle:", today["title"])
    print("\nScript:\n", today["script"])
    print("\nSaved to script.json")

if __name__ == "__main__":
    main()
