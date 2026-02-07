from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import View
from django.contrib.auth import get_user_model
from django.db import transaction
from django.core.management import call_command
from django.core.management.base import OutputWrapper
import io
import sys

User = get_user_model()

@method_decorator(staff_member_required, name='dispatch')
class SeedTestDataView(View):
    template_name = 'admin/seed_test_data.html'
    
    def get(self, request):
        # Get default values from query params
        context = {
            'title': 'Seed Test Data',
            'users': request.GET.get('users', 50),
            'posts': request.GET.get('posts', 200),
            'jobs': request.GET.get('jobs', 20),
            'opts': User._meta,
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        users = int(request.POST.get('users', 50))
        posts = int(request.POST.get('posts', 200))
        jobs = int(request.POST.get('jobs', 20))
        clean = request.POST.get('clean', False)
        
        try:
            with transaction.atomic():
                # Capture command output
                out = io.StringIO()
                call_command(
                    'seed_test_data',
                    users=users,
                    posts=posts,
                    jobs=jobs,
                    clean=clean,
                    stdout=out,
                    stderr=out
                )
                
                output = out.getvalue()
                
                messages.success(
                    request, 
                    f'Successfully seeded test data: {users} users, {posts} posts, {jobs} jobs'
                )
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': f'Successfully seeded test data',
                        'output': output
                    })
                
                return redirect('admin:index')
                
        except Exception as e:
            error_message = f'Error seeding test data: {str(e)}'
            messages.error(request, error_message)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': error_message
                })
            
            return redirect('admin:seed_test_data')

@method_decorator(staff_member_required, name='dispatch')
class ClearTestDataView(View):
    template_name = 'admin/clear_test_data.html'
    
    def get(self, request):
        context = {
            'title': 'Clear Test Data',
            'opts': User._meta,
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        confirm = request.POST.get('confirm', False)
        
        if not confirm:
            messages.error(request, 'Please confirm the action to clear test data')
            return redirect('admin:clear_test_data')
        
        try:
            with transaction.atomic():
                # Capture command output
                out = io.StringIO()
                call_command(
                    'drop_test_data',
                    confirm=True,
                    stdout=out,
                    stderr=out
                )
                
                output = out.getvalue()
                
                messages.success(request, 'Successfully cleared all test data')
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': 'Successfully cleared all test data',
                        'output': output
                    })
                
                return redirect('admin:index')
                
        except Exception as e:
            error_message = f'Error clearing test data: {str(e)}'
            messages.error(request, error_message)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': error_message
                })
            
            return redirect('admin:clear_test_data')

@method_decorator(staff_member_required, name='dispatch')
class TestDataStatsView(View):
    def get(self, request):
        try:
            from feed.models import Post, Comment
            from jobs.models import Job, Application
            from network.models import Connection, Follow
            from messaging.models import Message, Notification
            from users.models import Experience, Education
            
            stats = {
                'users': User.objects.filter(is_staff=False, is_superuser=False).count(),
                'posts': Post.objects.count(),
                'comments': Comment.objects.count(),
                'jobs': Job.objects.count(),
                'applications': Application.objects.count(),
                'connections': Connection.objects.count(),
                'follows': Follow.objects.count(),
                'messages': Message.objects.count(),
                'notifications': Notification.objects.count(),
                'experiences': Experience.objects.count(),
                'educations': Education.objects.count(),
            }
            
            return JsonResponse({'success': True, 'stats': stats})
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error getting stats: {str(e)}'
            })
