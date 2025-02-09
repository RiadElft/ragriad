from django.core.management.base import BaseCommand
import os
import shutil
import sqlite3
from django.conf import settings
from pdf_processor.models import PDFDocument
from pdf_processor.vector_store import VectorStore, extract_text_from_pdf
from sentence_transformers import SentenceTransformer

class Command(BaseCommand):
    help = 'Complete rebuild of search index and database'

    def clean_vector_store_db(self, db_path):
        """Clean the vector store database"""
        try:
            if os.path.exists(db_path):
                os.remove(db_path)
                self.stdout.write(f"Removed existing database: {db_path}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error cleaning database: {e}"))

    def handle(self, *args, **options):
        try:
            # 1. Clear everything
            self.stdout.write("=== Starting Complete Rebuild ===")
            
            # Clear vector store directory
            output_dir = os.path.join(settings.BASE_DIR, 'modelrag', 'output')
            if os.path.exists(output_dir):
                shutil.rmtree(output_dir)
                self.stdout.write("Cleared output directory")
            os.makedirs(output_dir, exist_ok=True)

            # Clear the vector store database
            db_path = 'djang/modelrag/output/vector_store.db'
            self.clean_vector_store_db(db_path)

            # 2. Initialize fresh vector store
            self.stdout.write("\nInitializing new vector store...")
            vector_store = VectorStore(dimension=384)
            
            # Initialize model
            self.stdout.write("Initializing model...")
            model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')

            # 3. Get all documents
            documents = PDFDocument.objects.all()
            self.stdout.write(f"\nFound {documents.count()} documents to process")

            # 4. Process each document
            processed_count = 0
            
            for doc in documents:
                try:
                    self.stdout.write(f"\nProcessing document {processed_count + 1}/{documents.count()}")
                    self.stdout.write(f"Title: {doc.title}")
                    self.stdout.write(f"File: {doc.file.name}")
                    
                    # Verify file exists
                    if not doc.file:
                        self.stdout.write(self.style.WARNING("No file attached"))
                        continue
                        
                    file_path = doc.file.path
                    if not os.path.exists(file_path):
                        self.stdout.write(self.style.WARNING(f"File not found: {file_path}"))
                        continue

                    # Extract text
                    text = extract_text_from_pdf(file_path)
                    if not text:
                        self.stdout.write(self.style.WARNING("No text extracted"))
                        continue
                    
                    self.stdout.write(f"Extracted {len(text)} characters")

                    # Generate embedding
                    embedding = model.encode([text])[0]
                    self.stdout.write("Generated embedding")

                    # Add to vector store
                    filename = os.path.basename(file_path)
                    vector_store.add_documents([filename], [embedding])
                    processed_count += 1
                    self.stdout.write(self.style.SUCCESS(f"Added to vector store: {filename}"))

                    # Update document
                    doc.content = text
                    doc.is_indexed = True
                    doc.save(update_fields=['content', 'is_indexed'])

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error processing document: {str(e)}"))

            # 5. Save vector store
            vector_store.save()

            # 6. Verify final state
            self.stdout.write("\n=== Final State ===")
            self.stdout.write(f"Documents in database: {documents.count()}")
            self.stdout.write(f"Documents processed: {processed_count}")
            self.stdout.write(f"Vectors in index: {vector_store.index.ntotal}")
            self.stdout.write(f"Document mappings: {vector_store.id_to_path}")

            # 7. Verify each document
            self.stdout.write("\n=== Document Verification ===")
            for doc in documents:
                self.stdout.write(f"Document: {doc.title}")
                self.stdout.write(f"- File: {doc.file.name}")
                self.stdout.write(f"- Indexed: {doc.is_indexed}")
                self.stdout.write(f"- Has content: {bool(doc.content)}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error during rebuild: {str(e)}"))
