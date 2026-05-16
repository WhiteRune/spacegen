#!/usr/bin/env python3
"""
Video generation pipeline orchestrator using OpenRouter Chat Completions API.

This script reads prompt templates from the Prompts/ folder and orchestrates
a video generation pipeline: retrieval_queries → outline → for each scene:
script_with_citations → fact_checker → ssml_generator.
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

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


def extract_json_from_response(response: str) -> Dict[str, Any] | List[Any]:
    """Robustly extract JSON from model response."""
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


def generate_retrieval_queries(
    client: OpenRouterClient,
    system_msg: str,
    prompt_template: str,
    topic: str
) -> List[str]:
    """Generate global retrieval queries for the topic."""
    logger.info("Generating retrieval queries...")
    
    user_message = f"""{prompt_template}

Topic: {topic}
Scene Keywords: {topic}

Please generate 5 ranked retrieval queries as a JSON array."""
    
    response = client.chat(system_msg, user_message)
    queries = extract_json_from_response(response)
    
    if not isinstance(queries, list):
        raise ValueError(f"Expected list of queries, got {type(queries)}")
    
    logger.info(f"Generated {len(queries)} retrieval queries")
    return queries


def generate_outline(
    client: OpenRouterClient,
    system_msg: str,
    prompt_template: str,
    topic: str,
    length_seconds: int,
    scenes_count: int
) -> List[Dict[str, Any]]:
    """Generate outline with scenes."""
    logger.info(f"Generating outline for {scenes_count} scenes...")
    
    user_message = f"""{prompt_template}

Video Topic: {topic}
Target Duration: {length_seconds} seconds
Number of Scenes: {scenes_count}

Please generate exactly {scenes_count} scenes as a JSON array."""
    
    response = client.chat(system_msg, user_message)
    scenes = extract_json_from_response(response)
    
    if not isinstance(scenes, list):
        raise ValueError(f"Expected list of scenes, got {type(scenes)}")
    
    logger.info(f"Generated outline with {len(scenes)} scenes")
    return scenes


def generate_script_with_citations(
    client: OpenRouterClient,
    system_msg: str,
    prompt_template: str,
    scene: Dict[str, Any],
    retrieved_docs: List[Dict[str, str]]
) -> Dict[str, Any]:
    """Generate script with citations for a scene."""
    logger.info(f"Generating script for scene {scene['id']}: {scene['title']}")
    
    estimated_seconds = scene.get("estimated_seconds", 10)
    
    # Format scene info as readable text
    scene_info = f"""Scene Details:
- ID: {scene.get('id', 'N/A')}
- Title: {scene.get('title', 'N/A')}
- Purpose: {scene.get('purpose', 'N/A')}
- Estimated Duration: {estimated_seconds} seconds"""
    
    # Format retrieved docs as readable list
    if retrieved_docs:
        docs_info = "\n\nRetrieved Documents:\n"
        for i, doc in enumerate(retrieved_docs, 1):
            docs_info += f"{i}. Title: {doc.get('title', 'N/A')}\n"
            docs_info += f"   URL: {doc.get('url', 'N/A')}\n"
            docs_info += f"   Excerpt: {doc.get('excerpt', 'N/A')}\n"
    else:
        docs_info = "\n\nRetrieved Documents: None provided"
    
    # Build user message with template + scene/docs info
    user_message = f"""{prompt_template}

{scene_info}
{docs_info}

Please generate the narration JSON now."""
    
    response = client.chat(system_msg, user_message)
    script_data = extract_json_from_response(response)
    
    if not isinstance(script_data, dict):
        raise ValueError(f"Expected dict for script, got {type(script_data)}")
    
    return script_data


def fact_check_claims(
    client: OpenRouterClient,
    system_msg: str,
    prompt_template: str,
    claims: List[Dict[str, Any]],
    candidate_docs: List[Dict[str, str]]
) -> List[Dict[str, Any]]:
    """Fact-check claims against candidate documents."""
    logger.info(f"Fact-checking {len(claims)} claims...")
    
    if not candidate_docs:
        # No docs provided; mark all claims as needing source
        for claim in claims:
            claim["supported"] = "false"
            claim["best_source_url"] = None
            claim["confidence"] = 0
            claim["note"] = "needs_source"
        return claims
    
    # Format claims as readable list
    claims_info = "Claims to verify:\n"
    for claim in claims:
        claim_id = claim.get("claim_id", "N/A")
        text = claim.get("text", "N/A")
        claims_info += f"- {claim_id}: {text}\n"
    
    # Format docs as readable list
    docs_info = "\nCandidate Documents:\n"
    for i, doc in enumerate(candidate_docs, 1):
        docs_info += f"{i}. Title: {doc.get('title', 'N/A')}\n"
        docs_info += f"   URL: {doc.get('url', 'N/A')}\n"
        docs_info += f"   Excerpt: {doc.get('excerpt', 'N/A')}\n"
    
    # Build user message
    user_message = f"""{prompt_template}

