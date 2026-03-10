"""
ChunkAnalyzer - The brain of the pipeline.

For each transcript chunk, uses Claude to:
1. Classify chunk type (CORE, INTRO, FILLER, JOKE, SPONSOR, TRANSITION, OUTRO)
2. Extract key points if it's CORE content
3. Identify concepts, definitions, action items
4. Score importance (0-10)

Maintains a rolling context so Claude understands what the video is about
as it processes each chunk — enabling smarter decisions.
"""

import json
import time
from dataclasses import dataclass, field
from typing import List, Optional

import litellm

from config import Config
from transcriber import TranscriptChunk


# Classification types for chunks
CHUNK_TYPES = {
    "CORE": "Main educational/informational content",
    "INTRO": "Introduction, channel/speaker intro, 'welcome back' type content",
    "OUTRO": "Closing remarks, subscribe reminders, thank you sections",
    "FILLER": "Repetitive recap, 'as I mentioned', 'so anyway', dead air",
    "JOKE": "Humor, tangents, off-topic banter",
    "SPONSOR": "Sponsorship or advertisement",
    "TRANSITION": "Topic transitions with no new content (very brief)",
    "QA": "Q&A or audience questions section",
}


@dataclass
class AnalyzedChunk:
    """A transcript chunk after AI analysis."""
    chunk: TranscriptChunk
    classification: str           # One of CHUNK_TYPES keys
    importance_score: int         # 0-10
    key_points: List[str] = field(default_factory=list)
    concepts: List[str] = field(default_factory=list)         # New terms/concepts defined
    action_items: List[str] = field(default_factory=list)     # Things to do/try
    section_title: Optional[str] = None                       # Inferred topic heading
    reasoning: str = ""                                       # Why it was classified this way

    @property
    def is_relevant(self) -> bool:
        return self.classification == "CORE" or (
            self.classification == "QA" and True  # Controlled by config
        )

    @property
    def start_timestamp(self) -> str:
        return self.chunk.start_timestamp

    @property
    def end_timestamp(self) -> str:
        return self.chunk.end_timestamp


