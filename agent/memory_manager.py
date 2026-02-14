import os
import yaml
import logging
import json
from datetime import datetime
from sqlalchemy import create_engine, text, Column, Integer, String, DateTime, JSON
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from langchain_postgres.vectorstores import PGVector
from langchain_ollama import OllamaEmbeddings
from pathlib import Path

logger = logging.getLogger("MemoryManager")
Base = declarative_base()

class ActivityLog(Base):
    __tablename__ = 'activity_log'
    id = Column(Integer, primary_key=True)
    action = Column(String)
    status = Column(String)
    details = Column(JSONB)
    timestamp = Column(DateTime, default=datetime.utcnow)

class MemoryManager:
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        mem_config = self.config.get("memory", {})
        
        self.db_url = os.getenv("DB_URL", mem_config.get("postgres_url", "postgresql://postgres:password@localhost:5432/agent_memory"))
        self.engine = create_engine(self.db_url)
        self.Session = sessionmaker(bind=self.engine)
        
        # Initialize Vector Store
        self.embedding_model = self._get_embedding_model(mem_config)
        self.vector_store = PGVector(
            embeddings=self.embedding_model,
            collection_name="memories",
            connection=self.db_url,
            use_jsonb=True,
        )
        
        self._init_db()

    def _load_config(self, path: str) -> dict:
        try:
            p = Path(path)
            if not p.exists():
                p = Path("/app") / path
            if p.exists():
                with open(p, "r") as f:
                    return yaml.safe_load(f)
            return {}
        except Exception:
            return {}

    def _get_embedding_model(self, config):
        provider = config.get("embedding_provider", "ollama")
        base_url = os.getenv("OLLAMA_BASE_URL", config.get("embedding_base_url", "http://localhost:11434"))
        model = config.get("embedding_model", "nomic-embed-text")
        
        if provider == "ollama":
            return OllamaEmbeddings(base_url=base_url, model=model)
        else:
            # Fallback or support other providers
            return OllamaEmbeddings(base_url=base_url, model=model)

    def _init_db(self):
        # Create extensions and tables
        try:
            with self.engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.commit()
            
            Base.metadata.create_all(self.engine)
            # PGVector manages its own tables usually, but we ensure our custom log table exists
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")

    def log_activity(self, action: str, status: str, details: dict = None):
        session = self.Session()
        try:
            log_entry = ActivityLog(
                action=action,
                status=status,
                details=details or {}
            )
            session.add(log_entry)
            session.commit()
            logger.info(f"Activity logged: {action} - {status}")
        except Exception as e:
            logger.error(f"Failed to log activity: {e}")
            session.rollback()
        finally:
            session.close()

    def store_memory(self, text: str, metadata: dict = None):
        """Stores a semantic memory"""
        self.vector_store.add_texts([text], metadatas=[metadata or {}])

    def recall(self, query: str, k: int = 4):
        """Recalls memories based on semantic similarity"""
        return self.vector_store.similarity_search(query, k=k)
