from django.core.management.base import BaseCommand
from sentence_transformers import SentenceTransformer
from ...vector_store import VectorStore, find_similar_documents

class Command(BaseCommand):
    help = 'Test the search functionality'

    def handle(self, *args, **options):
        model = SentenceTransformer('all-MiniLM-L6-v2')
        vector_store = VectorStore()
        vector_store.load()
        
        # Test queries
        queries = [
            "test query",
            "document",
            "PDF processing",
            "search functionality"
        ]
        
        for query in queries:
            self.stdout.write(f"\nTesting query: '{query}'")
            results = find_similar_documents(query, model, vector_store)
            if results:
                self.stdout.write(f"Found {len(results)} results:")
                for path, score in results:
                    self.stdout.write(f"- {path} (score: {score:.2f})")
            else:
                self.stdout.write("No results found")
