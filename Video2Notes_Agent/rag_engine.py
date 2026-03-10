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

    def ask_question(self, question: str, history: list = None) -> str:
        """Query the vector database and use the LLM to formulate an answer."""
        
        # 1. Retrieve most relevant chunks
        results = self.collection.query(
            query_texts=[question],
            n_results=3  # Top 3 most relevant chunks
        )
        
        if not results["documents"] or not results["documents"][0]:
            return "I couldn't find any information relevant to your question in the video."

        # 2. Format the context
        context_texts = []
        for i, doc in enumerate(results["documents"][0]):
            meta = results["metadatas"][0][i]
            if meta["type"] == "description":
                context_texts.append(f"[Video Description]:\n{doc}")
            else:
                context_texts.append(f"[Time: {meta['start']} - {meta['end']}]:\n{doc}")
                
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
