"""
Piece 6: YouTube Uploader
------------------------------------------------------------
Uploads final_video.mp4 + thumbnail.jpg + title/description to
YouTube using the free YouTube Data API (v3).

IMPORTANT — one-time manual step required:
YouTube requires you to personally approve access ONCE (Google's
security rule, can't be skipped). After that one-time approval,
this runs fully unattended forever using a saved "refresh token."

See README.md section "YouTube API setup" for exact steps.
"""

import json
import os
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_FILE = "token.pickle"
CLIENT_SECRET_FILE = "client_secret.json"

def get_authenticated_service():
    creds = None

    # Reuse saved login if we have one (this is what makes it "unattended")
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # ONE-TIME ONLY: opens a browser for you to approve access
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)

    return build("youtube", "v3", credentials=creds)

def upload_video(youtube, video_path, thumbnail_path, title, description):
    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": ["facts", "shorts", "didyouknow"],
            "categoryId": "27",  # Education
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        }
    }

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    print("Uploading video...")
    response = request.execute()
    video_id = response["id"]
    print(f"Uploaded! https://youtube.com/shorts/{video_id}")

    # Thumbnail upload requires phone-verified channel — don't let a failure
    # here undo the successful video upload.
    try:
        youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(thumbnail_path)).execute()
        print("Thumbnail set.")
    except Exception as e:
        print(f"  [!] Could not set thumbnail (video is still live): {e}")
        print("  [!] Tip: verify your channel at youtube.com/verify to enable custom thumbnails.")

    return video_id

def mark_topic_used(topic: str):
    """Add this topic to used_topics.json so it's never picked again."""
    used = []
    if os.path.exists("used_topics.json"):
        with open("used_topics.json", "r") as f:
            used = json.load(f)
    key = topic.lower()
    if key not in [u.lower() for u in used]:
        used.append(topic)
    with open("used_topics.json", "w") as f:
        json.dump(used, f, indent=2)

def main():
    # Authenticate FIRST — this is what creates token.pickle for one-time setup.
    # (If you're just doing the one-time login approval, it's normal to stop
    # here if script.json doesn't exist yet — that file only gets created
    # later when the full pipeline runs.)
    youtube = get_authenticated_service()
    print("\nLogin successful! token.pickle has been created.\n")

    if not os.path.exists("script.json"):
        print("No script.json yet (that's created when the full pipeline runs).")
        print("One-time login setup is complete — you're done with this step.")
        return

    with open("script.json", "r") as f:
        script_data = json.load(f)

    upload_video(
        youtube,
        video_path="final_video.mp4",
        thumbnail_path="thumbnail.jpg",
        title=script_data["title"],
        description=script_data["description"],
    )

    # Remember this topic so it's never used again in a future run
    source_topic = script_data.get("source_topic")
    if source_topic:
        mark_topic_used(source_topic)
        print(f"Marked topic as used: {source_topic}")

if __name__ == "__main__":
    main()
