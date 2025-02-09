import os
import logging
from django.core.management.base import BaseCommand
from sentence_transformers import SentenceTransformer
import fitz  # PyMuPDF
from django.conf import settings
from pdf_processor.vector_store import VectorStore

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Generate or update FAISS index from PDF documents'

    def handle(self, *args, **options):
        # Check PDF directory
        self.stdout.write(f"Looking for PDFs in: {settings.PDF_STORAGE}")
        if os.path.exists(settings.PDF_STORAGE):
            pdf_files = [f for f in os.listdir(settings.PDF_STORAGE) if f.endswith('.pdf')]
            self.stdout.write(f"Found {len(pdf_files)} PDF files: {pdf_files}")
        else:
            self.stdout.write(self.style.ERROR(f"PDF directory does not exist: {settings.PDF_STORAGE}"))
            return

        # Initialize model
        model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
        model.max_seq_length = 256
        
        # Initialize VectorStore
        vector_store = VectorStore(dimension=384)
        
        try:
            # Try to load existing index
            vector_store.load()
            self.stdout.write(self.style.SUCCESS('Loaded existing vector store'))
            
            # Get list of already processed files
            existing_files = set(vector_store.id_to_path.values())
            self.stdout.write(f"Found {len(existing_files)} already processed files")
            
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Could not load vector store: {str(e)}'))
            self.stdout.write('Creating new vector store')
            existing_files = set()

        # Process each PDF
        pdf_dir = settings.PDF_STORAGE
        processed_count = 0
        skipped_count = 0
        
        for filename in pdf_files:
            if filename in existing_files:
                self.stdout.write(f'Skipping already processed file: {filename}')
                skipped_count += 1
                continue
                
            pdf_path = os.path.join(pdf_dir, filename)
            try:
                # Extract text
                text = self.extract_text_from_pdf(pdf_path)
                if not text:
                    self.stdout.write(self.style.WARNING(f'No text extracted from {filename}'))
                    continue
                    
                # Generate embedding
                embedding = model.encode([text])
                
                # Add to vector store
                vector_store.add_documents([filename], embedding)
                
                processed_count += 1
                self.stdout.write(self.style.SUCCESS(f'Processed {filename}'))
                
            except Exception as e:
                logger.error(f'Error processing {filename}: {str(e)}')
                self.stdout.write(self.style.ERROR(f'Error processing {filename}: {str(e)}'))
                continue

        # Save updated vector store
        if processed_count > 0:
            vector_store.save()
            self.stdout.write(self.style.SUCCESS(
                f'Successfully processed {processed_count} new documents\n'
                f'Skipped {skipped_count} already processed documents\n'
                f'Vector store updated with {vector_store.index.ntotal} total embeddings'
            ))
        else:
            if skipped_count > 0:
                self.stdout.write(self.style.SUCCESS(
                    f'No new documents to process\n'
                    f'Skipped {skipped_count} already processed documents\n'
                    f'Vector store contains {vector_store.index.ntotal} total embeddings'
                ))
            else:
                self.stdout.write(self.style.WARNING('No valid PDFs processed'))

    def extract_text_from_pdf(self, pdf_path):
        """Extract text from a PDF file using PyMuPDF"""
        try:
            doc = fitz.open(pdf_path)
            text = ''
            for page in doc:
                text += page.get_text()
            return text
        except Exception as e:
            logger.error(f'Error extracting text from {pdf_path}: {str(e)}')
            return None
