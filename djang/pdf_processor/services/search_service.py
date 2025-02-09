import os
import logging
from typing import List, Dict
from sentence_transformers import SentenceTransformer
from ..vector_store import VectorStore

logger = logging.getLogger(__name__)

class SearchService:
   
   
   
    instance = None
    _initialized = False
    def __new__(cls):
        if cls.instance is None:
            cls.instance = super(SearchService, cls).__new__(cls)
        return cls.instance
   
   
    def __init__(self):
        if not self._initialized:
            self.model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
            self.model.max_seq_length = 256
            
            self.vector_store = VectorStore(dimension=384)
            try:
                self.vector_store.load()
                logger.info("Loaded existing vector store")
            except Exception as e:
                logger.warning(f"Could not load vector store: {str(e)}")
                logger.info("Creating new vector store")
            
            SearchService._initialized = True

    def add_to_index(self, title: str, embeddings, text: str, document_id: int, 
                    owner_id: int, group_ids: List[int], permission_ids: List[int]):
        """Add document to search index"""
        try:
            self.vector_store.add_documents([title], embeddings)
            logger.info(f"Added document to index: {title}")
        except Exception as e:
            logger.error(f"Error adding document to index: {str(e)}")
            raise

    def search(self, query: str, user=None, k: int = 5) -> List[Dict]:
        """Search documents"""
        try:
            logger.info(f"Processing search query: {query}")
            
            # Generate query embedding
            query_embedding = self.model.encode(query)
            
            # Search using vector store
            results = self.vector_store.search(
                query_vector=query_embedding,
                query_text=query,
                k=k,
                threshold=0.3
            )
            
            logger.info(f"Found {len(results)} results for query: {query}")
            
            # Format results
            formatted_results = []
            for path, score, preview in results:
                formatted_results.append({
                    'path': path,
                    'title': os.path.basename(path),
                    'content': preview,
                    'score': score
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error during search: {str(e)}")
            return []
    def get_document_content(self, document_id: int, user=None) -> str:
        """Get document content"""
        try:
            # Implementation for getting document content
            pass
        except Exception as e:
            logger.error(f"Error getting document content: {str(e)}")
            return None

    def answer_question(self, document_id: int, question: str, user=None) -> Dict:
        """Answer a question about a document"""
        try:
            # Implementation for answering questions
            pass
        except Exception as e:
            logger.error(f"Error answering question: {str(e)}")
            return None
