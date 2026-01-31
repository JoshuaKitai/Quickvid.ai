import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Video settings
# Supported sizes: 720x1280, 1280x720, 1024x1792, 1792x1024
VIDEO_WIDTH = 720
VIDEO_HEIGHT = 1280  # 9:16 aspect ratio for YouTube Shorts
CLIP_DURATION = 4  # seconds per clip (Sora supports: 4, 8, or 12)
MAX_CLIPS = 11  # 11 clips x 4 seconds = 44 seconds
MIN_CLIPS = 3

# Output directory
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
