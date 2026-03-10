import os
import chromadb
from chromadb.config import Settings
import litellm
import uuid

from config import Config
from analyzer import AnalyzedChunk
from transcriber import TranscriptChunk

class VideoRAGEngine:
    """
    Retrieval-Augmented Generation engine for answering follow-up questions 
    about the video using the extracted chunks.
    """
    
    def __init__(self, config: Config, video_id: str):
        self.config = config
        self.video_id = video_id
        
        # Initialize an in-memory or persistent Chroma client for this run
        db_path = os.path.join(self.config.temp_dir, f"chroma_{self.video_id}")
        self.client = chromadb.PersistentClient(path=db_path)
        
        # Using open-source Sentence Transformers embedding model by default via Chroma
        # Alternatively, we could wire up litellm embeddings.
        self.collection = self.client.get_or_create_collection(
            name=f"video_{self.video_id}"
        )

    def populate_database(self, analyzed_chunks: list[AnalyzedChunk], raw_description: str):
        """Insert analyzed chunks into ChromaDB."""
        
        documents = []
        metadatas = []
        ids = []

        # Add the video description as general context
        if raw_description:
            documents.append(raw_description)
            metadatas.append({"type": "description", "start": "00:00", "end": "00:00"})
            ids.append(f"desc_{self.video_id}")

        for i, chunk in enumerate(analyzed_chunks):
            # We index both the generated summary AND the raw transcript text for richer search
            doc_text = f"Section: {chunk.section_title}\nTranscript: {chunk.chunk.text}\nSummary Key Points: {', '.join(chunk.key_points)}"
            
            documents.append(doc_text)
            metadatas.append({
                "type": "chunk",
                "start": chunk.start_timestamp,
                "end": chunk.end_timestamp,
                "importance": chunk.importance_score
            })
            ids.append(f"chunk_{self.video_id}_{i}")

        if documents:
            self.collection.upsert(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )

    def populate_from_cache(self, notes: str, raw_description: str):
        """Insert cached notes and description directly into ChromaDB to enable basic Q&A."""
        documents = []
        metadatas = []
        ids = []

        if raw_description:
            documents.append(raw_description)
            metadatas.append({"type": "description", "start": "00:00", "end": "00:00"})
            ids.append(f"desc_{self.video_id}")

        if notes:
            # Simple chunking: split markdown mostly by headings or double newlines
            chunks = [c.strip() for c in notes.split('\n\n') if len(c.strip()) > 10]
            for i, chunk_text in enumerate(chunks):
                documents.append(chunk_text)
                metadatas.append({"type": "cached_note", "start": "00:00", "end": "00:00"})
                ids.append(f"cached_{self.video_id}_{i}")

        if documents:
            self.collection.upsert(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )

    def ask_question(self, question: str, history: list = None) -> str:
        """Query the vector database and use the LLM to formulate an answer."""
        
        # 1. Retrieve most relevant chunks
        n_results = min(3, self.collection.count())
        if n_results == 0:
            return "The video's context is currently empty (probably loaded from cache without vector data re-embedded). I cannot answer specific questions right now."
            
        results = self.collection.query(
            query_texts=[question],
            n_results=n_results  # Top 3 most relevant chunks or max available
        )
        
        if not results["documents"] or not results["documents"][0]:
            return "I couldn't find any information relevant to your question in the video."

        # 2. Format the context
        context_texts = []
        for i, doc in enumerate(results["documents"][0]):
            meta = results["metadatas"][0][i]
            if meta["type"] == "description":
                context_texts.append(f"[Video Description]:\n{doc}")
            elif meta.get("type") == "cached_note":
                context_texts.append(f"[Video Notes Section]:\n{doc}")
            else:
                context_texts.append(f"[Time: {meta.get('start', '00:00')} - {meta.get('end', '00:00')}]:\n{doc}")
                
        context = "\n\n".join(context_texts)
        
        # 3. Formulate the prompt
        prompt = f"""You are an intelligent assistant helping a user understand a video.
Answer the user's question based strictly on the provided context from the video.
If the answer is not contained in the context, say "I don't have enough information from the video to answer that."

Context from the video:
---
{context}
---

Question: {question}
Answer:"""

        # 4. Generate the answer
        response = litellm.completion(
            model=self.config.current_model,
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.choices[0].message.content.strip()
