import os
import subprocess
import tempfile
from typing import List, Dict
from config import OUTPUT_DIR, CLIP_DURATION


class VideoProcessor:
    """Process and combine video clips using FFmpeg."""

    def __init__(self):
        # Use explicit path for FFmpeg (winget install location)
        self.ffmpeg_path = r"C:\Users\yasha\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-full_build\bin\ffmpeg.exe"

    def concatenate_clips(self, clip_paths: List[str], output_path: str) -> bool:
        """
        Concatenate multiple video clips into a single video.

        Args:
            clip_paths: List of paths to video clips (in order)
            output_path: Path for the output video

        Returns:
            True if successful, False otherwise
        """
        # Create a temporary file listing all clips
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        ) as f:
            for path in clip_paths:
                # FFmpeg concat requires forward slashes and escaped paths
                escaped_path = path.replace("\\", "/")
                f.write(f"file '{escaped_path}'\n")
            concat_file = f.name

        try:
            cmd = [
                self.ffmpeg_path,
                "-y",  # Overwrite output
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-c", "copy",  # Copy without re-encoding
                output_path,
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True
            )
            return True

        except subprocess.CalledProcessError as e:
            print(f"FFmpeg concat error: {e.stderr}")
            return False

        finally:
            # Clean up temp file
            os.unlink(concat_file)

    def add_captions(
        self,
        video_path: str,
        clips: List[Dict],
        output_path: str,
        clip_duration: int = CLIP_DURATION,
    ) -> bool:
        """
        Add burned-in captions to video.

        Args:
            video_path: Path to input video
            clips: List of clip dictionaries with 'narration' text
            output_path: Path for output video with captions
            clip_duration: Duration of each clip in seconds

        Returns:
            True if successful, False otherwise
        """
        # Generate SRT subtitle file
        srt_path = self._generate_srt(clips, clip_duration)

        try:
            # Use FFmpeg to burn in subtitles
            # Windows paths need special escaping for FFmpeg subtitles filter:
            # - Replace backslashes with forward slashes
            # - Escape colons (C: -> C\\:)
            escaped_srt = srt_path.replace("\\", "/").replace(":", "\\:")

            # Style: white text, black outline, centered at bottom, large font
            subtitle_filter = (
                f"subtitles='{escaped_srt}':"
                f"force_style='Fontsize=24,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,"
                f"Outline=2,Alignment=2,MarginV=50'"
            )

            cmd = [
                self.ffmpeg_path,
                "-y",
                "-i", video_path,
                "-vf", subtitle_filter,
                "-c:a", "copy",  # Keep audio as-is
                output_path,
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True
            )
            return True

        except subprocess.CalledProcessError as e:
            print(f"FFmpeg caption error: {e.stderr}")
            return False

        finally:
            # Clean up SRT file
            if os.path.exists(srt_path):
                os.unlink(srt_path)

    def _generate_srt(
        self, clips: List[Dict], clip_duration: int
    ) -> str:
        """Generate an SRT subtitle file from clips."""
        srt_content = []

        for i, clip in enumerate(clips):
            start_time = i * clip_duration
            end_time = (i + 1) * clip_duration

            # Format timestamps as HH:MM:SS,mmm
            start_str = self._format_srt_time(start_time)
            end_str = self._format_srt_time(end_time)

            narration = clip.get("narration", "")
            # Wrap long lines for better display
            wrapped = self._wrap_text(narration, max_chars=40)

            srt_content.append(f"{i + 1}")
            srt_content.append(f"{start_str} --> {end_str}")
            srt_content.append(wrapped)
            srt_content.append("")  # Blank line between entries

        # Write to temp file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".srt", delete=False, encoding="utf-8"
        ) as f:
            f.write("\n".join(srt_content))
            return f.name

    def _format_srt_time(self, seconds: float) -> str:
        """Format seconds as SRT timestamp (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def _wrap_text(self, text: str, max_chars: int = 40) -> str:
        """Wrap text to fit on screen."""
        words = text.split()
        lines = []
        current_line = []
        current_length = 0

        for word in words:
            if current_length + len(word) + 1 <= max_chars:
                current_line.append(word)
                current_length += len(word) + 1
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
                current_length = len(word)

        if current_line:
            lines.append(" ".join(current_line))

        return "\n".join(lines)

    def process_video(
        self, clip_results: List[Dict], clips: List[Dict], job_id: str
    ) -> Dict:
        """
        Full video processing: concatenate clips and add captions.

        Args:
            clip_results: Results from Sora generation with video paths
            clips: Original clip data with narration text
            job_id: Job identifier

        Returns:
            Dict with status and output path or error
        """
        # Filter successful clips and sort by clip_id
        successful = sorted(
            [r for r in clip_results if r["status"] == "completed"],
            key=lambda x: x["clip_id"],
        )

        if not successful:
            return {"status": "failed", "error": "No clips were generated successfully"}

        # Get video paths in order
        video_paths = [r["video_path"] for r in successful]

        # Create output paths
        job_dir = os.path.join(OUTPUT_DIR, job_id)
        os.makedirs(job_dir, exist_ok=True)

        final_path = os.path.join(job_dir, "final.mp4")

        # Concatenate clips (no captions - user handles that separately)
        if not self.concatenate_clips(video_paths, final_path):
            return {"status": "failed", "error": "Failed to concatenate clips"}

        return {"status": "completed", "output_path": final_path}
