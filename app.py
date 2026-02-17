import os
import uuid
import threading
from flask import Flask, render_template, request, jsonify, send_file
from PIL import Image
from services.sora_client import SoraClient
from services.story_processor import StoryProcessor
from config import OUTPUT_DIR, VIDEO_WIDTH, VIDEO_HEIGHT

app = Flask(__name__)

# Store clip status in memory
clips = {}


def _resize_cover(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Resize and center-crop an image to exactly target_w x target_h."""
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    new_w = round(src_w * scale)
    new_h = round(src_h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    img = img.crop((left, top, left + target_w, top + target_h))
    return img.convert("RGB")


@app.route("/")
def index():
    """Serve the main page."""
    return render_template("index.html")


@app.route("/api/generate-clip", methods=["POST"])
def generate_clip():
    """Start generation for a single clip (JSON or multipart/form-data)."""
    if request.content_type and request.content_type.startswith("multipart/form-data"):
        prompt = (request.form.get("prompt") or "").strip()
        duration = int(request.form.get("duration", 4))
        ref_file = request.files.get("reference_image")
        api_key = (request.form.get("api_key") or "").strip() or None
        model = (request.form.get("model") or "sora-2").strip()
    else:
        data = request.get_json()
        prompt = data.get("prompt", "").strip()
        duration = data.get("duration", 4)
        ref_file = None
        api_key = (data.get("api_key") or "").strip() or None
        model = data.get("model", "sora-2")

    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400

    valid_durations = SoraClient.VALID_DURATIONS.get(model, [4, 8, 12])
    if duration not in valid_durations:
        return jsonify({"error": f"Duration must be one of {valid_durations} for {model}"}), 400

    clip_id = str(uuid.uuid4())[:8]

    # Save reference image if provided, resized to match Sora's required dimensions
    reference_image_path = None
    if ref_file and ref_file.filename:
        clip_dir = os.path.join(OUTPUT_DIR, clip_id)
        os.makedirs(clip_dir, exist_ok=True)
        reference_image_path = os.path.join(clip_dir, "reference.png")

        img = Image.open(ref_file)
        img = _resize_cover(img, VIDEO_WIDTH, VIDEO_HEIGHT)
        img.save(reference_image_path, format="PNG")

    clips[clip_id] = {
        "status": "generating",
        "prompt": prompt,
        "duration": duration,
        "video_path": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_run_clip_generation,
        args=(clip_id, prompt, duration, reference_image_path, api_key, model),
    )
    thread.start()

    return jsonify({"clip_id": clip_id, "status": "generating"})


def _run_clip_generation(clip_id: str, prompt: str, duration: int, reference_image_path: str = None, api_key: str = None, model: str = "sora-2"):
    """Generate a single clip in a background thread."""
    try:
        sora = SoraClient(clip_duration=duration, api_key=api_key, model=model)
        clip_data = {"id": 1, "visual_prompt": prompt}
        result = sora.generate_clip(clip_data, clip_id, reference_image_path=reference_image_path)

        if result["status"] == "completed":
            clips[clip_id]["status"] = "completed"
            clips[clip_id]["video_path"] = result["video_path"]
        else:
            clips[clip_id]["status"] = "failed"
            clips[clip_id]["error"] = result.get("error", "Generation failed")
    except Exception as e:
        clips[clip_id]["status"] = "failed"
        clips[clip_id]["error"] = str(e)


@app.route("/api/ai-generate-prompts", methods=["POST"])
def ai_generate_prompts():
    """Generate AI prompts from a video description."""
    data = request.get_json()
    description = (data.get("description") or "").strip()
    clip_count = data.get("clip_count", 3)
    duration = data.get("duration", 4)
    api_key = (data.get("api_key") or "").strip() or None
    model = data.get("model", "sora-2")

    if not description:
        return jsonify({"error": "No description provided"}), 400

    if not isinstance(clip_count, int) or clip_count < 1 or clip_count > 10:
        return jsonify({"error": "Clip count must be between 1 and 10"}), 400

    valid_durations = SoraClient.VALID_DURATIONS.get(model, [4, 8, 12])
    if duration not in valid_durations:
        return jsonify({"error": f"Duration must be one of {valid_durations} for {model}"}), 400

    try:
        processor = StoryProcessor(api_key=api_key)
        prompts = processor.generate_prompts_from_description(description, clip_count, duration)
        return jsonify({"prompts": prompts})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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
