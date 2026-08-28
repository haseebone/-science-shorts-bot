import os

# Reuse your SAME Gemini and Pexels keys from the Facts channel — that's fine.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "PASTE_YOUR_GEMINI_KEY_HERE")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "PASTE_YOUR_PEXELS_KEY_HERE")

NICHE = "science_explained"
AUDIENCE = "USA"
UPLOADS_PER_RUN = 1
EDGE_TTS_VOICE = "en-US-JennyNeural"   # calm, clear voice — good fit for explainer content
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
