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
