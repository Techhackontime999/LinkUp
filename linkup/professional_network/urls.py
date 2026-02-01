"""
URL configuration for professional_network project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core import health_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('users/', include('users.urls')),
    path('', include('feed.urls')),
    path('network/', include('network.urls')),
    path('jobs/', include('jobs.urls')),
    path('', include('core.urls')),  # Include core URLs at root level
    path('messages/', include('messaging.urls', namespace='messaging')),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path("__reload__/", include("django_browser_reload.urls")),
    
    # Health check endpoints
    path('health/', health_views.health_check, name='health_check'),
    path('health/db/', health_views.health_check_db, name='health_check_db'),
    path('health/redis/', health_views.health_check_redis, name='health_check_redis'),
    path('readiness/', health_views.readiness_check, name='readiness_check'),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
