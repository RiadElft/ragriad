from django.core.management.base import BaseCommand
import os
import shutil
from django.conf import settings

class Command(BaseCommand):
    help = 'Reset search index and database'

    def handle(self, *args, **options):
        # Clear vector store
        output_dir = os.path.join(settings.BASE_DIR, 'modelrag', 'output')
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
            os.makedirs(output_dir)
            self.stdout.write(self.style.SUCCESS(f"Cleared {output_dir}"))

        # Clear database entries
        from pdf_processor.models import PDFDocument
        PDFDocument.objects.all().delete()
        self.stdout.write(self.style.SUCCESS("Cleared database entries"))
