#!/usr/bin/env python3
"""
Extract pure narration text from video_package.json and generate YouTube-formatted version using OpenRouter API.
"""

import json
import argparse
import sys
import re
import time
import logging
import os
from pathlib import Path
from typing import Any, Dict, List

from openai import OpenAI
from dotenv import load_dotenv

# Fix encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class OpenRouterClient:
    """Client for OpenRouter Chat Completions API using OpenAI SDK."""

    def __init__(self, api_key: str, model: str, enable_reasoning: bool = False):
        """Initialize client with API key and model."""
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
        self.model = model
        self.enable_reasoning = enable_reasoning
        self.max_retries = 3
        self.base_wait = 1  # seconds

    def _call_api(self, messages: List[Dict[str, Any]], retry: int = 0) -> str:
        """Call OpenRouter API with exponential backoff on 429/5xx."""
        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "timeout": 60.0
            }
            
            if self.enable_reasoning:
                kwargs["extra_body"] = {"reasoning": {"enabled": True}}
            
            response = self.client.chat.completions.create(**kwargs)
            
            return response.choices[0].message.content
        
        except Exception as e:
            if retry < self.max_retries and ("429" in str(e) or "500" in str(e) or "502" in str(e) or "503" in str(e) or "504" in str(e)):
                wait_time = self.base_wait * (2 ** retry)
                logger.warning(
                    f"API error: {e}. "
                    f"Retrying in {wait_time}s (attempt {retry + 1}/{self.max_retries})"
                )
                time.sleep(wait_time)
                return self._call_api(messages, retry + 1)
            else:
                logger.error(f"API request failed: {e}")
                raise

    def chat(self, system_message: str, user_message: str) -> str:
        """Send a chat completion request."""
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
        return self._call_api(messages)


def load_prompt_template(prompt_name: str, prompts_dir: Path) -> str:
    """Load a prompt template from file."""
    file_path = prompts_dir / f"{prompt_name}.txt"
    if not file_path.exists():
        raise FileNotFoundError(f"Prompt template not found: {file_path}")
    return file_path.read_text(encoding="utf-8")


def split_sentences(text: str) -> list:
    """Split text into sentences using regex."""
    # Split on periods, question marks, exclamation marks followed by space
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]


def extract_narration(video_package_path: str, output_path: str, youtube_output_path: str = None, enable_ai: bool = True) -> None:
    """Extract narration and generate YouTube format with AI enhancement."""
    
    # Load video package
    with open(video_package_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    video_package = data.get("video_package", {})
    scenes = video_package.get("scenes", [])
    topic = video_package.get("topic", "topic")
    
    # Extract pure narration text (space-separated, no newlines)
    narration_lines = []
    for scene in scenes:
        narration = scene.get("narration", "").strip()
        if narration:
            narration_lines.append(narration)
    
    # Join with spaces to create continuous narration
    full_narration = " ".join(narration_lines)
    
    # Write pure narration to file (space-separated, single content)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(full_narration)
    
    print(f"✓ Raw narration extracted to: {output_path}")
    
    # Generate YouTube format version using AI
    if youtube_output_path is None:
        youtube_output_path = output_path.replace(".txt", "_youtube.txt")
    
    if enable_ai:
        youtube_format = generate_youtube_format_ai(topic, full_narration)
    else:
        # Fallback: split into sentences and return
        sentences = split_sentences(full_narration)
        youtube_format = "\n".join(sentences)
    
    with open(youtube_output_path, 'w', encoding='utf-8') as f:
        f.write(youtube_format)
    
    print(f"✓ YouTube format generated to: {youtube_output_path}")


def generate_youtube_format_ai(topic: str, narration: str) -> str:
    """Generate YouTube format using OpenRouter API."""
    
    # Load API key and model
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENROUTER_API_KEY environment variable not set. "
            "Please set it before running this script."
        )
    
    model = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-v4-flash")
    
    # Initialize client
    client = OpenRouterClient(api_key, model)
    
    # Load prompts
    prompts_dir = Path(__file__).parent / "Prompts"
    system_prompt = load_prompt_template("system", prompts_dir)
    youtube_prompt = load_prompt_template("youtube_format", prompts_dir)
    
    # Fill in the template with topic and narration
    user_message = youtube_prompt.format(topic=topic, narration=narration)
    
    # Call API
    print("⏳ Generating entertainment-focused YouTube format with AI...")
    youtube_format = client.chat(system_prompt, user_message)
    
    # Split into sentences with newlines for TTS
    sentences = split_sentences(youtube_format)
    return "\n".join(sentences)


def main():
    parser = argparse.ArgumentParser(
        description="Extract narration and generate YouTube format"
    )
    parser.add_argument(
        "--video-package",
        default="./output/video_package.json",
        help="Path to video_package.json (default: ./output/video_package.json)"
    )
    parser.add_argument(
        "--output",
        default="./output/narration_draft.txt",
        help="Output txt file path (default: ./output/narration_draft.txt)"
    )
    parser.add_argument(
        "--youtube-output",
        default=None,
        help="YouTube format output path (default: same as --output with _youtube suffix)"
    )
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="Use static format instead of AI-generated YouTube format"
    )
    
    args = parser.parse_args()
    
    try:
        enable_ai = not args.no_ai
        extract_narration(args.video_package, args.output, args.youtube_output, enable_ai=enable_ai)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in video package: {e}")
        exit(1)
    except ValueError as e:
        print(f"Error: {e}")
        exit(1)
    except Exception as e:
        print(f"Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
