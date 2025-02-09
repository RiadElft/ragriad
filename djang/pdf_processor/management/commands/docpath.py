from django.core.management.base import BaseCommand
from pdf_processor.vector_store import VectorStore
import os
from django.conf import settings

class Command(BaseCommand):
    help = 'Rebuild the document paths database'

    def handle(self, *args, **options):
        vector_store = VectorStore(dimension=384)
        
        # Get list of PDF files
        pdf_dir = settings.PDF_STORAGE
        pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith('.pdf')]
        
        self.stdout.write(f"Found {len(pdf_files)} PDF files")
        
        # Clear existing database
        vector_store._init_db()
        
        # Add documents to database
        for pdf_file in pdf_files:
            vector_store.current_id += 1
            vector_store.id_to_path[vector_store.current_id] = pdf_file
            
        self.stdout.write(self.style.SUCCESS(f"Rebuilt database with {len(pdf_files)} documents"))
