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
uv sync
```

### 2. Set Your API Keys (Optional)

You can run elements locally or choose to use incredibly fast cloud solutions.

```bash
# Recommended: For intelligent note synthesis and analysis (Choose one)
export GEMINI_API_KEY="AIzaSy..."          # For Gemini 2.5 Flash
export ANTHROPIC_API_KEY="sk-ant-..."      # For Claude 3.5 Sonnet
export OLLAMA_API_BASE="http://localhost:11434" # For Local LLMs

# Recommended: For lightning-fast audio transcription
export GROQ_API_KEY="gsk_..."              # Groq Cloud Whisper API 
```

### 3. Run FastAPI Backend & React Frontend

```bash
# Start the Backend Server
uvicorn api:app --reload

# Start the Frontend (In a separate terminal)
cd frontend
npm run dev
```

---

## Features & Architecture

```
Video/URL
   ↓
[Audio Extraction]     — FFmpeg or yt-dlp (Outputs 16kHz MP3 optimized for Whisper)
   ↓
[Audio Transcription]  — Choose Local Whisper (CPU/GPU) OR Groq Cloud Whisper API (Lightning-fast)
   ↓
[Smart Chunking]       — ~2 min windows with 15s overlap to preserve chronological context
   ↓
[LLM Analysis]         — Uses Gemini/Claude/Ollama to analyze topics iteratively:
    • Classify: CORE / INTRO / QA / SPONSOR
    • Extract: Structurally group raw transcripts into logical key points
    • Score: Importance 0-10
   ↓
[LLM Synthesis]        — Final merge into unified Markdown + Database Storage
   ↓
[RAG Engine]           — Locally vector-embeds notes using ChromaDB for follow-up semantic Q&A Chat
```

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
