# Generated by Django 3.2.24 on 2025-01-26 18:57

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pdf_processor', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pdfdocument',
            name='file',
            field=models.FileField(upload_to='pdfs/', validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['pdf'])]),
        ),
    ]
