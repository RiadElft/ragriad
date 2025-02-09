import os
import logging
import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
import pickle
from typing import Dict, List, Tuple, TYPE_CHECKING
import sqlite3
from datetime import datetime
from django.conf import settings

logger = logging.getLogger(__name__)

def extract_text_from_pdf(pdf_path: str) -> str:    
    try:
        doc = fitz.open(pdf_path)
        text = ''
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
        return None
class VectorStore:
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)
        self.db_path = 'djang/modelrag/output/vector_store.db'
        self.current_id = 0
        self.id_to_path = {}
        self.model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
        self._init_db()
        self._load_existing_paths()

    def _init_db(self):
        """Initialize the database if it doesn't exist"""
        try:
            # Create directory if it doesn't exist
            os.makedirs('djang/modelrag/output', exist_ok=True)
            
            # Create database if it doesn't exist
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Create table if it doesn't exist
            c.execute('''CREATE TABLE IF NOT EXISTS documents
                        (id INTEGER PRIMARY KEY,
                        path TEXT UNIQUE,
                        added_date TEXT)''')
            
            conn.commit()
            conn.close()
            
            print("Database initialized successfully")
            
        except Exception as e:
            print(f"Error in _init_db: {str(e)}")
            raise

    def _load_existing_paths(self):
        """Load existing document paths from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("SELECT id, path FROM documents")
            for id_, path in c.fetchall():
                self.id_to_path[id_] = path
                self.current_id = max(self.current_id, id_)
            conn.close()
        except Exception as e:
            print(f"Error loading existing paths: {str(e)}")
            raise
    def save(self):
        """Save the FAISS index and document mappings"""
        try:
            output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'modelrag', 'output')
            os.makedirs(output_dir, exist_ok=True)
            
            index_path = os.path.join(output_dir, 'faiss.index')
            print(f"Saving FAISS index to {index_path}")
            faiss.write_index(self.index, index_path)
            
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('DELETE FROM documents')
            
            current_date = datetime.now().isoformat()
            for doc_id, path in self.id_to_path.items():
                c.execute("INSERT OR REPLACE INTO documents (id, path, added_date) VALUES (?, ?, ?)",
                         (doc_id, path, current_date))
            
            conn.commit()
            conn.close()
            print(f"Saved {len(self.id_to_path)} document mappings to database")
            
        except Exception as e:
            print(f"Error saving vector store: {e}")
            raise

    def load(self):
        """Load the FAISS index and document mappings"""
        try:
            index_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                    '..', 'modelrag', 'output', 'faiss.index')
            print(f"Looking for FAISS index at {index_path}")
            
            if os.path.exists(index_path):
                print(f"Loading FAISS index from {index_path}")
                self.index = faiss.read_index(index_path)
                print(f"FAISS index loaded with {self.index.ntotal} vectors")
                
                # Load document mappings
                self._load_existing_paths()
                print(f"Loaded {len(self.id_to_path)} document mappings from database")
            else:
                print("FAISS index not found. Starting with an empty index.")
                self.index = faiss.IndexFlatIP(self.dimension)
                self._init_db()  # Just initialize the database, don't reset it
                
        except Exception as e:
            print(f"Error loading vector store: {e}")
            raise
    def add_documents(self, paths: List[str], embeddings):
        """Add documents to the vector store"""
        if len(paths) == 0:
            return
                
        # Ensure embeddings is a numpy array with correct shape
        if not isinstance(embeddings, np.ndarray):
            embeddings = np.array(embeddings)
                
        if len(embeddings.shape) == 1:
            embeddings = embeddings.reshape(1, -1)
                
        # Verify embedding dimensions
        if embeddings.shape[1] != self.dimension:
            raise ValueError(f"Embedding dimension mismatch. Expected {self.dimension}, got {embeddings.shape[1]}")
                
        # Normalize vectors
        faiss.normalize_L2(embeddings)
        
        # Add to FAISS index
        self.index.add(embeddings)
        
        # Add to database and mapping
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        current_date = datetime.now().isoformat()
        
        for path in paths:
            self.current_id += 1
            try:
                # Get the correct filename from the path
                if isinstance(path, str):
                    # Handle different path formats
                    if '/' in path:
                        filename = path.split('/')[-1]
                    else:
                        filename = path.split('\\')[-1]
                    
                    # Remove any 'pdfs/' prefix
                    if filename.startswith('pdfs/'):
                        filename = filename.replace('pdfs/', '')
                    
                    print(f"Processing file: {filename}")  # Debug print
                    
                    # Verify file exists
                    full_path = os.path.join(settings.MEDIA_ROOT, 'pdfs', filename)
                    if not os.path.exists(full_path):
                        print(f"Warning: File not found at {full_path}")
                        continue
                    
                    c.execute("INSERT OR REPLACE INTO documents (id, path, added_date) VALUES (?, ?, ?)",
                            (self.current_id, filename, current_date))
                    self.id_to_path[self.current_id] = filename
                    print(f"Added document to database: {filename}")
                
            except sqlite3.IntegrityError:
                print(f"Document {filename} already exists in database")
            except Exception as e:
                print(f"Error processing document: {str(e)}")
        
        conn.commit()
        conn.close()
        
        # Save the updated index and mappings
        self.save()
        print(f"Current document mappings: {self.id_to_path}")  # Debug print

    def remove_document(self, path: str):
        """Remove a document from the vector store"""
        try:
            doc_id = None
            for id_, p in self.id_to_path.items():
                if p == path:
                    doc_id = id_
                    break

            if doc_id is None:
                logger.warning(f"Document {path} not found in vector store")
                return

            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            conn.commit()
            conn.close()

            del self.id_to_path[doc_id]
            self._rebuild_index()
            
        except Exception as e:
            logger.error(f"Error removing document {path}: {str(e)}")
    def search(self, query_vector: np.ndarray, query_text: str, k: int = 5, threshold: float = 0.5) -> List[Tuple[str, float, str]]:
        print("\n=== VECTOR STORE SEARCH STARTED ===")
        print(f"Searching for query: {query_text}")
        print(f"Number of vectors in index: {self.index.ntotal}")
        print(f"Document paths: {self.id_to_path}")
        
        try:
            # Normalize query vector
            faiss.normalize_L2(query_vector.reshape(1, -1))
            
            # Search in FAISS
            scores, indices = self.index.search(query_vector.reshape(1, -1), k * 2)
            print(f"FAISS returned {len(indices[0])} results")
            print(f"Indices: {indices[0]}")
            print(f"Scores: {scores[0]}")
            
            results = []
            query_terms = set(query_text.lower().split())
            
            for idx, score in zip(indices[0], scores[0]):
                if idx != -1 and score > -float('inf'):  # Check for valid scores
                    doc_id = idx + 1
                    filename = self.id_to_path.get(doc_id)
                    
                    if filename:
                        print(f"\nProcessing result for file: {filename}")
                        print(f"Document ID: {doc_id}")
                        semantic_similarity = (score + 1) / 2
                        print(f"Semantic similarity: {semantic_similarity}")
                        
                        try:
                            # Get the full path
                            full_path = os.path.join(settings.MEDIA_ROOT, 'pdfs', filename)
                            print(f"Looking for file at: {full_path}")
                            
                            if not os.path.exists(full_path):
                                # Try alternative path
                                full_path = os.path.join(settings.MEDIA_ROOT, filename)
                                print(f"Trying alternative path: {full_path}")
                                
                                if not os.path.exists(full_path):
                                    print(f"File not found at either location")
                                    continue
                            
                            print(f"Found file, extracting text...")
                            doc = fitz.open(full_path)
                            content = ""
                            for page in doc:
                                content += page.get_text().lower()
                            doc.close()
                            
                            word_matches = sum(1 for term in query_terms if term in content)
                            exact_match_score = word_matches / len(query_terms)
                            print(f"Word matches: {word_matches}")
                            print(f"Exact match score: {exact_match_score}")
                            
                            combined_score = (0.7 * semantic_similarity) + (0.3 * exact_match_score)
                            print(f"Combined score: {combined_score}")
                            
                            if combined_score >= threshold and word_matches > 0:
                                preview = self.get_content_preview(filename, query_vector, query_terms)
                                results.append((filename, float(combined_score), preview))
                                print("Added to results")
                                
                        except Exception as e:
                            print(f"Error processing document {filename}: {str(e)}")
                            continue
            
            print(f"\nReturning {len(results)} final results")
            return sorted(results, key=lambda x: x[1], reverse=True)[:k]
            
        except Exception as e:
            print(f"Error in vector store search: {str(e)}")
            return []
        finally:
            print("=== VECTOR STORE SEARCH COMPLETED ===\n")



    def get_content_preview(self, path: str, query_vector: np.ndarray, query_terms: set, preview_length: int = 200) -> str:
        """Get a preview of the document content"""
        try:
            file_name = os.path.basename(path)
            full_path = os.path.join(settings.MEDIA_ROOT, 'pdfs', file_name)
            
            if not os.path.exists(full_path):
                logger.error(f"File not found: {full_path}")
                return "Document not found"
                
            doc = fitz.open(full_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            
            sentences = text.replace('\n', ' ').split('.')
            best_sentence = ""
            best_score = -1
            
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) < 20:
                    continue
                
                sentence_lower = sentence.lower()
                matches = sum(1 for term in query_terms if term in sentence_lower)
                
                if matches > 0:
                    sentence_embedding = self.model.encode([sentence])[0]
                    faiss.normalize_L2(sentence_embedding.reshape(1, -1))
                    similarity = np.dot(query_vector, sentence_embedding)
                    combined_score = (0.7 * similarity) + (0.3 * (matches / len(query_terms)))
                    
                    if combined_score > best_score:
                        best_score = combined_score
                        best_sentence = sentence
            
            if not best_sentence:
                return "No relevant preview available"
            
            preview = best_sentence.strip()
            if len(preview) > preview_length:
                preview = preview[:preview_length] + "..."
            
            for term in query_terms:
                preview = preview.replace(term, f'**{term}**')
                
            return preview
            
        except Exception as e:
            logger.error(f"Error getting preview for {path}: {str(e)}")
            return ""
    def _rebuild_index(self):
        """Rebuild the FAISS index from remaining documents"""
        try:
            new_index = faiss.IndexFlatIP(self.dimension)
            
            for doc_id, path in self.id_to_path.items():
                full_path = os.path.join(settings.PDF_STORAGE, path)
                if os.path.exists(full_path):
                    text = extract_text_from_pdf(full_path)
                    if text:
                        embedding = self.model.encode([text])[0]
                        faiss.normalize_L2(embedding.reshape(1, -1))
                        new_index.add(embedding.reshape(1, -1))
            
            self.index = new_index
            
        except Exception as e:
            logger.error(f"Error rebuilding index: {str(e)}")

    def _get_full_path(self, file_path: str) -> str:
        """Convert relative path to full path"""
        file_name = os.path.basename(file_path.replace('pdfs/', ''))
        return os.path.join(settings.MEDIA_ROOT, 'pdfs', file_name)


def find_similar_documents(query: str, 
                         model: SentenceTransformer,
                         vector_store: 'VectorStore',
                         top_k: int = 5) -> List[Tuple[str, float]]:
    """Find similar documents using semantic search"""
    query_embedding = model.encode([query])[0]
    semantic_results = vector_store.search(query_embedding, query, k=top_k * 2)

    pdf_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'media', 'pdfs')
    query_terms = set(query.lower().split())
    final_results = []

    for path, semantic_score, _ in semantic_results:
        full_path = os.path.join(pdf_directory, path)
        text = extract_text_from_pdf(full_path)
        
        if text:
            text_lower = text.lower()
            term_matches = sum(1 for term in query_terms if term in text_lower)
            keyword_score = term_matches / len(query_terms) if query_terms else 0
            combined_score = (0.7 * semantic_score) + (0.3 * keyword_score)
            
            if keyword_score > 0:
                final_results.append((path, combined_score))

    final_results.sort(key=lambda x: x[1], reverse=True)
    return final_results[:top_k]


__all__ = ['VectorStore', 'find_similar_documents']
