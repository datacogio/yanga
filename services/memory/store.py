import os
import time
import logging
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MemoryService")

class MemoryStore:
    def __init__(self, qdrant_host="localhost", qdrant_port=6333, collection_name="agent_memory", use_local=False, local_path="./qdrant_data"):
        self.collection_name = collection_name
        
        # Initialize Qdrant Client (Remote or Embedded)
        try:
            if use_local or qdrant_host == "local":
                logger.info(f"Connecting to Local Embedded Qdrant at: {local_path}")
                self.client = QdrantClient(path=local_path)
            else:
                logger.info(f"Connecting to Remote Qdrant at {qdrant_host}:{qdrant_port}")
                self.client = QdrantClient(host=qdrant_host, port=qdrant_port)
            
            logger.info("Qdrant Connected.")
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise e

        # Initialize Embedding Model (MiniLM is fast and good specific for semantic search)
        # In production, we might use OpenAI embeddings
        logger.info("Loading Embedding Model (all-MiniLM-L6-v2)...")
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Embedding Model Loaded.")

        # Ensure Collection Exists
        self._init_collection()

    def _init_collection(self):
        """Create the collection if it doesn't exist."""
        try:
            collections = self.client.get_collections()
            exists = any(c.name == self.collection_name for c in collections.collections)
            
            if not exists:
                logger.info(f"Creating collection '{self.collection_name}'...")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=384,  # Size for all-MiniLM-L6-v2
                        distance=models.Distance.COSINE
                    )
                )
            else:
                logger.info(f"Collection '{self.collection_name}' exists.")
        except Exception as e:
            logger.error(f"Failed to initialize collection: {e}")

    def add_memory(self, text: str, metadata: Dict[str, Any] = None):
        """
        Embeds text and stores it in Qdrant.
        """
        if not text:
            return False

        try:
            vector = self.encoder.encode(text).tolist()
            payload = metadata or {}
            payload["text"] = text
            payload["timestamp"] = time.time()

            operation_info = self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    models.PointStruct(
                        id=str(os.urandom(16).hex()),  # Simple random ID
                        vector=vector,
                        payload=payload
                    )
                ]
            )
            logger.info(f"Memory stored: '{text[:30]}...'")
            return True
        except Exception as e:
            logger.error(f"Failed to add memory: {e}")
            return False

    def search_memory(self, query: str, limit: int = 5, score_threshold: float = 0.5) -> List[Dict]:
        """
        Semantically searches memory for the query.
        """
        try:
            vector = self.encoder.encode(query).tolist()
            
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=vector,
                limit=limit,
                score_threshold=score_threshold
            )
            
            results = []
            for hit in search_result:
                results.append({
                    "text": hit.payload.get("text"),
                    "score": hit.score,
                    "metadata": hit.payload
                })
            
            return results
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

# Simple CLI test
if __name__ == "__main__":
    memory = MemoryStore(qdrant_host=os.getenv("QDRANT_HOST", "localhost"))
    
    # Test Add
    memory.add_memory("Project Polaris is due on Friday.", {"project": "Polaris"})
    memory.add_memory("The server key is 12345.", {"type": "secret"})
    
    # Test Search
    print("\n--- Searching for 'deadline' ---")
    results = memory.search_memory("When is the deadline?")
    for r in results:
        print(f"[{r['score']:.2f}] {r['text']}")
