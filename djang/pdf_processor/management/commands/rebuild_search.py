from django.core.management.base import BaseCommand
import os
from django.conf import settings
from pdf_processor.models import PDFDocument
from pdf_processor.vector_store import VectorStore
from sentence_transformers import SentenceTransformer

class Command(BaseCommand):
    help = 'Rebuild search index from existing documents'

    def handle(self, *args, **options):
        # Initialize
        self.stdout.write("Initializing...")
        model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
        vector_store = VectorStore(dimension=384)
        
        # Get all documents
        documents = PDFDocument.objects.all()
        self.stdout.write(f"Found {documents.count()} documents in database")
        
        # Process each document
        for doc in documents:
            try:
                # Get file path
                file_path = os.path.join(settings.MEDIA_ROOT, str(doc.file))
                if not os.path.exists(file_path):
                    self.stdout.write(self.style.WARNING(f"File not found: {file_path}"))
                    continue
                
                self.stdout.write(f"Processing: {doc.title}")
                
                # Extract text
                from pdf_processor.vector_store import extract_text_from_pdf
                text = extract_text_from_pdf(file_path)
                
                if not text:
                    self.stdout.write(self.style.WARNING(f"No text extracted from {doc.title}"))
                    continue
                
                # Generate embedding
                embedding = model.encode([text])[0]
                
                # Add to vector store
                vector_store.add_documents(
                    [str(doc.file)],
                    [embedding]
                )
                
                self.stdout.write(self.style.SUCCESS(f"Indexed: {doc.title}"))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing {doc.title}: {str(e)}"))
        
        # Save vector store
        vector_store.save()
        
        # Verify final state
        self.stdout.write("\nFinal state:")
        self.stdout.write(f"Documents in database: {documents.count()}")
        self.stdout.write(f"Vectors in index: {vector_store.index.ntotal}")
        self.stdout.write(f"Document mappings: {vector_store.id_to_path}")
