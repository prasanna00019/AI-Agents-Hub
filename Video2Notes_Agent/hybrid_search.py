import hashlib
import math
import re
from collections import Counter
from typing import Callable, Iterable, TypeVar


T = TypeVar("T")


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def _normalize_scores(scores: list[float]) -> list[float]:
    if not scores:
        return []
    maximum = max(scores)
    minimum = min(scores)
    if maximum - minimum < 1e-9:
        return [1.0 if maximum > 0 else 0.0 for _ in scores]
    return [(score - minimum) / (maximum - minimum) for score in scores]


def _cosine_similarity(left, right) -> float:
    return float(sum(a * b for a, b in zip(left, right)))


class HybridSearchRanker:
    """
    Hybrid search using BM25-style lexical matching plus optional vector similarity.
    Falls back to BM25-only when the sentence-transformers encoder is unavailable.
    """

    _encoder = None
    _encoder_failed = False
    _embedding_cache: dict[str, list[float]] = {}

    @classmethod
    def _get_encoder(cls):
        if cls._encoder or cls._encoder_failed:
            return cls._encoder
        try:
            from sentence_transformers import SentenceTransformer

            cls._encoder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        except Exception as exc:
            print(f"Hybrid search vector encoder unavailable, falling back to BM25-only search: {exc}")
            cls._encoder_failed = True
            cls._encoder = None
        return cls._encoder

    @classmethod
    def _embed_texts(cls, texts: list[str]) -> list[list[float]] | None:
        encoder = cls._get_encoder()
        if not encoder or not texts:
            return None

        embeddings: list[list[float] | None] = [None] * len(texts)
        uncached_texts: list[str] = []
        uncached_indices: list[int] = []

        for index, text in enumerate(texts):
            key = hashlib.sha256(text.encode("utf-8")).hexdigest()
            cached = cls._embedding_cache.get(key)
            if cached is not None:
                embeddings[index] = cached
                continue
            uncached_texts.append(text)
            uncached_indices.append(index)

        if uncached_texts:
            encoded = encoder.encode(uncached_texts, normalize_embeddings=True)
            for index, vector in zip(uncached_indices, encoded):
                embedding = vector.tolist() if hasattr(vector, "tolist") else list(vector)
                key = hashlib.sha256(texts[index].encode("utf-8")).hexdigest()
                cls._embedding_cache[key] = embedding
                embeddings[index] = embedding

        return [embedding or [] for embedding in embeddings]

    @staticmethod
    def _bm25_scores(query: str, documents: list[str]) -> list[float]:
        query_tokens = _tokenize(query)
        tokenized_documents = [_tokenize(document) for document in documents]
        if not query_tokens or not tokenized_documents:
            return [0.0 for _ in documents]

        document_frequencies: Counter[str] = Counter()
        document_lengths = []
        token_frequencies = []
        for tokens in tokenized_documents:
            counts = Counter(tokens)
            token_frequencies.append(counts)
            document_lengths.append(len(tokens))
            for token in counts:
                document_frequencies[token] += 1

        avg_doc_length = sum(document_lengths) / max(len(document_lengths), 1)
        k1 = 1.5
        b = 0.75
        scores = []

        for counts, document_length in zip(token_frequencies, document_lengths):
            score = 0.0
            for token in query_tokens:
                frequency = counts.get(token, 0)
                if not frequency:
                    continue
                doc_freq = document_frequencies.get(token, 0)
                idf = math.log(1 + ((len(documents) - doc_freq + 0.5) / (doc_freq + 0.5)))
                denominator = frequency + k1 * (1 - b + b * (document_length / max(avg_doc_length, 1)))
                score += idf * ((frequency * (k1 + 1)) / max(denominator, 1e-9))
            scores.append(score)

        return scores

    @classmethod
    def rank(cls, query: str, items: Iterable[T], text_getter: Callable[[T], str]) -> list[T]:
        items = list(items)
        if not query.strip() or not items:
            return items

        documents = [text_getter(item) or "" for item in items]
        bm25_scores = cls._bm25_scores(query, documents)
        bm25_normalized = _normalize_scores(bm25_scores)

        vector_scores = [0.0 for _ in items]
        embeddings = cls._embed_texts([query] + documents)
        if embeddings and len(embeddings) == len(documents) + 1:
            query_embedding = embeddings[0]
            document_embeddings = embeddings[1:]
            if query_embedding and any(document_embeddings):
                raw_scores = [
                    _cosine_similarity(query_embedding, document_embedding)
                    if document_embedding
                    else 0.0
                    for document_embedding in document_embeddings
                ]
                vector_scores = _normalize_scores(raw_scores)

        scored = []
        for index, item in enumerate(items):
            combined = (0.6 * bm25_normalized[index]) + (0.4 * vector_scores[index])
            scored.append((combined, index, item))

        scored.sort(key=lambda row: (row[0], -row[1]), reverse=True)
        return [item for _, _, item in scored]
