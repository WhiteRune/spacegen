#!/usr/bin/env python3
"""
Voice generation from narration text using OpenRouter Gemini TTS API.

Reads narration sentences from narration_draft_youtube.txt line by line and generates
audio files (MP3) with professional voice narration. 

NARRATOR PROMPTS:
When a narrator prompt is provided via --narrator-prompt, it is applied as the
base instruction/performance direction for EVERY sentence generated. The narrator
prompt acts as the foundational performance guidance that ensures consistent voice
character, tone, pacing, and style across all audio files.

Available narrator prompts (following Gemini TTS official guide):
- Educational: General educational content with balanced pacing and engagement
- Technical: Technical deep-dives with precise, authoritative delivery
- Motivational: Personal development with warm, inspiring tone

Narrator prompts include:
- Audio Profile: Character identity and archetype
- Scene: Environmental context for consistent mood
- Director's Notes: Specific performance guidance (style, pacing, accent)
- Transcript Guidelines: Recommended audio tags ([excitedly], [serious], etc.)

Supports ffmpeg conversion from PCM to MP3 for better compatibility.
"""

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from openai import OpenAI

from shared_utils import setup_environment, get_logger, load_api_credentials, get_audio_duration, format_duration

# Initialize environment
setup_environment()
logger = get_logger(__name__)


class VoiceGenerator:
    """Generate voice narration from text using OpenRouter Gemini TTS.
    
    This class processes narration text line by line, generating audio for each sentence.
    When a narrator_prompt is provided, it serves as the base performance instruction
    applied to every sentence, ensuring consistent voice character and delivery style
    across all generated audio files.
    
    The narrator_prompt is passed as the 'instructions' parameter to the Gemini TTS
    API, allowing advanced performance direction without modifying the actual narration text.
    """

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
        """Generate speech for a single sentence and save as PCM.
        
        Args:
            text: The narration text to speak (single sentence)
            sentence_idx: Index number for output file naming (001, 002, etc.)
            narrator_prompt: Optional base performance instruction from narrator prompt.
                           Applied as 'instructions' to Gemini TTS API to control
                           voice character, tone, pacing, style across all sentences.
        
        Returns:
            True if generation successful, False otherwise.
            
        The narrator_prompt parameter:
        - Is applied as the base instruction for voice delivery
        - Comes from narrator_prompt_educational.txt, narrator_prompt_technical.txt, etc.
        - Ensures consistent voice character and performance across all generated sentences
        - Is passed to the API's 'instructions' parameter
        """
        
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
        return get_audio_duration(file_path)
    
    def format_duration(self, seconds: float) -> str:
        """Format duration in seconds to HH:MM:SS format."""
        return format_duration(seconds)
    
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
    
    # Load API credentials
    try:
        api_key, model = load_api_credentials()
        if args.model != "google/gemini-3.1-flash-tts-preview":
            model = args.model
    except ValueError as e:
        logger.error(f"❌ {e}")
        exit(1)
    
    # Validate narration file
    narration_path = Path(args.narration)
    if not narration_path.exists():
        logger.error(f"❌ Narration file not found: {args.narration}")
        exit(1)
    
    # Load narration
    with open(narration_path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]
    
    logger.info(f"📦 Loaded {len(lines)} narration sentences")
    
    # Load narrator prompt if provided
    narrator_prompt = None
    if args.narrator_prompt:
        narrator_path = Path(args.narrator_prompt)
        if narrator_path.exists():
            with open(narrator_path, 'r', encoding='utf-8') as f:
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
