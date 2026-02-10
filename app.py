import os
import uuid
import threading
from flask import Flask, render_template, request, jsonify, send_file
from services.sora_client import SoraClient
from config import OUTPUT_DIR

app = Flask(__name__)

# Store clip status in memory
clips = {}


@app.route("/")
def index():
    """Serve the main page."""
    return render_template("index.html")


@app.route("/api/generate-clip", methods=["POST"])
def generate_clip():
    """Start generation for a single clip."""
    data = request.get_json()
    prompt = data.get("prompt", "").strip()
    duration = data.get("duration", 4)

    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400

    if duration not in [4, 8, 12]:
        return jsonify({"error": "Duration must be 4, 8, or 12"}), 400

    clip_id = str(uuid.uuid4())[:8]

    clips[clip_id] = {
        "status": "generating",
        "prompt": prompt,
        "duration": duration,
        "video_path": None,
        "error": None,
    }

    thread = threading.Thread(target=_run_clip_generation, args=(clip_id, prompt, duration))
    thread.start()

    return jsonify({"clip_id": clip_id, "status": "generating"})


def _run_clip_generation(clip_id: str, prompt: str, duration: int):
    """Generate a single clip in a background thread."""
    try:
        sora = SoraClient(clip_duration=duration)
        clip_data = {"id": 1, "visual_prompt": prompt}
        result = sora.generate_clip(clip_data, clip_id)

        if result["status"] == "completed":
            clips[clip_id]["status"] = "completed"
            clips[clip_id]["video_path"] = result["video_path"]
        else:
            clips[clip_id]["status"] = "failed"
            clips[clip_id]["error"] = result.get("error", "Generation failed")
    except Exception as e:
        clips[clip_id]["status"] = "failed"
        clips[clip_id]["error"] = str(e)


@app.route("/api/clip-status/<clip_id>")
def clip_status(clip_id):
    """Get status for a single clip."""
    if clip_id not in clips:
        return jsonify({"error": "Clip not found"}), 404

    clip = clips[clip_id]
    return jsonify({
        "clip_id": clip_id,
        "status": clip["status"],
        "error": clip["error"],
    })


@app.route("/api/download-clip/<clip_id>")
def download_clip(clip_id):
    """Download a generated clip."""
    if clip_id not in clips:
        return jsonify({"error": "Clip not found"}), 404

    clip = clips[clip_id]

    if clip["status"] != "completed":
        return jsonify({"error": "Clip not ready"}), 400

    if not clip["video_path"] or not os.path.exists(clip["video_path"]):
        return jsonify({"error": "Video file not found"}), 404

    return send_file(
        clip["video_path"],
        mimetype="video/mp4",
        as_attachment=True,
        download_name=f"clip_{clip_id}.mp4",
    )


@app.route("/api/preview-clip/<clip_id>")
def preview_clip(clip_id):
    """Stream a clip for inline video playback."""
    if clip_id not in clips:
        return jsonify({"error": "Clip not found"}), 404

    clip = clips[clip_id]

    if clip["status"] != "completed":
        return jsonify({"error": "Clip not ready"}), 400

    if not clip["video_path"] or not os.path.exists(clip["video_path"]):
        return jsonify({"error": "Video file not found"}), 404

    return send_file(clip["video_path"], mimetype="video/mp4")


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    app.run(debug=True, port=5000)
