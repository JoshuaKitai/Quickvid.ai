import json
from openai import OpenAI
from typing import List, Dict
from config import OPENAI_API_KEY


class StoryProcessor:
    """Uses GPT to create consistent prompts across all clips."""

    def __init__(self, api_key: str = None):
        self.client = OpenAI(api_key=api_key or OPENAI_API_KEY)

    def generate_prompts_from_description(self, description: str, clip_count: int, duration: int) -> List[str]:
        """
        Generate Sora-optimized prompts from a paragraph description.

        Args:
            description: User's paragraph describing the video
            clip_count: Number of clips to generate
            duration: Duration per clip in seconds

        Returns:
            List of prompt strings, one per clip
        """
        system_prompt = """You are an expert AI video director. Given a description of a video, break it into sequential scenes and write detailed Sora-optimized prompts for each one.

For each scene prompt you MUST include:
1. Camera work (dolly, tracking shot, aerial, handheld, static, crane, etc.)
2. Lighting (golden hour, neon-lit, overcast, studio, natural, etc.)
3. Detailed action description with pacing appropriate for the clip duration
4. Visual style and mood (cinematic, documentary, dreamy, gritty, etc.)
5. Texture, material, and color details

CRITICAL RULES:
- Maintain visual consistency across ALL clips: use the EXACT same character descriptions, settings, color palette, and style in every prompt
- Each prompt should be self-contained (Sora generates clips independently)
- Consider the clip duration when pacing the action — shorter clips need simpler, focused action; longer clips can have more complex sequences
- Do NOT include any text overlays, subtitles, or narration instructions
- Write in a descriptive, present-tense style

Output format: Return ONLY a JSON array of strings, one prompt per clip. No other text."""

        user_prompt = f"""Video description: {description}

Number of clips: {clip_count}
Duration per clip: {duration} seconds

Break this into {clip_count} sequential scenes and write a detailed Sora-optimized prompt for each. Return as a JSON array of {clip_count} strings."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
            )

            content = response.choices[0].message.content.strip()

            # Handle markdown code blocks if present
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            prompts = json.loads(content)

            # Ensure we got the right count
            if len(prompts) < clip_count:
                prompts.extend(prompts[-1:] * (clip_count - len(prompts)))
            elif len(prompts) > clip_count:
                prompts = prompts[:clip_count]

            return prompts

        except Exception as e:
            raise Exception(f"Failed to generate prompts: {e}")

    def enhance_prompts(self, clips: List[Dict], global_style: str = "") -> List[Dict]:
        """
        Enhance clip prompts with consistent character/setting descriptions.

        Args:
            clips: List of clip dicts with 'visual_prompt'
            global_style: Global style to apply

        Returns:
            Updated clips with enhanced prompts
        """
        # Gather all scene descriptions
        scenes = [clip.get("visual_prompt", "") for clip in clips]
        scenes_text = "\n".join([f"Clip {i+1}: {s}" for i, s in enumerate(scenes)])

        # Ask GPT to create consistent prompts
        system_prompt = """You are a video production assistant. Your job is to rewrite scene descriptions to maintain visual consistency across all clips in a short video.

When given a series of scene descriptions, you must:
1. Identify recurring characters/subjects and create a FIXED detailed description for each (appearance, clothing, features)
2. Identify the setting and create a FIXED detailed description (location, lighting, time of day, weather)
3. Rewrite each scene description to include these consistent details

CRITICAL: Every clip must describe characters and settings EXACTLY the same way so AI video generation produces consistent visuals.

Output format - return ONLY a JSON array of strings, one enhanced prompt per clip:
["enhanced prompt 1", "enhanced prompt 2", ...]"""

        user_prompt = f"""Global style: {global_style if global_style else "Cinematic, high quality"}

Scene descriptions:
{scenes_text}

Rewrite each scene with consistent character and setting descriptions. Return as JSON array."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
            )

            # Parse the response
            content = response.choices[0].message.content.strip()

            # Extract JSON array from response
            # Handle markdown code blocks if present
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            enhanced_prompts = json.loads(content)

            # Update clips with enhanced prompts
            for i, clip in enumerate(clips):
                if i < len(enhanced_prompts):
                    clip["visual_prompt"] = enhanced_prompts[i]

            return clips

        except Exception as e:
            print(f"Story processing error: {e}")
            # Return original clips if enhancement fails
            return clips
