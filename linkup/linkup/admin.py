"""
Custom AdminSite configuration for LinkUp Administration
"""
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.http import HttpRequest
from django.template.response import TemplateResponse
from typing import List, Dict
from .admin_dashboard import DashboardStats


class LinkUpAdminSite(AdminSite):
    """Custom admin site with LinkUp branding and enhanced functionality"""
    
    site_header = "LinkUp Administration"
    site_title = "LinkUp Admin Portal"
    index_title = "Welcome to LinkUp Administration"
    
    def index(self, request, extra_context=None):
        """
        Custom dashboard view with statistics
        
        Args:
            request: HttpRequest object
            extra_context: Additional context dict
            
        Returns:
            TemplateResponse with dashboard data
        """
        # Get statistics
        user_stats = DashboardStats.get_user_stats()
        content_stats = DashboardStats.get_content_stats()
        job_stats = DashboardStats.get_job_stats()
        network_stats = DashboardStats.get_network_stats()
        recent_actions = DashboardStats.get_recent_actions(limit=10)
        chart_data = DashboardStats.get_chart_data()
        
        # Prepare context
        context = {
            **self.each_context(request),
            'title': self.index_title,
            'user_stats': user_stats,
            'content_stats': content_stats,
            'job_stats': job_stats,
            'network_stats': network_stats,
            'recent_actions': recent_actions,
            'chart_data': chart_data,
        }
        
        if extra_context:
            context.update(extra_context)
        
        request.current_app = self.name
        
        return TemplateResponse(request, 'admin/index.html', context)
    
    def get_app_list(self, request: HttpRequest) -> List[Dict]:
        """
        Return a sorted list of all the installed apps that have been
        registered in this site, organized in logical order.
        """
        app_list = super().get_app_list(request)
        
        # Define custom ordering for apps
        app_order = {
            'users': 1,
            'feed': 2,
            'jobs': 3,
            'network': 4,
            'messaging': 5,
            'auth': 6,
            'contenttypes': 7,
            'sessions': 8,
            'admin': 9,
        }
        
        # Sort apps based on custom order
        app_list.sort(key=lambda x: app_order.get(x['app_label'], 999))
        
        return app_list


# Create custom admin site instance
admin_site = LinkUpAdminSite(name='linkup_admin')
