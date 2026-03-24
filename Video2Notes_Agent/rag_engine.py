import os
import re
from typing import Iterable

import chromadb
import litellm

from analyzer import AnalyzedChunk
from config import Config
from note_structuring import StructuredSection


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", (value or "general").lower()).strip("-")
    return cleaned or "general"


def _coerce_list(value):
    if isinstance(value, list):
        return value
    return []


class VideoRAGEngine:
    """
    Parent-child retrieval engine with optional Hugging Face cross-encoder reranking.
    """

    _reranker = None
    _reranker_failed = False

    def __init__(self, config: Config, video_id: str):
        self.config = config
        self.video_id = video_id
        db_path = os.path.join(self.config.temp_dir, f"chroma_{self.video_id}")
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(name=f"video_{self.video_id}")

    @classmethod
    def _get_reranker(cls):
        if cls._reranker or cls._reranker_failed:
            return cls._reranker
        try:
            from sentence_transformers import CrossEncoder

            cls._reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        except Exception as exc:
            print(f"[VideoNotes RAG] Cross-encoder unavailable, falling back to vector-only retrieval: {exc}")
            cls._reranker_failed = True
            cls._reranker = None
        return cls._reranker

    def populate_database(
        self,
        analyzed_chunks: list[AnalyzedChunk],
        structured_sections: list[StructuredSection],
        raw_description: str,
    ):
        documents = []
        metadatas = []
        ids = []

        if raw_description:
            documents.append(raw_description)
            metadatas.append({"type": "parent", "parent_id": "description", "title": "Video Description", "start": "00:00", "end": "00:00"})
            ids.append(f"parent_desc_{self.video_id}")

        section_parent_map = {}
        for index, section in enumerate(structured_sections):
            parent_id = f"parent_{index}_{_slugify(section.title)}"
            section_parent_map[_slugify(section.title)] = parent_id
            summary = "\n".join(
                [f"Section: {section.title}"]
                + [f"- {point}" for point in section.key_points[:8]]
                + [f"Concept: {concept}" for concept in section.concepts[:6]]
                + [f"Action: {action}" for action in section.action_items[:6]]
            )
            documents.append(summary)
            metadatas.append(
                {
                    "type": "parent",
                    "parent_id": parent_id,
                    "title": section.title,
                    "start": section.timestamps[0] if section.timestamps else "00:00",
                    "end": section.timestamps[-1] if section.timestamps else "00:00",
                }
            )
            ids.append(f"{parent_id}_{self.video_id}")

        for index, chunk in enumerate(analyzed_chunks):
            normalized_title = _slugify(chunk.section_title or "general")
            parent_id = section_parent_map.get(normalized_title, "description")
            doc_text = "\n".join(
                [
                    f"Section: {chunk.section_title or 'General'}",
                    f"Transcript: {chunk.chunk.text}",
                    f"Key Points: {', '.join(_coerce_list(chunk.key_points))}",
                ]
            )
            documents.append(doc_text)
            metadatas.append(
                {
                    "type": "child",
                    "parent_id": parent_id,
                    "title": chunk.section_title or "General",
                    "start": chunk.start_timestamp,
                    "end": chunk.end_timestamp,
                    "importance": chunk.importance_score,
                }
            )
            ids.append(f"child_{self.video_id}_{index}")

        if documents:
            self.collection.upsert(documents=documents, metadatas=metadatas, ids=ids)

    def populate_from_cache(self, notes: str, raw_description: str):
        documents = []
        metadatas = []
        ids = []

        if raw_description:
            documents.append(raw_description)
            metadatas.append({"type": "parent", "parent_id": "description", "title": "Video Description", "start": "00:00", "end": "00:00"})
            ids.append(f"parent_desc_{self.video_id}")

        sections = self._sections_from_notes(notes)
        for index, section in enumerate(sections):
            parent_id = f"cached_parent_{index}_{_slugify(section['title'])}"
            documents.append(f"Section: {section['title']}\n{section['content']}")
            metadatas.append({"type": "parent", "parent_id": parent_id, "title": section["title"], "start": "00:00", "end": "00:00"})
            ids.append(f"{parent_id}_{self.video_id}")

            for child_index, paragraph in enumerate(section["children"]):
                documents.append(paragraph)
                metadatas.append({"type": "child", "parent_id": parent_id, "title": section["title"], "start": "00:00", "end": "00:00", "importance": 5})
                ids.append(f"cached_child_{self.video_id}_{index}_{child_index}")

        if documents:
            self.collection.upsert(documents=documents, metadatas=metadatas, ids=ids)

    def ask_question(self, question: str, history: list = None) -> str:
        total_docs = self.collection.count()
        if total_docs == 0:
            return "The video's context is currently empty. I cannot answer specific questions right now."

        parent_results = self.collection.query(
            query_texts=[question],
            n_results=min(4, total_docs),
            where={"type": "parent"},
        )
        child_results = self.collection.query(
            query_texts=[question],
            n_results=min(10, total_docs),
            where={"type": "child"},
        )

        candidate_items = self._merge_candidates(parent_results, child_results)
        reranked_items = self._rerank_candidates(question, candidate_items)

        if not reranked_items:
            return "I couldn't find any information relevant to your question in the video."

        context_text = []
        for item in reranked_items[:5]:
            meta = item["meta"]
            label = meta.get("title") or meta.get("parent_id") or "Context"
            context_text.append(
                f"[Section: {label} | {meta.get('start', '00:00')} - {meta.get('end', '00:00')}]\n{item['document']}"
            )

        context = "\n\n".join(context_text)
        prompt = f"""You are an intelligent assistant helping a user understand a video.
Answer the user's question based strictly on the provided context from the video.
If the answer is not contained in the context, say "I don't have enough information from the video to answer that."

Context from the video:
---
{context}
---

Question: {question}
Answer:"""

        response = litellm.completion(
            model=self.config.current_model,
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()

    def _sections_from_notes(self, notes: str) -> list[dict]:
        sections = []
        current_title = "Overview"
        current_lines = []
        for line in (notes or "").splitlines():
            if line.startswith("## "):
                if current_lines:
                    sections.append(self._build_cached_section(current_title, current_lines))
                current_title = line[3:].strip()
                current_lines = []
            else:
                current_lines.append(line)
        if current_lines:
            sections.append(self._build_cached_section(current_title, current_lines))
        return sections

    def _build_cached_section(self, title: str, lines: Iterable[str]) -> dict:
        content = "\n".join(lines).strip()
        children = [chunk.strip() for chunk in content.split("\n\n") if len(chunk.strip()) > 20]
        return {"title": title, "content": content, "children": children or ([content] if content else [])}

    def _merge_candidates(self, parent_results: dict, child_results: dict) -> list[dict]:
        parent_docs = parent_results.get("documents", [[]])[0] if parent_results.get("documents") else []
        parent_meta = parent_results.get("metadatas", [[]])[0] if parent_results.get("metadatas") else []
        child_docs = child_results.get("documents", [[]])[0] if child_results.get("documents") else []
        child_meta = child_results.get("metadatas", [[]])[0] if child_results.get("metadatas") else []

        top_parent_ids = {meta.get("parent_id") for meta in parent_meta if meta}
        candidates = []
        seen = set()

        for document, meta in zip(parent_docs, parent_meta):
            key = ("parent", meta.get("parent_id"))
            if key in seen:
                continue
            seen.add(key)
            candidates.append({"document": document, "meta": meta})

        for document, meta in zip(child_docs, child_meta):
            key = ("child", document)
            if key in seen:
                continue
            if meta.get("parent_id") in top_parent_ids or len(candidates) < 8:
                seen.add(key)
                candidates.append({"document": document, "meta": meta})

        return candidates

    def _rerank_candidates(self, question: str, candidates: list[dict]) -> list[dict]:
        reranker = self._get_reranker()
        if not reranker or not candidates:
            return candidates

        try:
            pairs = [(question, item["document"]) for item in candidates]
            scores = reranker.predict(pairs)
            reranked = sorted(
                zip(scores, candidates),
                key=lambda item: item[0],
                reverse=True,
            )
            return [candidate for _, candidate in reranked]
        except Exception as exc:
            print(f"[VideoNotes RAG] Reranking failed, using vector-only ranking: {exc}")
            return candidates
