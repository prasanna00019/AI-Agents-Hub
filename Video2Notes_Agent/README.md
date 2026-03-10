# 🎬 Video2Notes — Intelligent Video to Notes Agent

Turn any long video into clean, structured study notes using AI.

**What makes it smart:**
-  Prunes intros, outros, jokes, sponsors, fillers
-  Each chunk analyzed with context of the full video
-  Notes organized by **topic**, not just time order
-  Timestamps preserved so you can jump back to source
-  Configurable detail level (low / medium / high)

---

## Quick Start

### 1. Install Dependencies

```bash
# Install Python packages
pip install -r requirements.txt

# Install FFmpeg (required for local video files)
# macOS:
brew install ffmpeg

# Ubuntu/Debian:
sudo apt install ffmpeg
```

### 2. Set Your Anthropic API Key

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### 3. Run

```bash
# From a YouTube URL
python main.py --url "https://www.youtube.com/watch?v=VIDEO_ID"

# From a local video file
python main.py --file lecture.mp4

# More options
python main.py --url "..." --model large-v3 --detail high --chunk-size 3
```

---

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--url` | — | YouTube or video URL |
| `--file` | — | Local video/audio file |
| `--output` | `<title>_notes.md` | Output file path |
| `--format` | `markdown` | `markdown` or `json` |
| `--chunk-size` | `2` | Minutes per analysis chunk |
| `--model` | `base` | Whisper model: `tiny`, `base`, `small`, `medium`, `large-v2`, `large-v3` |
| `--detail` | `medium` | Notes detail: `low`, `medium`, `high` |
| `--language` | auto | Force language (e.g., `en`, `es`, `fr`) |
| `--keep-qa` | off | Include Q&A sections |
| `--timestamps` | on | Include `[MM:SS]` in notes |
| `-v` | off | Verbose mode |

---

## Model Size Guide

| Whisper Model | Speed | Accuracy | RAM |
|---------------|-------|----------|-----|
| `tiny` | ⚡⚡⚡⚡⚡ | ⭐⭐ | ~1GB |
| `base` | ⚡⚡⚡⚡ | ⭐⭐⭐ | ~1GB |
| `small` | ⚡⚡⚡ | ⭐⭐⭐⭐ | ~2GB |
| `medium` | ⚡⚡ | ⭐⭐⭐⭐ | ~5GB |
| `large-v3` | ⚡ | ⭐⭐⭐⭐⭐ | ~10GB |

**Recommendation:** `base` for quick testing, `large-v3` for final notes.

---

## How It Works

```
Video/URL
   ↓
[Audio Extraction]     — FFmpeg or yt-dlp
   ↓
[Whisper Transcription] — with word timestamps + VAD silence filtering
   ↓
[Smart Chunking]        — ~2 min windows with 15s overlap
   ↓
[Claude Analysis]       — per chunk, with rolling context:
    • Classify: CORE / INTRO / OUTRO / FILLER / JOKE / SPONSOR / QA
    • Extract: key points, concepts, action items
    • Score: importance 0–10
   ↓
[Claude Synthesis]      — merge CORE chunks into structured notes
   ↓
[Markdown Output]       — organized by topic, with timestamps
```

---

## Output Example

```markdown
# How Transformers Work — The Illustrated Guide

**Summary:** This video explains the Transformer architecture from first principles, 
covering attention mechanisms, positional encoding, and the encoder-decoder structure.

## Self-Attention Mechanism
- Every token in a sequence attends to every other token [04:32]
- **Query, Key, Value** matrices are learned projections of the input
- Attention score = softmax(QKᵀ / √d_k) — scaling prevents gradient vanishing [06:15]
  
 **Scaled Dot-Product Attention** — the core operation: compute similarity between 
   query and all keys, normalize with softmax, use as weights for values

## Positional Encoding
- Transformers have no inherent notion of order (unlike RNNs) [11:40]
- Position info injected via sinusoidal functions added to embeddings

## Action Items
- [ ] Implement self-attention from scratch in PyTorch
- [ ] Read "Attention Is All You Need" (Vaswani et al. 2017)
```

---

## Tips

- Use `--chunk-size 1` for dense technical content (more granular analysis)
- Use `--chunk-size 4` for conversational/interview style videos (fewer API calls)
- Use `--detail high` for lectures you want to study from
- Use `--detail low` for a quick overview before deciding if a video is worth watching
- `large-v3` + `high` detail = best quality, but slower and more API tokens
