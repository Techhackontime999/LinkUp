"""
Custom template tags for admin interface enhancements
"""
from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def thumbnail(image_field, width: int = 50, height: int = 50) -> str:
    """
    Render an image thumbnail
    
    Args:
        image_field: ImageField instance
        width: Thumbnail width in pixels
        height: Thumbnail height in pixels
        
    Returns:
        HTML img tag or placeholder text
    """
    try:
        if image_field and hasattr(image_field, 'url'):
            return format_html(
                '<img src="{}" width="{}" height="{}" style="border-radius: 4px; object-fit: cover;" />',
                image_field.url,
                width,
                height
            )
    except Exception:
        pass
    return "No image"


@register.simple_tag
def percentage_bar(value: int, max_value: int = 100) -> str:
    """
    Render a progress bar showing percentage
    
    Args:
        value: Current value
        max_value: Maximum value (default 100)
        
    Returns:
        HTML progress bar
    """
    try:
        # Convert to numeric values
        value = float(value) if value is not None else 0
        max_value = float(max_value) if max_value is not None else 100
        
        if max_value == 0:
            percentage = 0
        else:
            percentage = min(int((value / max_value) * 100), 100)
    except (ValueError, TypeError):
        percentage = 0
    
    # Color based on percentage
    if percentage >= 80:
        color = "#28a745"  # Green
    elif percentage >= 50:
        color = "#ffc107"  # Yellow
    else:
        color = "#dc3545"  # Red
    
    return format_html(
        '<div style="width: 100px; height: 20px; background-color: #e9ecef; '
        'border-radius: 4px; overflow: hidden; display: inline-block;">'
        '<div style="width: {}%; height: 100%; background-color: {}; '
        'display: flex; align-items: center; justify-content: center; '
        'color: white; font-size: 11px; font-weight: bold;">{}</div>'
        '</div>',
        percentage,
        color,
        f"{percentage}%"
    )


@register.filter
def truncate_text(text: str, length: int = 100) -> str:
    """
    Truncate text to specified length
    
    Args:
        text: Text to truncate
        length: Maximum length
        
    Returns:
        Truncated text with ellipsis
    """
    if not text:
        return ''
    
    if len(text) <= length:
        return text
    
    return text[:length] + '...'
