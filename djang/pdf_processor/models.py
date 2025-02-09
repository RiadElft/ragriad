import os
import time
import pickle
from django.db import models
from .vector_store import VectorStore
from django.contrib.auth.models import User, Group
from django.core.files.storage import FileSystemStorage
from django.core.validators import FileExtensionValidator
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from .services import search_service
import logging
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

pdf_storage = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'pdfs/'))

class DocumentPermission(models.Model):
    # No changes needed in DocumentPermission
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    document = models.ForeignKey('PDFDocument', on_delete=models.CASCADE)
    can_view = models.BooleanField(default=True)
    can_edit = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'document')
        verbose_name = 'Document Permission'
        verbose_name_plural = 'Document Permissions'

    def __str__(self):
        return f"{self.user.username} - {self.document.title}"

class PDFDocument(models.Model):
    # Existing fields remain the same
    title = models.CharField(max_length=255)
    file = models.FileField(
        upload_to='pdfs/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])]
    )
    content = models.TextField(blank=True)
    embeddings = models.BinaryField(null=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_documents')
    groups = models.ManyToManyField(Group, blank=True, related_name='accessible_documents')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_indexed = models.BooleanField(default=False)
    permissions = models.ManyToManyField(
        User,
        through=DocumentPermission,
        through_fields=('document', 'user'),
        related_name='document_permissions'
    )

    def __str__(self):
        return self.title

    def get_embeddings(self):
        return pickle.loads(self.embeddings) if self.embeddings else None

    def set_embeddings(self, embeddings_array):
        self.embeddings = pickle.dumps(embeddings_array)
    def save(self, *args, **kwargs):
        """Save the document and handle indexing"""
        is_new = self._state.adding
        file_changed = False

        # NEW DEBUG PRINTS
        print("\n=== SAVE METHOD STARTED ===")
        print(f"Saving document: {self.title}")
        print(f"Is new document: {is_new}")
        print(f"Has file: {bool(self.file)}")
        print(f"File path: {self.file.path if self.file else 'No file'}")
        print(f"Is indexed: {self.is_indexed}")
        print(f"Update fields: {kwargs.get('update_fields')}")

        if not is_new and 'file' in kwargs.get('update_fields', []):
            try:
                old_instance = PDFDocument.objects.get(pk=self.pk)
                file_changed = old_instance.file != self.file
                print(f"File changed: {file_changed}")  # Debug print
            except PDFDocument.DoesNotExist:
                file_changed = True
                print("Old instance not found")  # Debug print

        if is_new or file_changed:
            self.is_indexed = False
            print("Setting is_indexed to False")  # Debug print

        try:
            super().save(*args, **kwargs)
            print("Base save completed")  # Debug print

            # Index if needed
            if not self.is_indexed and self.file:
                print("Starting indexing process...")  # Debug print
                self.process_and_index()
                print("Indexing completed")  # Debug print
            else:
                print(f"Skipping indexing - is_indexed: {self.is_indexed}, has_file: {bool(self.file)}")

        except Exception as e:
            print(f"Error in save method: {str(e)}")  # Debug print
            logger.error(f"Error saving document {self.title}: {str(e)}")
            if is_new and self.pk:
                self.delete()
            raise
        finally:
            print("=== SAVE METHOD COMPLETED ===\n")

    def process_and_index(self):
        """Process the PDF file and generate embeddings"""
        from .vector_store import extract_text_from_pdf
        
        print("\n=== INDEXING PROCESS STARTED ===")
        print(f"Processing document: {self.title}")
        print(f"File path: {self.file.path}")
        
        try:
            # Extract text
            text = extract_text_from_pdf(self.file.path)
            if not text:
                raise ValueError("Failed to extract text from PDF")

            print(f"Extracted {len(text)} characters")

            # Generate embeddings
            embeddings = search_service.model.encode(text, show_progress_bar=True, batch_size=32)
            print(f"Generated embeddings with shape: {embeddings.shape}")
            
            # Save to document
            self.set_embeddings(embeddings)
            self.content = text
            self.is_indexed = True
            self.save(update_fields=['embeddings', 'content', 'is_indexed'])

            # Add to search index
            # Get the actual filename
            filename = os.path.basename(self.file.name)
            print(f"Adding file to index: {filename}")
            
            search_service.add_to_index(
                title=filename,  # Use filename instead of title
                embeddings=embeddings,
                text=text,
                document_id=self.id,
                owner_id=self.owner.id,
                group_ids=[g.id for g in self.groups.all()],
                permission_ids=[p.user.id for p in self.documentpermission_set.all()]
            )
            
            print("Added to vector store successfully")
            return True

        except Exception as e:
            print(f"Error in indexing process: {str(e)}")
            self.is_indexed = False
            self.save(update_fields=['is_indexed'])
            raise
        finally:
            print("=== INDEXING PROCESS COMPLETED ===\n")

    def user_has_access(self, user):
        """Check if user has access to this document"""
        return (self.owner == user or 
                user in [group.user for group in self.groups.all()] or
                self.permissions.filter(user=user).exists())

    def get_user_permissions(self, user):
        """Get specific permissions for a user"""
        try:
            return self.documentpermission_set.get(user=user)
        except DocumentPermission.DoesNotExist:
            return None

    def delete(self, *args, **kwargs):
        """Override delete to remove from vector store"""
        try:
            # Remove from vector store
            vector_store = VectorStore(dimension=384)
            vector_store.load()
            vector_store.remove_document(str(self.file))
            vector_store.save()
            logger.info(f"Removed document from vector store: {self.title}")
        except Exception as e:
            logger.error(f"Error removing document from vector store: {str(e)}")
        
        super().delete(*args, **kwargs)

# MODIFIED: Fixed signal handler
@receiver(post_save, sender=PDFDocument)
def index_document(sender, instance, created, **kwargs):
    """Signal handler to ensure document is indexed after save"""
    # NEW DEBUG
    print(f"Signal handler triggered - created: {created}, is_indexed: {instance.is_indexed}")
    
    if created and not instance.is_indexed:
        try:
            # NEW DEBUG
            print(f"Attempting to index document {instance.title} from signal handler")
            instance.process_and_index()
        except Exception as e:
            # NEW DEBUG
            print(f"Error in signal handler: {str(e)}")
            logger.error(f"Error in post-save indexing: {str(e)}")