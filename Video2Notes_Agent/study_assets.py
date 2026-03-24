import json
import re

import litellm

from config import Config


def _fallback_glossary(notes: str) -> list[dict]:
    glossary = []
    for match in re.finditer(r"\*\*(.+?)\*\*\s*[—-]\s*(.+)", notes or ""):
        glossary.append(
            {
                "term": match.group(1).strip(),
                "definition": match.group(2).strip(),
            }
        )
    return glossary[:12]


class StudyAssetsGenerator:
    def __init__(self, config: Config):
        self.config = config

    def generate(self, video_title: str, notes: str) -> dict:
        prompt = f"""Create study assets from the following notes for "{video_title}".

Return JSON only with this exact shape:
{{
  "flashcards": [{{"front": "Question", "back": "Answer"}}],
  "quiz": [{{"question": "Question", "answer": "Answer"}}],
  "revision_sheet": "Short markdown revision sheet",
  "glossary": [{{"term": "Term", "definition": "Definition"}}]
}}

Rules:
- 6 to 10 flashcards
- 5 to 8 quiz questions
- revision_sheet should be concise markdown
- glossary should contain the most important terms only

Notes:
{notes}
"""
        try:
            response = litellm.completion(
                model=self.config.current_model,
                max_tokens=1800,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.choices[0].message.content.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            payload = json.loads(raw)
        except Exception:
            payload = {
                "flashcards": [],
                "quiz": [],
                "revision_sheet": notes[:1200],
                "glossary": _fallback_glossary(notes),
            }

        payload.setdefault("flashcards", [])
        payload.setdefault("quiz", [])
        payload.setdefault("revision_sheet", "")
        payload.setdefault("glossary", [])
        return payload
