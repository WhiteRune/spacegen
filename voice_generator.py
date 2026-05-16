#!/usr/bin/env python3
"""
Voice generation from narration text using OpenRouter Gemini TTS API.

Reads narration sentences from narration_draft_youtube.txt and generates
audio files (MP3) with professional voice narration. Supports ffmpeg conversion
from PCM to MP3 for better compatibility.
"""

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

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


class VoiceGenerator:
    """Generate voice narration from text using OpenRouter Gemini TTS."""

    def __init__(
        self,
        api_key: str,
        model: str = "google/gemini-3.1-flash-tts-preview",
        voice: str = "Charon",
        speed: float = 1.0,
        output_dir: str = "./output/voice_over"
    ):
        """Initialize voice generator with API credentials and settings."""
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
        self.model = model
        self.voice = voice
        self.speed = speed
        self.output_dir = output_dir
        
        # Create output directory
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Voice Generator initialized")
        logger.info(f"  Model: {self.model}")
        logger.info(f"  Voice: {self.voice}")
        logger.info(f"  Speed: {self.speed}")
        logger.info(f"  Output: {self.output_dir}")

    def generate_speech(self, text: str, sentence_idx: int, narrator_prompt: Optional[str] = None) -> bool:
        """Generate speech for a single sentence and save as MP3."""
        
        output_path = Path(self.output_dir) / f"{sentence_idx:03d}.pcm"
        
        # Skip if file already exists
        if output_path.exists():
            logger.info(f"⏭  Sentence {sentence_idx:03d} already exists, skipping")
            return True
        
        try:
            logger.info(f"🎙️  Generating speech {sentence_idx}/{len(text) if isinstance(text, list) else '?'}: {text[:50]}...")
            
            # Prepare API request kwargs
            kwargs = {
                "model": self.model,
                "input": text,
                "voice": self.voice,
                "speed": self.speed,
            }
            
            # Add narrator prompt if provided
            if narrator_prompt:
                kwargs["instructions"] = narrator_prompt
            
            # Generate speech with streaming response
            with self.client.audio.speech.with_streaming_response.create(**kwargs) as response:
                response.stream_to_file(str(output_path))
            
            logger.info(f"✅ Sentence {sentence_idx:03d}.pcm created")
            time.sleep(1.0)  # Rate limiting
            return True
            
        except Exception as e:
            error_str = str(e)
            if "500" in error_str or "Internal" in error_str:
                logger.warning(f"⚠️  Server error. Waiting 15 seconds before retry...")
                time.sleep(15)
            else:
                logger.error(f"❌ Error generating speech for sentence {sentence_idx}: {e}")
                time.sleep(2)
            return False

    def get_audio_duration(self, file_path: str) -> float:
        """Get duration of an audio file in seconds using ffprobe."""
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
        except Exception as e:
            logger.warning(f"Could not get duration for {file_path}: {e}")
        
        return 0.0
    
    def format_duration(self, seconds: float) -> str:
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
    
    def get_total_duration(self) -> float:
        """Calculate total duration of all MP3 files in output directory."""
        total_duration = 0.0
        mp3_files = [f for f in os.listdir(self.output_dir) if f.lower().endswith('.mp3')]
        
        for mp3_file in mp3_files:
            file_path = Path(self.output_dir) / mp3_file
            duration = self.get_audio_duration(str(file_path))
            total_duration += duration
        
        return total_duration

    def convert_pcm_to_mp3(self, force: bool = False) -> int:
        """Convert all PCM files to MP3 using ffmpeg."""
        
        ffmpeg_path = shutil.which("ffmpeg")
        
        if not ffmpeg_path:
            logger.warning("⚠️  ffmpeg not found in PATH")
            logger.warning("📥 Install ffmpeg and add it to PATH to convert PCM to MP3")
            return 0
        
        # Find all PCM files
        pcm_files = sorted([f for f in os.listdir(self.output_dir) if f.lower().endswith('.pcm')])
        
        if not pcm_files:
            logger.info("ℹ️  No PCM files to convert")
            return 0
        
        logger.info(f"📦 Found {len(pcm_files)} PCM files for conversion\n")
        
        converted_count = 0
        for pcm_file in pcm_files:
            input_path = Path(self.output_dir) / pcm_file
            base_name = pcm_file.rsplit('.', 1)[0]
            output_path = Path(self.output_dir) / f"{base_name}.mp3"
            
            if output_path.exists() and not force:
                logger.info(f"⏭  {output_path.name} already exists, skipping")
                try:
                    os.remove(input_path)
                    logger.info(f"  🗑️  Deleted original PCM file: {pcm_file}")
                except OSError:
                    pass
                continue
            
            try:
                logger.info(f"🔄 Converting {pcm_file} → MP3...")
                subprocess.run(
                    [
                        ffmpeg_path,
                        '-y',
                        '-f', 's16le',
                        '-ar', '24000',
                        '-ac', '1',
                        '-i', str(input_path),
                        '-b:a', '128k',
                        str(output_path),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                logger.info(f"✅ Successfully converted: {output_path.name}")
                converted_count += 1
                
                try:
                    os.remove(input_path)
                    logger.info(f"  🗑️  Deleted original PCM file: {pcm_file}")
                except OSError:
                    pass
                    
            except subprocess.CalledProcessError as e:
                logger.error(f"❌ Error converting {pcm_file}: {e.stderr.strip() if e.stderr else e}")
        
        logger.info(f"\n✨ Conversion complete! Converted {converted_count}/{len(pcm_files)} files")
        return converted_count


def load_prompt_template(prompt_name: str, prompts_dir: Path) -> Optional[str]:
    """Load a prompt template from file."""
    file_path = prompts_dir / f"{prompt_name}.txt"
    if not file_path.exists():
        logger.warning(f"Prompt template not found: {file_path}")
        return None
    return file_path.read_text(encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(
        description="Generate voice narration from text using OpenRouter Gemini TTS"
    )
    parser.add_argument(
        "--narration",
        default="./output/narration_draft_youtube.txt",
        help="Path to narration text file (default: ./output/narration_draft_youtube.txt)"
    )
    parser.add_argument(
        "--output-dir",
        default="./output/voice_over",
        help="Output directory for audio files (default: ./output/voice_over)"
    )
    parser.add_argument(
        "--model",
        default="google/gemini-3.1-flash-tts-preview",
        help="TTS model to use (default: google/gemini-3.1-flash-tts-preview)"
    )
    parser.add_argument(
        "--voice",
        default="Charon",
        help="Voice name (default: Charon)"
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Speech speed (default: 1.0)"
    )
    parser.add_argument(
        "--narrator-prompt",
        default=None,
        help="Path to narrator prompt file (optional)"
    )
    parser.add_argument(
        "--no-convert",
        action="store_true",
        help="Skip PCM to MP3 conversion"
    )
    parser.add_argument(
        "--force-convert",
        action="store_true",
        help="Force re-conversion of existing MP3 files"
    )
    
    args = parser.parse_args()
    
    # Validate API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("❌ OPENROUTER_API_KEY environment variable not set")
        exit(1)
    
    # Validate narration file
    if not os.path.exists(args.narration):
        logger.error(f"❌ Narration file not found: {args.narration}")
        exit(1)
    
    # Load narration
    with open(args.narration, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]
    
    logger.info(f"📦 Loaded {len(lines)} narration sentences")
    
    # Load narrator prompt if provided
    narrator_prompt = None
    if args.narrator_prompt and os.path.exists(args.narrator_prompt):
        with open(args.narrator_prompt, 'r', encoding='utf-8') as f:
            narrator_prompt = f.read()
        logger.info(f"📄 Loaded narrator prompt")
    
    # Initialize voice generator
    generator = VoiceGenerator(
        api_key=api_key,
        model=args.model,
        voice=args.voice,
        speed=args.speed,
        output_dir=args.output_dir
    )
    
    # Generate speech for each sentence
    logger.info(f"\n🎙️  Starting voice generation for {len(lines)} sentences...\n")
    
    generated_count = 0
    for i, line in enumerate(lines, start=1):
        if generator.generate_speech(line, i, narrator_prompt):
            generated_count += 1
    
    logger.info(f"\n✨ Voice generation complete! Generated {generated_count}/{len(lines)} audio files")
    
    # Convert PCM to MP3 if requested
    if not args.no_convert:
        logger.info(f"\n🔄 Starting PCM to MP3 conversion...\n")
        generator.convert_pcm_to_mp3(force=args.force_convert)
    
    # Calculate and display total audio duration
    logger.info(f"\n📊 Calculating total audio duration...")
    total_duration = generator.get_total_duration()
    formatted_duration = generator.format_duration(total_duration)
    
    # Count MP3 files
    mp3_files = [f for f in os.listdir(args.output_dir) if f.lower().endswith('.mp3')]
    
    logger.info(f"\n{'=' * 70}")
    logger.info(f"✨ VOICE GENERATION SUMMARY")
    logger.info(f"{'=' * 70}")
    logger.info(f"📁 Output directory: {args.output_dir}")
    logger.info(f"🎵 Total audio files: {len(mp3_files)} MP3 files")
    logger.info(f"⏱️  Total audio duration: {formatted_duration}")
    logger.info(f"{'=' * 70}")


if __name__ == "__main__":
    main()
