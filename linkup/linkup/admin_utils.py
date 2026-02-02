"""
Utility functions and mixins for Django admin customization
"""
import csv
from django.http import HttpResponse
from django.utils.html import strip_tags, format_html
from django.utils.text import Truncator


class ExportCSVMixin:
    """Mixin to add CSV export functionality to ModelAdmin classes"""
    
    def export_as_csv(self, request, queryset):
        """
        Export selected objects as CSV file
        
        Args:
            request: HttpRequest object
            queryset: QuerySet of selected objects
            
        Returns:
            HttpResponse with CSV file
        """
        meta = self.model._meta
        field_names = [field.name for field in meta.fields]
        
        # Use list_display if available, otherwise use all fields
        if hasattr(self, 'list_display') and self.list_display:
            # Filter out callables and use actual field names
            export_fields = []
            for field in self.list_display:
                if isinstance(field, str) and field in field_names:
                    export_fields.append(field)
            if not export_fields:
                export_fields = field_names
        else:
            export_fields = field_names
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename={meta.verbose_name_plural}.csv'
        
        writer = csv.writer(response)
        writer.writerow(export_fields)
        
        for obj in queryset:
            row = []
            for field in export_fields:
                value = getattr(obj, field)
                # Handle special cases
                if value is None:
                    row.append('')
                elif hasattr(value, 'all'):  # ManyToMany field
                    row.append(', '.join(str(item) for item in value.all()))
                else:
                    row.append(str(value))
            writer.writerow(row)
        
        return response
    
    export_as_csv.short_description = "Export selected as CSV"


def truncate_html(html_content: str, length: int = 100) -> str:
    """
    Truncate HTML content while stripping tags
    
    Args:
        html_content: HTML string to truncate
        length: Maximum length of truncated text
        
    Returns:
        Truncated plain text with ellipsis if needed
    """
    if not html_content:
        return ''
    
    # Strip HTML tags
    text = strip_tags(html_content)
    
    # Truncate to specified length
    return Truncator(text).chars(length)


def status_badge(value: bool, true_label: str = "Active", false_label: str = "Inactive") -> str:
    """
    Generate HTML badge for boolean status fields
    
    Args:
        value: Boolean value to display
        true_label: Label to show when value is True
        false_label: Label to show when value is False
        
    Returns:
        HTML string with colored badge
    """
    if value:
        color = "#28a745"  # Green
        label = true_label
    else:
        color = "#dc3545"  # Red
        label = false_label
    
    return format_html(
        '<span style="background-color: {}; color: white; padding: 3px 10px; '
        'border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
        color,
        label
    )