class ChunkAnalyzer:
    """Analyzes transcript chunks using Claude with rolling context."""

    def __init__(self, config: Config):
        self.config = config
        self._rolling_context = ""   # Grows as we process chunks
        self._discovered_topics = [] # Topic headers found so far

    def analyze_all(
        self, chunks: List[TranscriptChunk], video_title: str, video_description: str = ""
    ) -> List[AnalyzedChunk]:
        """
        Analyze all chunks. Maintains rolling context across the video.
        """
        analyzed = []
        total = len(chunks)

        # First pass: get a quick overview of the video from the first chunk
        self._rolling_context = f'Video title: "{video_title}"\n'
        if video_description:
            self._rolling_context += f'Video Description (Context):\n{video_description[:1000]}...\n\n'

        for i, chunk in enumerate(chunks):
            if self.config.verbose:
                print(f"   Analyzing chunk {i+1}/{total} [{chunk.start_timestamp}–{chunk.end_timestamp}]")
            else:
                # Progress bar
                pct = (i + 1) / total
                bar_len = 30
                filled = int(bar_len * pct)
                bar = "█" * filled + "░" * (bar_len - filled)
                print(f"\r   [{bar}] {i+1}/{total}", end="", flush=True)

            analyzed_chunk = self._analyze_chunk(chunk, i, total)

            # Update rolling context with what we learned
            if analyzed_chunk.classification == "CORE" and analyzed_chunk.section_title:
                topic = analyzed_chunk.section_title
                if topic not in self._discovered_topics:
                    self._discovered_topics.append(topic)
                    self._rolling_context += f"- {topic}\n"

            analyzed.append(analyzed_chunk)

            # Small delay to respect rate limits
            if i < total - 1:
                time.sleep(0.3)

        print()  # Newline after progress bar
        return analyzed

    def _analyze_chunk(
        self, chunk: TranscriptChunk, index: int, total: int
    ) -> AnalyzedChunk:
        """Send one chunk to Claude for analysis."""

        is_early = index < 2
        is_late = index >= total - 2
        position_hint = (
            "This is near the BEGINNING of the video." if is_early else
            "This is near the END of the video." if is_late else
            f"This is chunk {index+1} of {total} (middle of the video)."
        )

        include_qa = self.config.keep_qa
        include_examples = self.config.keep_examples

        prompt = f"""You are analyzing a transcript chunk from a video to extract intelligent notes.

## Video Context (topics covered so far):
{self._rolling_context if self._rolling_context.strip() else "No prior context yet."}

## Current Chunk Info:
- Timestamp: [{chunk.start_timestamp} → {chunk.end_timestamp}]
- {position_hint}

## Transcript:
{chunk.text}

---

## Your Task:

1. **CLASSIFY** this chunk. Pick ONE:
   - CORE: Main educational/informational content worth keeping
   - INTRO: Speaker/channel introduction, "welcome back", "today we'll cover"
   - OUTRO: Closing remarks, "subscribe", "see you next time"  
   - FILLER: Recaps with no new info, "as I said", stutters, dead air
   - JOKE: Humor, tangents, personal anecdotes unrelated to topic
   - SPONSOR: Ad reads or sponsorship mentions
   - TRANSITION: Pure bridge between topics, no actual content
   - QA: Audience questions / Q&A section

2. **SCORE** importance 0-10 (10 = critical concept, 0 = pure filler)

3. If CORE: Extract **key_points** (bullet points of what was taught/explained).
   - {"Include examples and analogies as key points." if include_examples else "Skip examples and analogies."}
   - {"Include Q&A exchanges if relevant." if include_qa else "Skip Q&A exchanges."}
   - {self.config.detail_instruction}

4. List any **concepts** (new terms, frameworks, formulas defined in this chunk).

5. List any **action_items** (things the viewer should try, do, or remember to apply).

6. Give a short **section_title** IF this chunk is CORE (3-6 words summarizing the topic).

7. Brief **reasoning** for your classification (1 sentence).

## Respond in JSON only (no markdown, no preamble):
{{
  "classification": "CORE",
  "importance_score": 8,
  "key_points": ["Point 1", "Point 2"],
  "concepts": ["Term: definition"],
  "action_items": ["Do X", "Try Y"],
  "section_title": "How Neural Networks Learn",
  "reasoning": "Chunk covers backpropagation algorithm in detail."
}}"""

        try:
            response = litellm.completion(
                model=self.config.current_model,
                max_tokens=self.config.max_tokens_per_chunk,
                messages=[{"role": "user", "content": prompt}],
                # We can add response_format={"type": "json_object"} if provider supports it, 
                # but standard prompting usually works.
            )

            raw = response.choices[0].message.content.strip()
            # Strip markdown fences if present
            raw = raw.replace("```json", "").replace("```", "").strip()
            data = json.loads(raw)

            return AnalyzedChunk(
                chunk=chunk,
                classification=data.get("classification", "FILLER"),
                importance_score=int(data.get("importance_score", 0)),
                key_points=data.get("key_points", []),
                concepts=data.get("concepts", []),
                action_items=data.get("action_items", []),
                section_title=data.get("section_title"),
                reasoning=data.get("reasoning", ""),
            )

        except (json.JSONDecodeError, Exception) as e:
            if self.config.verbose:
                print(f"\n   Warning: Analysis failed for chunk {index}: {e}")
            # Fallback: treat as CORE with empty extraction
            return AnalyzedChunk(
                chunk=chunk,
                classification="CORE",
                importance_score=5,
                key_points=[chunk.text[:300] + "..." if len(chunk.text) > 300 else chunk.text],
                reasoning="Fallback: analysis failed",
            )
