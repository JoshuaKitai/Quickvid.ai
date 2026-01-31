from openai import OpenAI
from typing import List, Dict
from config import OPENAI_API_KEY


class StoryProcessor:
    """Uses GPT to create consistent prompts across all clips."""

    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)

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
            import json
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
