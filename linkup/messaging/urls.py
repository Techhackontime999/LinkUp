from django.urls import path
from . import views

app_name = 'messaging'

urlpatterns = [
    path('', views.messages_inbox, name='inbox'),
    path('chat/<str:username>/', views.chat_view, name='chat_view'),
    path('history/<str:username>/', views.fetch_history, name='fetch_history'),
    path('load-older/<str:username>/', views.load_older_messages, name='load_older_messages'),
    path('sync/<str:username>/', views.synchronize_conversation, name='synchronize_conversation'),
    path('send/<str:username>/', views.send_message_fallback, name='send_message_fallback'),
    path('queue/<str:username>/', views.queue_message, name='queue_message'),
    path('unread/', views.unread_notifications, name='unread_notifications'),
    path('status/<str:username>/', views.user_status, name='user_status'),
    path('mark-read/<str:username>/', views.mark_messages_read, name='mark_messages_read'),
    
    # Notification management endpoints
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('notifications/preferences/', views.notification_preferences, name='notification_preferences'),
    path('notifications/preferences/page/', views.notification_preferences_page, name='notification_preferences_page'),
    path('notifications/preferences/update/', views.update_notification_preferences, name='update_notification_preferences'),
    path('notifications/dashboard/', views.notification_dashboard, name='notification_dashboard'),
]
