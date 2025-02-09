from django.core.management.base import BaseCommand
from pdf_processor.models import PDFDocument
from pdf_processor.vector_store import VectorStore
from sentence_transformers import SentenceTransformer
import os
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Rebuild FAISS index and clean up orphaned vectors'

    def handle(self, *args, **options):
        self.stdout.write("Starting index rebuild...")
        
        # Initialize new vector store
        vector_store = VectorStore(dimension=384)
        model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
        
        # Get all PDF documents from database
        documents = PDFDocument.objects.all()
        self.stdout.write(f"Found {documents.count()} documents in database")
        
        # Clear existing index
        vector_store = VectorStore(dimension=384)
        vector_store._init_db()  # Reset the database
        
        # Process each document
        successful = 0
        failed = 0
        
        for doc in documents:
            try:
                if not doc.file:
                    self.stdout.write(self.style.WARNING(f"Skipping {doc.title}: No file"))
                    continue
                    
                file_path = os.path.join(settings.MEDIA_ROOT, str(doc.file))
                if not os.path.exists(file_path):
                    self.stdout.write(self.style.WARNING(f"Skipping {doc.title}: File not found at {file_path}"))
                    continue
                
                # Extract text
                from pdf_processor.vector_store import extract_text_from_pdf
                text = extract_text_from_pdf(file_path)
                
                if not text:
                    self.stdout.write(self.style.WARNING(f"Skipping {doc.title}: No text extracted"))
                    continue
                
                # Generate embedding
                embedding = model.encode([text])[0]
                
                # Add to vector store
                vector_store.add_documents([str(doc.file)], [embedding])
                
                # Update document status
                doc.is_indexed = True
                doc.save(update_fields=['is_indexed'])
                
                successful += 1
                self.stdout.write(self.style.SUCCESS(f"Indexed: {doc.title}"))
                
            except Exception as e:
                failed += 1
                self.stdout.write(self.style.ERROR(f"Error processing {doc.title}: {str(e)}"))
        
        # Save the new index
        vector_store.save()
        
        self.stdout.write(self.style.SUCCESS(
            f"\nIndex rebuild complete:\n"
            f"- Successfully indexed: {successful}\n"
            f"- Failed: {failed}\n"
            f"- Total vectors in index: {vector_store.index.ntotal}\n"
            f"- Total documents mapped: {len(vector_store.id_to_path)}"
        ))
