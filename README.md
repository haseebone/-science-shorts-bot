# Fully Automated YouTube Shorts Channel #2 — "Curious Minds Daily" (Science Explained)

Same system as your Facts channel, new topic, new channel. Since you already
did this once, this will go much faster.

**Pipeline:** Science topic → Explainer script → Voiceover → Video → Thumbnail → Upload

---

## What's DIFFERENT from your first channel

1. **New Google account** — needed since this is a separate YouTube channel
2. **New GitHub repository** — keep it separate from `facts-shorts-bot`
   (name it e.g. `science-shorts-bot`)
3. **New YouTube API credentials** — repeat the Google Cloud Console steps
   (new project, enable YouTube Data API, OAuth client, one-time approval)
4. **Reuse your Gemini and Pexels keys** — same free keys work fine here

## What's the SAME (you already know these steps)

- Uploading files to GitHub
- Adding secrets (GEMINI_API_KEY, PEXELS_API_KEY, YT_CLIENT_SECRET_B64, YT_TOKEN_PICKLE_B64)
- The one-time `python upload.py` login approval
- Enabling "Read and write permissions" in repo Settings → Actions → General
- Turning it on via Actions tab → Run workflow

---

## Quick setup checklist

- [ ] Create new Google account
- [ ] Create YouTube channel on it (e.g. "Curious Minds Daily")
- [ ] Create new GitHub repo (same GitHub account is fine): `science-shorts-bot`
- [ ] Upload all files from this folder to that repo (root level, not a subfolder!)
- [ ] Go to Google Cloud Console → new project → enable YouTube Data API v3
- [ ] Create OAuth client ID (Desktop app) → download as `client_secret.json`
- [ ] On your computer: `pip install -r requirements.txt` then `python upload.py`
      to approve access and create `token.pickle`
- [ ] Convert both files to base64, add as GitHub secrets:
      `YT_CLIENT_SECRET_B64`, `YT_TOKEN_PICKLE_B64`
- [ ] Add `GEMINI_API_KEY` and `PEXELS_API_KEY` secrets (reuse your existing keys)
- [ ] Repo Settings → Actions → General → "Read and write permissions" → Save
- [ ] Actions tab → Run workflow → test it

## Branding

Upload `logo.png`, `banner.png`, `watermark.png` in YouTube Studio →
Customization → Branding (same place as last time).

**Suggested channel details:**
- Name: **Curious Minds Daily**
- Handle: **@CuriousMindsDaily**
- Description: "Real science, explained simply, in 60 seconds or less. New videos daily on how the world actually works."
- Keywords: `science, how things work, education, explained, science facts, why does, how does, learn, shorts, curious`

---

## Files in this project

Same structure as your Facts channel — `topic_finder.py` now pulls from
science/education subreddits instead, and `script_writer.py` writes in an
explainer teaching tone instead of quick facts. Everything else
(voiceover, video assembly, thumbnail, upload, scheduler) works identically.

**Cost: still $0**, same as before.
