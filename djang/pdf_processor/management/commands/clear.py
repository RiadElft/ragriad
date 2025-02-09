from django.core.management.base import BaseCommand
import os
from pdf_processor.vector_store import VectorStore
import sqlite3
import shutil

class Command(BaseCommand):
    help = 'Clear all FAISS indexes and document mappings'

    def handle(self, *args, **options):
        try:
            # Initialize VectorStore to get paths
            vector_store = VectorStore(dimension=384)
            
            # Clear FAISS index file
            faiss_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                    'modelrag', 'output', 'faiss.index')
            if os.path.exists(faiss_path):
                os.remove(faiss_path)
                self.stdout.write(self.style.SUCCESS(f"Deleted FAISS index: {faiss_path}"))
            
            # Clear SQLite database
            if os.path.exists(vector_store.db_path):
                os.remove(vector_store.db_path)
                self.stdout.write(self.style.SUCCESS(f"Deleted database: {vector_store.db_path}"))
            
            # Clear the output directory
            output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                    'modelrag', 'output')
            if os.path.exists(output_dir):
                shutil.rmtree(output_dir)
                os.makedirs(output_dir)
                self.stdout.write(self.style.SUCCESS(f"Cleared output directory: {output_dir}"))
            
            self.stdout.write(self.style.SUCCESS("Successfully cleared all indexes"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error clearing indexes: {str(e)}"))
