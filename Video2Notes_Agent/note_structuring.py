import re
from dataclasses import dataclass, field

from analyzer import AnalyzedChunk


@dataclass
class StructuredSection:
    title: str
    timestamps: list[str] = field(default_factory=list)
    key_points: list[str] = field(default_factory=list)
    concepts: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)
    supporting_text: list[str] = field(default_factory=list)


def _normalize_title(title: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", (title or "").lower()).strip()
    return normalized or "general"


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    deduped = []
    for value in values:
        cleaned = re.sub(r"\s+", " ", (value or "").strip())
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(cleaned)
    return deduped


def structure_analyzed_chunks(chunks: list[AnalyzedChunk]) -> list[StructuredSection]:
    sections: list[StructuredSection] = []
    index_by_title: dict[str, int] = {}

    for chunk in chunks:
        if chunk.classification not in {"CORE", "QA"}:
            continue

        title = chunk.section_title or "Key Ideas"
        normalized_title = _normalize_title(title)
        if normalized_title in index_by_title:
            section = sections[index_by_title[normalized_title]]
        else:
            section = StructuredSection(title=title)
            index_by_title[normalized_title] = len(sections)
            sections.append(section)

        section.timestamps.append(f"{chunk.start_timestamp}-{chunk.end_timestamp}")
        section.key_points.extend(chunk.key_points)
        section.concepts.extend(chunk.concepts)
        section.action_items.extend(chunk.action_items)
        if chunk.chunk.text:
            section.supporting_text.append(chunk.chunk.text)

    for section in sections:
        section.timestamps = _dedupe(section.timestamps)
        section.key_points = _dedupe(section.key_points)
        section.concepts = _dedupe(section.concepts)
        section.action_items = _dedupe(section.action_items)
        section.supporting_text = _dedupe(section.supporting_text)

    return sections


def summarize_search_fields(sections: list[StructuredSection]) -> tuple[str, str]:
    concepts = []
    actions = []
    for section in sections:
        concepts.extend(section.concepts)
        actions.extend(section.action_items)
    return "\n".join(_dedupe(concepts)), "\n".join(_dedupe(actions))
