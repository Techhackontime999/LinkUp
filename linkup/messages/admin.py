from django.contrib import admin
from .models import Message
from linkup.admin import admin_site


class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'recipient', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('sender__username', 'recipient__username', 'content')
    readonly_fields = ('created_at',)
    raw_id_fields = ('sender', 'recipient')
    list_per_page = 100


# Register with custom admin site
admin_site.register(Message, MessageAdmin)