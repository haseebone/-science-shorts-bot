"""
MAIN PIPELINE — runs everything, in order, in one command.
------------------------------------------------------------
Topic -> Script -> Voiceover -> Video -> Thumbnail -> Upload

Run manually with:
    python3 run_pipeline.py

Or let GitHub Actions run this automatically, twice a day, forever,
for free — see .github/workflows/pipeline.yml
"""

import subprocess
import sys

STEPS = [
    ("Finding trending topic...",     "topic_finder.py"),
    ("Writing script...",             "script_writer.py"),
    ("Generating voiceover...",       "voiceover.py"),
    ("Assembling video...",           "video_assembly.py"),
    ("Creating thumbnail...",         "thumbnail.py"),
    ("Uploading to YouTube...",       "upload.py"),
]

def main():
    for message, script in STEPS:
        print(f"\n{'='*50}\n{message}\n{'='*50}")
        result = subprocess.run([sys.executable, script])
        if result.returncode != 0:
            print(f"\n[STOPPED] {script} failed. Fix the error above and re-run.")
            sys.exit(1)

    print("\nAll done! Video is live on your channel.")

if __name__ == "__main__":
    main()
