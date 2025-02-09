from django.urls import path
from . import views

app_name = 'pdf_processor_api'

urlpatterns = [
    path('search/', views.search_page, name='search'),
    path('upload/', views.upload_document, name='upload_document'),
    path('document/<int:document_id>/content/', views.get_document_content, name='get_document_content'),
    path('document/<int:document_id>/answer/', views.answer_question, name='answer_question'),
]
