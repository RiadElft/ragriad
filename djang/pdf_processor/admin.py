from django.contrib import admin
from .models import PDFDocument, DocumentPermission
from django.utils.html import format_html

class DocumentPermissionInline(admin.TabularInline):
    model = DocumentPermission
    extra = 1
    fields = ('user', 'can_view', 'can_edit', 'can_delete')
    autocomplete_fields = ['user']

class PDFDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'created_at', 'updated_at', 'indexing_status', 'file_link')
    search_fields = ('title', 'content')
    list_filter = ('owner', 'groups', 'created_at', 'is_indexed')
    filter_horizontal = ('groups',)
    readonly_fields = ('embeddings', 'content', 'is_indexed', 'indexing_status')
    fieldsets = (
        (None, {
            'fields': ('title', 'file')
        }),
        ('Permissions', {
            'fields': ('owner', 'groups')
        }),
        ('Indexing Status', {
            'fields': ('is_indexed', 'indexing_status'),
        }),
        ('Advanced', {
            'fields': ('embeddings', 'content'),
            'classes': ('collapse',)
        })
    )
    inlines = [DocumentPermissionInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(owner=request.user)

    def get_inline_instances(self, request, obj=None):
        """Only show permissions inline for existing documents"""
        if obj:
            return super().get_inline_instances(request, obj)
        return []

    def indexing_status(self, obj):
        """Display indexing status with color coding"""
        if obj.is_indexed:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Indexed</span>'
            )
        return format_html(
            '<span style="color: red; font-weight: bold;">✗ Not Indexed</span>'
        )
    indexing_status.short_description = 'Indexing Status'

    def file_link(self, obj):
        """Display clickable link to the PDF file"""
        if obj.file:
            return format_html(
                '<a href="{}" target="_blank">{}</a>',
                obj.file.url,
                obj.file.name
            )
        return '-'
    file_link.short_description = 'File'

    def save_model(self, request, obj, form, change):
        if not obj.owner:
            obj.owner = request.user
        
        try:
            super().save_model(request, obj, form, change)
            self.message_user(
                request, 
                f'Document "{obj.title}" successfully saved and indexed.'
            )
        except Exception as e:
            self.message_user(
                request,
                f'Error saving document: {str(e)}',
                level='ERROR'
            )

class DocumentPermissionAdmin(admin.ModelAdmin):
    list_display = ('document', 'user', 'can_view', 'can_edit', 'can_delete')
    list_filter = ('document', 'user')
    search_fields = ('document__title', 'user__username')
    raw_id_fields = ('document',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(document__owner=request.user)

admin.site.register(PDFDocument, PDFDocumentAdmin)
admin.site.register(DocumentPermission, DocumentPermissionAdmin)
