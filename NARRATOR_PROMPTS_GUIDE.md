# Narrator Prompts Guide - Gemini TTS Audio Generation

This folder contains professionally crafted narrator prompts based on the official Gemini TTS Prompting Guide. Each prompt is optimized for specific educational YouTube content styles.

## How Narrator Prompts Work

**Narrator prompts serve as the BASE INSTRUCTION for audio generation.**

When you select a narrator prompt (Educational, Technical, or Motivational) and generate voice narration:

1. **Line-by-line Processing**: Your narration_draft_youtube.txt is read sentence by sentence
2. **Base Instruction Applied**: The selected narrator prompt is applied as performance guidance to EVERY sentence
3. **Consistent Voice Character**: Each line uses the same narrator prompt to ensure:
   - Consistent voice personality and character
   - Unified pacing and rhythm across all audio
   - Matching tone and style from beginning to end
   - Professional performance direction applied uniformly

**Example Flow:**
```
narration_draft_youtube.txt (from extract_narration.py)
│
├─ Line 1: "Neutron stars are..."
│   ↓ [Applied: narrator_prompt_educational.txt]
│   → 001.mp3 (Generated with Educational narrator guidance)
│
├─ Line 2: "With a density of..."
│   ↓ [Applied: narrator_prompt_educational.txt]
│   → 002.mp3 (Same narrator guidance applied)
│
├─ Line 3: "These objects..."
│   ↓ [Applied: narrator_prompt_educational.txt]
│   → 003.mp3 (Consistent voice character maintained)
│
└─ ... continues for all sentences ...
```

**Result**: All MP3 files sound like they're coming from the same narrator with consistent performance, even though each sentence is generated individually.

## Available Narrator Prompts

### 1. **narrator_prompt_educational.txt** (Default Recommended)
**Best for:** General educational content, science, history, how-to tutorials

**Characteristics:**
- Professional yet approachable narrator (Dr. Nova)
- Balanced pacing that allows information absorption
- Emphasis on key concepts with vocal dynamics
- Hooks viewers with curiosity and excitement
- Suitable for audiences aged 13-45

**Use case:** Most educational YouTube content
- Science explainers
- History lessons
- Tutorial content
- Educational documentaries
- General knowledge videos

---

### 2. **narrator_prompt_technical.txt**
**Best for:** Technical tutorials, coding, advanced topics, professional content

**Characteristics:**
- Technical expert narrator (Alex Chen)
- Deliberate, measured pacing
- Emphasis on accuracy and clarity over dramatization
- Authoritative but accessible tone
- Precise technical terminology delivery

**Use case:** Specialized educational content
- Programming tutorials
- Technical deep-dives
- Advanced academic content
- Professional skill development
- Science and engineering explanations

---

### 3. **narrator_prompt_motivational.txt**
**Best for:** Personal development, wellness, psychology, lifestyle content

**Characteristics:**
- Warm, inspiring narrator (Morgan Riley)
- Energetic yet conversational delivery
- Emotional authenticity and relatability
- Empathy-driven approach
- Encouragement and call-to-action focused

**Use case:** Motivational and self-improvement content
- Personal development courses
- Wellness and health education
- Psychology insights
- Self-help and productivity tips
- Lifestyle and mindset content

---

## How to Use

### Method 1: Via Command Line
```bash
python voice_generator.py \
    --narration ./output/narration_draft_youtube.txt \
    --narrator-prompt ./Prompts/narrator_prompt_educational.txt \
    --voice Charon \
    --speed 1.0
```

### Method 2: Via GUI ⭐ **EASIEST**
1. Launch the GUI: `python gui_launcher.py`
2. Generate video package and extract narration as usual
3. In the "Voice Generation Settings" section:
   - Select your desired **Narrator Prompt**: Educational, Technical, or Motivational
   - Choose **Voice**: Any of 30 available Gemini TTS voices
   - Adjust **Speed**: 0.5 (slow) to 2.0 (fast)
4. Click "Generate Voice Over" button
5. All lines from narration_draft_youtube.txt will be generated with your selected narrator prompt as the base instruction

The GUI automatically applies the selected narrator prompt to every sentence for consistent voice character across all audio files.

