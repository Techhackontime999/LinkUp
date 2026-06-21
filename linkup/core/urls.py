from django.urls import path
from . import views

urlpatterns = [
    path('search/', views.search, name='search'),
    path('search/suggestions/', views.search_suggestions, name='search_suggestions'),
    path('csrf-token-refresh/', views.csrf_token_refresh, name='csrf_token_refresh'),
    path('sw.js', views.service_worker, name='service_worker'),
    path('offline/', views.offline_page, name='offline_page'),
]
