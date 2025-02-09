from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.conf import settings
import os
import json
import logging
from .models import PDFDocument
from .services.search_service import SearchService
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from sentence_transformers import SentenceTransformer
from .vector_store import VectorStore, find_similar_documents

# Initialize logger first
logger = logging.getLogger(__name__)

# Initialize model and vector store
model = SentenceTransformer('all-MiniLM-L6-v2')
vector_store = VectorStore(dimension=384)
try:
    vector_store.load()
    logger.info("Loaded existing vector store")
except Exception as e:
    logger.warning(f"Could not load vector store: {str(e)}")

search_service = SearchService()

@login_required
def search_page(request):
    query = request.GET.get('q', '')
    results = []
    
    print("\n=== SEARCH STARTED ===")
    print(f"Search query: {query}")
    
    if query:
        try:
            # Check current state
            print("\nChecking current state:")
            from pdf_processor.models import PDFDocument
            docs = PDFDocument.objects.all()
            print(f"Documents in database: {docs.count()}")
            for doc in docs:
                print(f"- {doc.title}: {doc.file.name} (indexed: {doc.is_indexed})")
            
            # Perform search
            print("\nPerforming search...")
            results = search_service.search(query)
            print(f"Search returned {len(results)} results")
            print(f"Raw results: {results}")
            
        except Exception as e:
            print(f"Search error: {str(e)}")
            logger.error(f"Search error: {str(e)}")
    else:
        print("No query provided")
    
    print("=== SEARCH COMPLETED ===\n")
    
    return render(request, 'pdf_app/search.html', {
        'query': query,
        'results': results
    })
@login_required
def search_page(request):
    query = request.GET.get('q', '')
    results = []
    
    # NEW DEBUG PRINTS
    print("\n=== SEARCH STARTED ===")
    print(f"Search query: {query}")
    
    if query:
        try:
            # Check vector store state
            print("\nChecking vector store state:")
            vector_store = VectorStore(dimension=384)
            vector_store.load()
            print(f"Vectors in index: {vector_store.index.ntotal}")
            print(f"Document paths: {vector_store.id_to_path}")
            
            # Perform search
            print("\nPerforming search...")
            results = search_service.search(query)
            print(f"Search returned {len(results)} results")
            print(f"Raw results: {results}")
            
        except Exception as e:
            print(f"Search error: {str(e)}")
            logger.error(f"Search error: {str(e)}")
    else:
        print("No query provided")
    
    print("=== SEARCH COMPLETED ===\n")
    
    return render(request, 'pdf_app/search.html', {
        'query': query,
        'results': results
    })

@login_required
def upload_document(request):
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        file_path = os.path.join(settings.PDF_STORAGE, file.name)
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        file_path = default_storage.save(file_path, file)
        
        # Create Document record
        doc = PDFDocument.objects.create(
            title=file.name,
            file=file_path,
            owner=request.user
        )
        
        return JsonResponse({
            'status': 'success',
            'document_id': doc.id
        })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def get_document_content(request, document_id):
    try:
        content = search_service.get_document_content(document_id, request.user)
        if content:
            logger.info(f'Successfully retrieved content for document {document_id}')
            return JsonResponse({'content': content})
        logger.warning(f'Document not found or access denied: {document_id}')
        return JsonResponse({'error': 'Document not found or access denied'}, status=404)
    except Exception as e:
        logger.error(f'Document content error: {str(e)}', exc_info=True)
        return JsonResponse({'error': 'Internal server error'}, status=500)

@csrf_exempt
@login_required
@require_http_methods(["POST"])
def answer_question(request, document_id):
    try:
        data = json.loads(request.body)
        question = data.get('question')
        
        if not question:
            logger.warning('Answer question called without question')
            return JsonResponse({'error': 'Question is required'}, status=400)
        
        # Get answer
        result = search_service.answer_question(document_id, question, request.user)
        if not result:
            logger.warning(f'Document not found or access denied: {document_id}')
            return JsonResponse({'error': 'Document not found or access denied'}, status=404)
            
        logger.info(f'Successfully answered question for document {document_id}')
        return JsonResponse(result)
    except Exception as e:
        logger.error(f'Answer question error: {str(e)}', exc_info=True)
        return JsonResponse({'error': 'Internal server error'}, status=500)

def login_view(request):
    return render(request, 'registration/login.html')

def logout_view(request):
    return redirect('login')

class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'pdf_processor/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        return context
