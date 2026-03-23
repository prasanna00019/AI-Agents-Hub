from sqlalchemy import select, func
from src.backend.db.database import get_session_factory
from src.backend.core.config import settings
from src.backend.models.content_models import EmbeddingRecord

def verify():
    # Force use of local docker connection for this script
    db_url = "postgresql://postgres:radha@localhost:5433/CONTENT"
    print(f"Connecting to database: {db_url}")
    
    Session = get_session_factory(db_url)
    with Session() as session:
        # Get count using SQLAlchemy 2.0 syntax
        count = session.scalar(select(func.count()).select_from(EmbeddingRecord))
        
        if count == 0:
            print("\n❌ The embeddings table is EMPTY.")
            print("Try generating some content first so the RAG pipeline processes documents.")
            return

        print(f"\n✅ SUCCESS: Found {count} embedding chunks stored via pgvector!")
        
        # Show top 3 recent
        recent = session.scalars(select(EmbeddingRecord).order_by(EmbeddingRecord.created_at.desc()).limit(3)).all()
        print("\n--- Most Recent Chunks ---")
        for chunk in recent:
            print(f"- [ID: {chunk.id[:8]}] Source: {chunk.source_url or chunk.source_title or 'Provided text'}")
            print(f"  Length: {len(chunk.chunk_text)} chars | Hash: {chunk.content_hash}")
            print(f"  Kind: {chunk.kind} | Metadata: {chunk.metadata_json.keys()}")

if __name__ == "__main__":
    verify()
