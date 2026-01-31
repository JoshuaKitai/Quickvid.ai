import os
import uuid
import threading
from flask import Flask, render_template, request, jsonify, send_file
from services.text_processor import create_clips, estimate_duration
from services.sora_client import SoraClient
from services.video_processor import VideoProcessor
from services.story_processor import StoryProcessor
from config import OUTPUT_DIR, CLIP_DURATION

app = Flask(__name__)

# Store job status in memory (for simplicity)
jobs = {}


@app.route("/")
def index():
    """Serve the main page."""
    return render_template("index.html")


@app.route("/api/process-text", methods=["POST"])
def process_text():
    """Process input text and return clip breakdown."""
    data = request.get_json()
    text = data.get("text", "").strip()
    style = data.get("style", "").strip()
    clip_duration = data.get("clip_duration", CLIP_DURATION)
    max_clips = data.get("max_clips", 5)

    if not text:
        return jsonify({"error": "No text provided"}), 400

    clips = create_clips(text, style, max_clips)
    duration = estimate_duration(clips, clip_duration)

    return jsonify({
        "clips": clips,
        "total_clips": len(clips),
        "estimated_duration": duration,
        "clip_duration": clip_duration,
        "style": style,
    })


@app.route("/api/generate", methods=["POST"])
def generate():
    """Start video generation job."""
    data = request.get_json()
    clips = data.get("clips", [])
    clip_duration = data.get("clip_duration", CLIP_DURATION)
    global_style = data.get("global_style", "")

    if not clips:
        return jsonify({"error": "No clips provided"}), 400

    # Create job ID
    job_id = str(uuid.uuid4())[:8]

    # Initialize job status
    jobs[job_id] = {
        "status": "queued",
        "progress": 0,
        "total_clips": len(clips),
        "current_clip": 0,
        "clips": clips,
        "clip_duration": clip_duration,
        "global_style": global_style,
        "results": [],
        "output_path": None,
        "error": None,
    }

    # Start generation in background thread
    thread = threading.Thread(target=run_generation, args=(job_id, clips, clip_duration, global_style))
    thread.start()

    return jsonify({"job_id": job_id, "status": "queued"})


def run_generation(job_id: str, clips: list, clip_duration: int = 4, global_style: str = ""):
    """Run video generation in background."""
    try:
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["progress"] = 5

        # Step 1: Enhance prompts with GPT for consistency
        story_processor = StoryProcessor()
        enhanced_clips = story_processor.enhance_prompts(clips, global_style)
        jobs[job_id]["clips"] = enhanced_clips  # Store enhanced clips

        jobs[job_id]["status"] = "generating"
        jobs[job_id]["progress"] = 10

        # Initialize clients
        sora = SoraClient(clip_duration=clip_duration)
        processor = VideoProcessor()

        # Progress callback
        def progress_callback(current, total, clip_id):
            jobs[job_id]["current_clip"] = current
            jobs[job_id]["progress"] = 10 + int((current / total) * 70)  # 10-80% for generation

        # Generate all clips
        results = sora.generate_all_clips(enhanced_clips, job_id, progress_callback)
        jobs[job_id]["results"] = results

        # Check if any clips succeeded
        successful = [r for r in results if r["status"] == "completed"]
        if not successful:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = "All clip generations failed"
            return

        # Process video (concatenate and add captions)
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["progress"] = 85

        final_result = processor.process_video(results, clips, job_id)

        if final_result["status"] == "completed":
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["progress"] = 100
            jobs[job_id]["output_path"] = final_result["output_path"]
        else:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = final_result.get("error", "Processing failed")

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


@app.route("/api/status/<job_id>")
def get_status(job_id):
    """Get job status."""
    if job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404

    job = jobs[job_id]
    return jsonify({
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"],
        "current_clip": job["current_clip"],
        "total_clips": job["total_clips"],
        "error": job["error"],
    })


@app.route("/api/download/<job_id>")
def download(job_id):
    """Download the generated video."""
    if job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404

    job = jobs[job_id]

    if job["status"] != "completed":
        return jsonify({"error": "Video not ready"}), 400

    if not job["output_path"] or not os.path.exists(job["output_path"]):
        return jsonify({"error": "Video file not found"}), 404

    return send_file(
        job["output_path"],
        mimetype="video/mp4",
        as_attachment=True,
        download_name=f"video_{job_id}.mp4",
    )


@app.route("/api/preview/<job_id>")
def preview(job_id):
    """Stream video for preview."""
    if job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404

    job = jobs[job_id]

    if job["status"] != "completed":
        return jsonify({"error": "Video not ready"}), 400

    if not job["output_path"] or not os.path.exists(job["output_path"]):
        return jsonify({"error": "Video file not found"}), 404

    return send_file(job["output_path"], mimetype="video/mp4")


if __name__ == "__main__":
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    app.run(debug=True, port=5000)
