# Video Generation Pipeline Orchestrator

A Python-based automation tool that orchestrates a video generation pipeline using the OpenRouter Chat Completions API and local prompt templates.

## Overview

This tool implements a multi-step pipeline for generating educational video content:

1. **Retrieval Queries**: Generate 5 ranked search queries for the topic
2. **Outline**: Create a scene-by-scene outline for the video
3. **For each scene**:
   - **Script with Citations**: Generate narration with inline source citations
   - **Fact-Checker**: Verify claims against provided documents
   - **SSML Generator**: Convert narration to SSML with timing hints

## Requirements

- Python 3.10+
- OpenRouter API key
- Prompt templates in `Prompts/` directory:
  - `system.txt`
  - `retrieval_queries.txt`
  - `outline.txt`
  - `script_with_citations.txt`
  - `fact_checker.txt`
  - `ssml_generator.txt`

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Set environment variables:

```bash
export OPENROUTER_API_KEY="your-api-key"
export OPENROUTER_MODEL="meta-llama/llama-3-8b-instruct"  # optional
```

Or create a `.env` file in the working directory:

```
OPENROUTER_API_KEY=your-api-key
OPENROUTER_MODEL=meta-llama/llama-3-8b-instruct
```

## Usage

### Basic Example

```bash
python generate_video_package.py \
  --topic "neutron stars" \
  --length-seconds 60 \
  --scenes-count 4
```

### With Retrieved Documents

Provide a JSON file mapping scene IDs or keywords to retrieved documents:

```bash
python generate_video_package.py \
  --topic "neutron stars" \
  --length-seconds 60 \
  --scenes-count 4 \
  --retrieval-limit 5 \
  --retrieved-docs docs.json \
  --output-dir ./output
```

### Expected Retrieved Documents JSON Schema

```json
{
  "1": [
    {
      "url": "https://example.com/article1",
      "title": "About Neutron Stars",
      "excerpt": "Neutron stars are collapsed cores of massive stars..."
    },
    {
      "url": "https://example.com/article2",
      "title": "Formation of Neutron Stars",
      "excerpt": "Neutron stars form when massive stars undergo supernova..."
    }
  ],
  "2": [
    {
      "url": "https://example.com/article3",
      "title": "Properties of Neutron Stars",
      "excerpt": "Neutron stars are extremely dense..."
    }
  ],
  "keywords_scene_3": [
    {
      "url": "https://example.com/article4",
      "title": "Pulsars",
      "excerpt": "Some neutron stars emit radio pulses..."
    }
  ]
}
```

Documents can be keyed by:
- Scene ID (string): `"1"`, `"2"`, etc.
- Scene keywords: `"neutron stars"`, `"pulsars"`, etc.

If a scene has no matching documents, claims are marked as `needs_source` with confidence 0.

## Output Files

Generated in the output directory (default: `./output`):

- **`video_package.json`**: Final video package with all scenes, narration, SSML, and fact-checked claims
- **`orchestration_log.json`**: Detailed statistics per scene (doc count, claim counts, support status)
- **`outline.json`**: Scene outline generated in step 2
- **`scene_<id>_script.json`**: Intermediate files for each scene (for debugging)

### video_package.json Schema

```json
{
  "video_package": {
    "topic": "string",
    "length_seconds": "int",
    "scenes_count": "int",
    "scenes": [
      {
        "id": "int",
        "title": "string",
        "purpose": "string",
        "estimated_seconds": "int",
        "keywords": ["string"],
        "narration": "string",
        "ssml": "string",
        "timings_hint": ["float"],
        "citations": [
          {
            "id": "int",
            "url": "string",
            "title": "string",
            "excerpt": "string",
            "confidence": "float"
          }
        ],
        "claims": [
          {
            "claim_id": "string",
            "text": "string",
            "supported": "true|false|uncertain",
            "best_source_url": "string|null",
            "confidence": "float (0-1)",
            "note": "string"
          }
        ]
      }
    ]
  },
  "orchestration_log": {
    "topic": "string",
    "length_seconds": "int",
    "scenes_count": "int",
    "global_queries": ["string"],
    "scenes": [
      {
        "scene_id": "int",
        "retrieved_doc_count": "int",
        "total_claims": "int",
        "claims_supported_count": "int",
        "claims_needing_source_count": "int"
      }
    ]
  }
}
```

## Troubleshooting

### API Rate Limiting (429)

The script implements exponential backoff with up to 3 retries. If you still hit rate limits:
- Reduce `--scenes-count`
- Wait between runs
- Check your OpenRouter API quota

### Missing Prompt Templates

Ensure all `.txt` files exist in the `Prompts/` directory:
```bash
ls Prompts/
system.txt
retrieval_queries.txt
outline.txt
script_with_citations.txt
fact_checker.txt
ssml_generator.txt
```

### JSON Parsing Errors

If the model response is not valid JSON:
- Check that `OPENROUTER_API_KEY` is correct
- Verify the model exists and is accessible
- Try a different model (see [OpenRouter docs](https://openrouter.ai/docs))
- Check logs for raw model output

### No Retrieved Documents Provided

If `--retrieved-docs` is omitted or a scene has no matching documents:
- All claims will be marked with `confidence: 0`
- `best_source_url` will be `null`
- `note` will contain `"needs_source"`
- This is expected behavior; the pipeline still completes successfully

## Example Commands

Generate a 2-minute video about black holes with 5 scenes and 3 documents per scene:

```bash
python generate_video_package.py \
  --topic "black holes" \
  --length-seconds 120 \
  --scenes-count 5 \
  --retrieval-limit 3 \
  --output-dir black_holes_output
```

## License

Use as needed. Requires valid OpenRouter API key.
