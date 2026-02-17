import os
import time
from typing import Dict, List
from openai import OpenAI
from config import OPENAI_API_KEY, OUTPUT_DIR


class SoraClient:
    """Client for interacting with OpenAI's Sora 2 API."""

    VALID_DURATIONS = {
        "sora-2": [4, 8, 12],
        "sora-2-pro": [10, 15, 25],
    }

    def __init__(self, clip_duration: int = 4, api_key: str = None, model: str = "sora-2"):
        self.client = OpenAI(api_key=api_key or OPENAI_API_KEY)
        self.model = model if model in self.VALID_DURATIONS else "sora-2"
        # Vertical format for YouTube Shorts (9:16)
        # Valid sizes: 720x1280, 1280x720, 1024x1792, 1792x1024
        self.resolution = "720x1280"
        valid = self.VALID_DURATIONS[self.model]
        self.clip_duration = clip_duration if clip_duration in valid else valid[0]

    def generate_clip(self, clip: Dict, job_id: str, reference_image_path: str = None) -> Dict:
        """
        Generate a single video clip using Sora 2.

        Args:
            clip: Dict with 'id', 'narration', and 'visual_prompt'
            job_id: Unique job identifier for organizing output
            reference_image_path: Optional path to a reference image for visual consistency

        Returns:
            Dict with clip info and video path or error
        """
        full_prompt = self._create_full_prompt(clip)

        try:
            # Build API kwargs
            create_kwargs = dict(
                model=self.model,
                prompt=full_prompt,
                size=self.resolution,
                seconds=str(self.clip_duration),  # "4", "8", or "12"
            )

            # Attach reference image if provided
            ref_file = None
            if reference_image_path and os.path.exists(reference_image_path):
                ref_file = open(reference_image_path, "rb")
                create_kwargs["input_reference"] = ref_file

            # Start video generation
            try:
                response = self.client.videos.create(**create_kwargs)
            finally:
                if ref_file:
                    ref_file.close()

            video_id = response.id

            # Poll for completion
            result = self._wait_for_completion(video_id)

            if result["status"] == "completed":
                # Download the video using the API
                video_path = self._download_video(video_id, job_id, clip["id"])
                return {
                    "clip_id": clip["id"],
                    "status": "completed",
                    "video_path": video_path,
                    "video_id": video_id,
                }
            else:
                return {
                    "clip_id": clip["id"],
                    "status": "failed",
                    "error": result.get("error", "Generation failed"),
                    "video_id": video_id,
                }

        except Exception as e:
            return {
                "clip_id": clip["id"],
                "status": "failed",
                "error": str(e),
            }

    def _create_full_prompt(self, clip: Dict) -> str:
        """Create a full prompt from the visual description."""
        visual = clip.get("visual_prompt", "")
        # Just use visual prompt - no narration, let Sora generate natural ambient sounds
        return visual

    def _wait_for_completion(
        self, video_id: str, timeout: int = 600, poll_interval: int = 5
    ) -> Dict:
        """
        Poll for video generation completion.

        Args:
            video_id: The video generation ID
            timeout: Maximum wait time in seconds
            poll_interval: Time between polls in seconds

        Returns:
            Dict with status and video_id
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                video = self.client.videos.retrieve(video_id)

                if video.status == "completed":
                    return {"status": "completed", "video_id": video_id}

                elif video.status == "failed":
                    error_msg = video.error if video.error else "Unknown error"
                    return {"status": "failed", "error": str(error_msg)}

                # Still processing, wait and retry
                time.sleep(poll_interval)

            except Exception as e:
                return {"status": "failed", "error": str(e)}

        return {"status": "failed", "error": "Timeout waiting for video generation"}

    def _download_video(self, video_id: str, job_id: str, clip_id: int) -> str:
        """Download video using the OpenAI API and save to output directory."""
        # Create job-specific output directory
        job_dir = os.path.join(OUTPUT_DIR, job_id)
        os.makedirs(job_dir, exist_ok=True)

        # Download video content via API
        video_path = os.path.join(job_dir, f"clip_{clip_id:02d}.mp4")

        content = self.client.videos.download_content(video_id)
        content.write_to_file(video_path)

        return video_path

    def generate_all_clips(
        self, clips: List[Dict], job_id: str, progress_callback=None
    ) -> List[Dict]:
        """
        Generate all clips for a video.

        Args:
            clips: List of clip dictionaries
            job_id: Unique job identifier
            progress_callback: Optional callback for progress updates

        Returns:
            List of results for each clip
        """
        results = []

        for i, clip in enumerate(clips):
            if progress_callback:
                progress_callback(i + 1, len(clips), clip["id"])

            result = self.generate_clip(clip, job_id)
            results.append(result)

        return results
