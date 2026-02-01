from django.urls import path
from . import views

urlpatterns = [
    path('', views.network_view, name='network'),
    path('send/<int:user_id>/', views.send_request, name='send_request'),
    path('accept/<int:request_id>/', views.accept_request, name='accept_request'),
    path('reject/<int:request_id>/', views.reject_request, name='reject_request'),
    path('follow/<int:user_id>/', views.follow_user, name='follow_user'),
    path('connect-toggle/<int:user_id>/', views.toggle_connection, name='toggle_connection'),
]
