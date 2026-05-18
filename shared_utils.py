#!/usr/bin/env python3
"""
Shared utilities for video generation pipeline.
Contains reusable components for API interaction, prompt loading, and JSON parsing.
"""

import json
import logging
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

from openai import OpenAI
from dotenv import load_dotenv


def setup_environment() -> None:
    """Initialize environment: Windows encoding and logging."""
    # Fix encoding for Windows console
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    
    # Load environment variables
    load_dotenv()


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)


def load_api_credentials() -> tuple[str, str]:
    """Load API key and model from environment variables."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    model = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-v4-flash")
    
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable not set")
    
    return api_key, model


def load_prompt_template(prompt_name: str, prompts_dir: Path) -> str:
    """Load a prompt template from file."""
    file_path = prompts_dir / f"{prompt_name}.txt"
    if not file_path.exists():
        raise FileNotFoundError(f"Prompt template not found: {file_path}")
    return file_path.read_text(encoding="utf-8")


def extract_json_from_response(response: str) -> Dict[str, Any] | List[Any]:
    """Robustly extract JSON from model response."""
    logger = get_logger(__name__)
    
    # Try to find JSON object or array in the response
    json_pattern = re.compile(r'(\{(?:[^{}]|(?:\{[^{}]*\}))*\}|\[(?:[^\[\]]|(?:\[[^\[\]]*\]))*\])', re.DOTALL)
    matches = json_pattern.findall(response)
    
    if matches:
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
    
    # If no JSON found, try parsing the entire response
    try:
        return json.loads(response)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to extract JSON. Raw response: {response[:500]}")
        raise ValueError(f"Could not extract valid JSON from response: {e}")


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
        self.logger = get_logger(__name__)

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
                self.logger.warning(
                    f"API error: {e}. "
                    f"Retrying in {wait_time}s (attempt {retry + 1}/{self.max_retries})"
                )
                time.sleep(wait_time)
                return self._call_api(messages, retry + 1)
            else:
                self.logger.error(f"API request failed: {e}")
                raise

    def chat(self, system_message: str, user_message: str) -> str:
        """Send a chat completion request."""
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
        return self._call_api(messages)


def get_audio_duration(file_path: str) -> float:
    """Get duration of an audio file in seconds using ffprobe."""
    import shutil
    ffprobe_path = shutil.which("ffprobe")
    
    if not ffprobe_path:
        return 0.0
    
    try:
        result = subprocess.run(
            [
                ffprobe_path,
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1:nokey=1",
                file_path
            ],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.stdout.strip():
            return float(result.stdout.strip())
    except Exception:
        pass
    
    return 0.0


def format_duration(seconds: float) -> str:
    """Format duration in seconds to HH:MM:SS format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"