{claims_info}
{docs_info}

Please verify each claim against the candidate documents and return the results as JSON."""
    
    response = client.chat(system_msg, user_message)
    checked_claims = extract_json_from_response(response)
    
    if not isinstance(checked_claims, list):
        raise ValueError(f"Expected list of checked claims, got {type(checked_claims)}")
    
    return checked_claims


def generate_ssml(
    client: OpenRouterClient,
    system_msg: str,
    prompt_template: str,
    scene_id: int,
    narration: str,
    estimated_seconds: int
) -> Dict[str, Any]:
    """Generate SSML for scene narration."""
    logger.info(f"Generating SSML for scene {scene_id}...")
    
    user_message = f"""{prompt_template}

Scene ID: {scene_id}
Narration: {narration}
Estimated Duration: {estimated_seconds} seconds

Please generate the SSML output as JSON with 'ssml' and 'timings_hint' keys."""
    
    response = client.chat(system_msg, user_message)
    ssml_data = extract_json_from_response(response)
    
    if not isinstance(ssml_data, dict):
        raise ValueError(f"Expected dict for SSML, got {type(ssml_data)}")
    
    return ssml_data


def load_retrieved_docs(
    retrieved_docs_path: Optional[str],
    scene_id: int,
    scene_keywords: List[str],
    retrieval_limit: int
) -> List[Dict[str, str]]:
    """Load retrieved documents for a scene from JSON file."""
    if not retrieved_docs_path:
        return []
    
    try:
        with open(retrieved_docs_path, "r", encoding="utf-8") as f:
            docs_map = json.load(f)
        
        # Try to find docs by scene ID or keywords
        scene_docs = docs_map.get(str(scene_id), [])
        if not scene_docs and scene_keywords:
            for keyword in scene_keywords:
                if keyword in docs_map:
                    scene_docs = docs_map[keyword]
                    break
        
        return scene_docs[:retrieval_limit]
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Failed to load retrieved docs: {e}")
        return []


def orchestrate_pipeline(
    topic: str,
    length_seconds: int,
    scenes_count: int,
    retrieval_limit: int,
    retrieved_docs_path: Optional[str],
    output_dir: Path,
    api_key: str,
    model: str,
    prompts_dir: Path,
    enable_reasoning: bool = False
) -> None:
    """Orchestrate the full video generation pipeline."""
    logger.info("Starting video generation pipeline...")
    
    # Initialize client and load system message
    client = OpenRouterClient(api_key, model, enable_reasoning=enable_reasoning)
    system_msg = load_prompt_template("system", prompts_dir)
    
    # Step 1: Generate retrieval queries
    retrieval_queries_template = load_prompt_template("retrieval_queries", prompts_dir)
    global_queries = generate_retrieval_queries(client, system_msg, retrieval_queries_template, topic)
    
    # Step 2: Generate outline
    outline_template = load_prompt_template("outline", prompts_dir)
    scenes = generate_outline(client, system_msg, outline_template, topic, length_seconds, scenes_count)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    outline_file = output_dir / "outline.json"
    outline_file.write_text(json.dumps(scenes, indent=2), encoding="utf-8")
    logger.info(f"Wrote outline to {outline_file}")
    
    # Load templates for script, fact-check, and SSML
    script_template = load_prompt_template("script_with_citations", prompts_dir)
    fact_check_template = load_prompt_template("fact_checker", prompts_dir)
    ssml_template = load_prompt_template("ssml_generator", prompts_dir)
    
    # Step 3: Process each scene
    video_scenes = []
    orchestration_log = {
        "topic": topic,
        "length_seconds": length_seconds,
        "scenes_count": scenes_count,
        "global_queries": global_queries,
        "scenes": []
    }
    
    for scene in scenes:
        scene_id = scene.get("id", len(video_scenes))
        scene_keywords = scene.get("keywords", [topic])
        
        logger.info(f"Processing scene {scene_id}/{scenes_count}...")
        
        # Load retrieved docs for this scene
        scene_docs = load_retrieved_docs(
            retrieved_docs_path,
            scene_id,
            scene_keywords,
            retrieval_limit
        )
        logger.info(f"Loaded {len(scene_docs)} documents for scene {scene_id}")
        
        # Generate script with citations
        script_data = generate_script_with_citations(
            client, system_msg, script_template, scene, scene_docs
        )
        
        # Extract claims for fact-checking
        claims = script_data.get("claims", [])
        
        # Fact-check claims
        checked_claims = fact_check_claims(
            client, system_msg, fact_check_template, claims, scene_docs
        )
        
        # Update script with fact-checked claims
        script_data["claims"] = checked_claims
        
        # Generate SSML
        narration = script_data.get("narration", "")
        estimated_seconds = scene.get("estimated_seconds", 10)
        ssml_data = generate_ssml(
            client, system_msg, ssml_template, scene_id, narration, estimated_seconds
        )
        
        # Merge SSML into script data
        script_data["ssml"] = ssml_data.get("ssml", "")
        script_data["timings_hint"] = ssml_data.get("timings_hint", [])
        
        # Build final scene object
        final_scene = {
            "id": scene_id,
            "title": scene.get("title", ""),
            "purpose": scene.get("purpose", ""),
            "estimated_seconds": estimated_seconds,
            "keywords": scene_keywords,
            "narration": narration,
            "ssml": script_data.get("ssml", ""),
            "timings_hint": script_data.get("timings_hint", []),
            "citations": script_data.get("citations", []),
            "claims": checked_claims
        }
        
        video_scenes.append(final_scene)
        
        # Log stats for this scene
        total_claims = len(checked_claims)
        supported_count = sum(1 for c in checked_claims if c.get("supported") == "true")
        needing_source = sum(1 for c in checked_claims if c.get("note") == "needs_source")
        
        orchestration_log["scenes"].append({
            "scene_id": scene_id,
            "retrieved_doc_count": len(scene_docs),
            "total_claims": total_claims,
            "claims_supported_count": supported_count,
            "claims_needing_source_count": needing_source
        })
        
        # Write intermediate scene file
        scene_file = output_dir / f"scene_{scene_id}_script.json"
        scene_file.write_text(json.dumps(final_scene, indent=2), encoding="utf-8")
        logger.info(f"Wrote scene {scene_id} to {scene_file}")
    
    # Build final video package
    video_package = {
        "topic": topic,
        "length_seconds": length_seconds,
        "scenes_count": scenes_count,
        "scenes": video_scenes
    }
    
    # Write final outputs
    final_output = {
        "video_package": video_package,
        "orchestration_log": orchestration_log
    }
    
    package_file = output_dir / "video_package.json"
    package_file.write_text(json.dumps(final_output, indent=2), encoding="utf-8")
    logger.info(f"Wrote final video package to {package_file}")
    
    log_file = output_dir / "orchestration_log.json"
    log_file.write_text(json.dumps(orchestration_log, indent=2), encoding="utf-8")
    logger.info(f"Wrote orchestration log to {log_file}")
    
    logger.info("Pipeline completed successfully!")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Orchestrate video generation pipeline using OpenRouter API"
    )
    parser.add_argument("--topic", required=True, help="Video topic")
    parser.add_argument("--length-seconds", type=int, required=True, help="Target length in seconds")
    parser.add_argument("--scenes-count", type=int, required=True, help="Number of scenes to generate")
    parser.add_argument("--retrieval-limit", type=int, default=5, help="Max docs per scene (default 5)")
    parser.add_argument("--retrieved-docs", help="Path to JSON file with retrieved documents")
    parser.add_argument("--output-dir", default="./output", help="Output directory (default: ./output)")
    parser.add_argument("--enable-reasoning", action="store_true", help="Enable DeepSeek reasoning mode")
    
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    api_key = os.getenv("OPENROUTER_API_KEY")
    model = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-v4-flash")
    
    if not api_key:
        logger.error("OPENROUTER_API_KEY environment variable not set")
        sys.exit(1)
    
    # Determine prompts directory (relative to script)
    script_dir = Path(__file__).parent.absolute()
    prompts_dir = script_dir / "Prompts"
    
    if not prompts_dir.exists():
        logger.error(f"Prompts directory not found at {prompts_dir}")
        sys.exit(1)
    
    # Run pipeline
    try:
        orchestrate_pipeline(
            topic=args.topic,
            length_seconds=args.length_seconds,
            scenes_count=args.scenes_count,
            retrieval_limit=args.retrieval_limit,
            retrieved_docs_path=args.retrieved_docs,
            output_dir=Path(args.output_dir),
            api_key=api_key,
            model=model,
            prompts_dir=prompts_dir,
            enable_reasoning=args.enable_reasoning
        )
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