### Method 3: Programmatically
```python
from voice_generator import VoiceGenerator

generator = VoiceGenerator(
    api_key="your-api-key",
    voice="Charon",
    output_dir="./output/voice_over"
)

with open("./Prompts/narrator_prompt_educational.txt", "r") as f:
    narrator_prompt = f.read()

generator.generate_speech(
    text="Your narration text here",
    sentence_idx=1,
    narrator_prompt=narrator_prompt
)
```

---

## Understanding Narrator Prompts

Each narrator prompt follows the Gemini TTS official structure:

### Audio Profile
- Character name and role
- Sets persona for consistent voice delivery

### Scene
- Environmental context
- Establishes mood and vibe
- Influences how lines are delivered

### Director's Notes
Specific performance guidance:
- **Style**: Tone, delivery characteristics, vocal qualities
- **Pacing**: Speed, rhythm, and natural breathing
- **Accent**: Regional or professional accent guidance
- **Emotional Arc**: Journey from opening to close

### Sample Context
- Target audience description
- Viewer motivation and expectations
- Narrator positioning

### Transcript Guidelines
- Recommended audio tags for different content types
- Tag examples: [excitedly], [thoughtfully], [with emphasis]
- Tips for effective tag usage

---

## Audio Tags Reference

Common tags you can use in your narration (these work with any narrator prompt):

### Emotions & Attitudes
- [amazed] [curious] [excited] [frustrated]
- [playful] [sarcastic] [serious] [thoughtful]
- [reluctantly] [bored] [enthusiastically]

### Vocal Effects
- [whispers] [shouting] [sighs] [giggles] [laughs]
- [cough] [gasp] [crying] [panicked]

### Pace & Delivery
- [very fast] [fast] [slowly] [very slow]
- [emphasized] [hesitantly] [naturally]

### Style Variations
- [like a cartoon character] [like a news reporter]
- [sarcastically] [mysteriously] [tenderly]

---

## Tips for Best Results

1. **Match Prompt to Content**: Choose the narrator prompt that aligns with your content style
2. **Use Audio Tags Strategically**: Don't overuse tags; let them enhance key moments
3. **Test Different Voices**: Try different voices (Charon, Puck, Zephyr, etc.) with your chosen prompt
4. **Adjust Speed**: Use `--speed` parameter (0.5-2.0) to fine-tune delivery pace
5. **Keep Coherence**: Ensure your transcript and narrator prompt directions align
6. **Give the Model Space**: Avoid over-specifying; let the AI model's creativity shine
7. **Iterate**: Generate samples and refine based on results

---

## Creating Custom Narrator Prompts

You can create your own narrator prompts following this structure:

```markdown
# AUDIO PROFILE: [Character Name]
## [Content Type/Style]

## THE SCENE: [Environment Description]
[Detailed scene description that sets mood and context...]

### DIRECTOR'S NOTES

Style:
* [Key style elements]
* [Vocal characteristics]
* [Tone guidance]

Pacing:
* [Pace instructions]
* [Rhythm and breathing]

Accent:
* [Accent/clarity guidance]

[Additional custom directions as needed]

### SAMPLE CONTEXT
[Target audience and context...]

### TRANSCRIPT GUIDELINES
[Recommended audio tags and usage for this narrator type...]
```

For best results creating custom prompts, use an LLM like Claude or ChatGPT to help flesh out the character and performance directions.

---

## Troubleshooting

**Issue**: Audio sounds robotic or unclear
- Solution: Use the technical prompt with clearer enunciation guidance

**Issue**: Not enough energy or enthusiasm
- Solution: Use the educational or motivational prompt with higher voice variety

**Issue**: Too dramatic/not professional enough
- Solution: Use the technical prompt for more measured delivery

**Issue**: Pacing is too fast
- Solution: Adjust `--speed` parameter to 0.8 or 0.9, or request "slower pacing" in custom prompts

---

## References

- Official Gemini TTS Prompting Guide: https://ai.google.dev/docs/gemini-2-5-pro/text-to-speech-guide
- Supported Voices: 30+ options including Charon, Puck, Zephyr, and more
- Supported Languages: Multiple languages (use English audio tags for best results)

---

## Next Steps

1. Try each narrator prompt with sample content
2. A/B test different voices and prompts with your audience
3. Create custom prompts for niche content styles
4. Combine narrator prompts with strategic audio tag usage for optimal results
