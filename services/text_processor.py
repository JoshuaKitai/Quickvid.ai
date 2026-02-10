import re
from typing import List, Dict
from config import MAX_CLIPS, MIN_CLIPS


def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences using common delimiters."""
    # Split on ., !, ? followed by space or end of string
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    # Clean up and filter empty sentences
    sentences = [s.strip() for s in sentences if s.strip()]
    return sentences


def create_clips(text: str, style: str = "", max_clips: int = None) -> List[Dict]:
    """
    Split text into clips for video generation.
    Returns a list of clip dictionaries with narration and visual prompt.

    Args:
        text: The scene descriptions
        style: Global style/vibe to apply to all clips
        max_clips: Maximum number of clips to generate
    """
    if max_clips is None:
        max_clips = MAX_CLIPS

    sentences = split_into_sentences(text)

    # If too few sentences, keep as is
    if len(sentences) <= MIN_CLIPS:
        clips = sentences
    # If too many sentences, combine some to fit within max_clips
    elif len(sentences) > max_clips:
        clips = combine_sentences(sentences, max_clips)
    else:
        clips = sentences

    # Create clip objects with narration and default visual prompts
    result = []
    for i, narration in enumerate(clips):
        result.append({
            "id": i + 1,
            "narration": narration,
            "visual_prompt": generate_visual_prompt(narration, style),
        })

    return result


def combine_sentences(sentences: List[str], target_count: int) -> List[str]:
    """Combine sentences to fit within target count."""
    if len(sentences) <= target_count:
        return sentences

    # Calculate how many sentences per clip
    sentences_per_clip = len(sentences) / target_count

    combined = []
    current_clip = []
    current_count = 0

    for sentence in sentences:
        current_clip.append(sentence)
        current_count += 1

        # Check if we should start a new clip
        if current_count >= sentences_per_clip and len(combined) < target_count - 1:
            combined.append(" ".join(current_clip))
            current_clip = []
            current_count = 0

    # Add remaining sentences to last clip
    if current_clip:
        combined.append(" ".join(current_clip))

    return combined


def generate_visual_prompt(scene_description: str, style: str = "") -> str:
    """
    Generate a visual prompt from scene description.
    Style is passed separately to the agent for context-aware enhancement.

    Args:
        scene_description: What this clip should show
        style: Unused - kept for API compatibility
    """
    return scene_description


def estimate_duration(clips: List[Dict], seconds_per_clip: int = 5) -> int:
    """Estimate total video duration in seconds."""
    return len(clips) * seconds_per_clip
