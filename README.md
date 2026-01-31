# Sora Video Generator

A local webapp for generating short-form videos using OpenAI's Sora 2 API. Designed for creating YouTube Shorts and similar vertical video content.

## Features

- Generate multiple video clips from scene descriptions
- Automatic story consistency processing to maintain character and setting continuity across clips
- Configurable clip duration (4, 8, or 12 seconds)
- Configurable number of clips (1-10)
- Global style/vibe settings applied to all clips
- Automatic clip stitching into final video
- Real-time cost estimation
- Clean video output with ambient audio (add your own voiceover and captions)

## Requirements

- Python 3.10+
- FFmpeg installed and in PATH
- OpenAI API key with Sora 2 access

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/sora-video-generator.git
cd sora-video-generator
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

4. Install FFmpeg if not already installed:
- Windows: `winget install Gyan.FFmpeg`
- Mac: `brew install ffmpeg`
- Linux: `sudo apt install ffmpeg`

## Usage

1. Start the server:
```bash
python app.py
```

2. Open http://localhost:5000 in your browser

3. Enter your scene descriptions (one sentence per clip)

4. Set your global style/vibe

5. Choose clip duration and number of clips

6. Click "Generate Video"

7. Download your finished video

## Project Structure

```
├── app.py                 # Flask backend
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── static/
│   ├── style.css         # Frontend styling
│   └── app.js            # Frontend logic
├── templates/
│   └── index.html        # Main page
├── services/
│   ├── text_processor.py # Scene text processing
│   ├── story_processor.py # Story consistency via GPT
│   ├── sora_client.py    # Sora 2 API client
│   └── video_processor.py # FFmpeg video processing
└── output/               # Generated videos (gitignored)
```

## API Costs

Sora 2 API pricing (as of 2026):
- 4 second clip: ~$0.40
- 8 second clip: ~$0.80
- 12 second clip: ~$1.20

The app displays estimated costs before generation.

## License

MIT
