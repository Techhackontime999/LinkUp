from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import IntegrityError
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Job, Application, SavedJob
from .forms import JobForm, ApplicationForm, JobSearchForm

@login_required
def job_list(request):
    # Initialize search form with GET parameters
    search_form = JobSearchForm(request.GET)
    jobs = Job.objects.filter(is_active=True).select_related('posted_by')
    
    # Apply search filters using GET parameters directly
    if request.GET:
        query = request.GET.get('query')
        location = request.GET.get('location')
        workplace_type = request.GET.get('workplace_type')
        job_type = request.GET.get('job_type')
        
        if query:
            jobs = jobs.filter(
                Q(title__icontains=query) |
                Q(company__icontains=query) |
                Q(description__icontains=query) |
                Q(requirements__icontains=query)
            )
        
        if location:
            jobs = jobs.filter(location__icontains=location)
        
        if workplace_type:
            jobs = jobs.filter(workplace_type=workplace_type)
        
        if job_type:
            jobs = jobs.filter(job_type=job_type)
    
    # Pagination
    paginator = Paginator(jobs, 10)  # Show 10 jobs per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'jobs/job_list.html', {
        'page_obj': page_obj,
        'search_form': search_form,
        'total_jobs': jobs.count()
    })

@login_required
def job_detail(request, pk):
    job = get_object_or_404(Job, pk=pk)
    has_applied = Application.objects.filter(job=job, applicant=request.user).exists()
    is_saved = SavedJob.objects.filter(job=job, user=request.user).exists()
    return render(request, 'jobs/job_detail.html', {'job': job, 'has_applied': has_applied, 'is_saved': is_saved})

@login_required
def job_create(request):
    if request.method == 'POST':
        form = JobForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.posted_by = request.user
            job.save()
            messages.success(request, 'Job posted successfully!')
            return redirect('jobs:job_detail', pk=job.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = JobForm()
    
    return render(request, 'jobs/job_form.html', {'form': form})

@login_required
def job_edit(request, pk):
    job = get_object_or_404(Job, pk=pk, posted_by=request.user)
    
    if request.method == 'POST':
        form = JobForm(request.POST, instance=job)
        if form.is_valid():
            form.save()
            messages.success(request, 'Job updated successfully!')
            return redirect('jobs:job_detail', pk=job.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = JobForm(instance=job)
    
    return render(request, 'jobs/job_form.html', {'form': form, 'job': job})

@login_required
def job_delete(request, pk):
    job = get_object_or_404(Job, pk=pk, posted_by=request.user)
    
    if request.method == 'POST':
        job.delete()
        messages.success(request, 'Job deleted successfully!')
        return redirect('jobs:job_list')
    
    return render(request, 'jobs/job_confirm_delete.html', {'job': job})

@login_required
def apply_job(request, pk):
    job = get_object_or_404(Job, pk=pk)
    
    # Check if user already applied
    if Application.objects.filter(job=job, applicant=request.user).exists():
        messages.warning(request, 'You have already applied for this job.')
        return redirect('jobs:job_detail', pk=job.pk)
    
    if request.method == 'POST':
        form = ApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                application = form.save(commit=False)
                application.job = job
                application.applicant = request.user
                application.save()
                messages.success(request, f'Successfully applied for {job.title} at {job.company}!')
                return redirect('jobs:job_detail', pk=job.pk)
            except IntegrityError:
                messages.error(request, 'An error occurred while submitting your application. Please try again.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ApplicationForm()
    
    return render(request, 'jobs/apply_form.html', {'job': job, 'form': form})

@login_required
def my_jobs(request):
    """View for jobs posted by the current user"""
    jobs = Job.objects.filter(posted_by=request.user).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(jobs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'jobs/my_jobs.html', {'page_obj': page_obj})

@login_required
def my_applications(request):
    """View for applications submitted by current user"""
    applications = Application.objects.filter(applicant=request.user).select_related('job').order_by('-applied_at')
    
    # Calculate pending count
    pending_count = applications.filter(status='pending').count()
    
    # Pagination
    paginator = Paginator(applications, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'jobs/my_applications.html', {
        'page_obj': page_obj,
        'pending_count': pending_count
    })

@login_required
def saved_jobs(request):
    """View for jobs saved by current user"""
    saved_jobs = SavedJob.objects.filter(user=request.user).select_related('job').order_by('-saved_at')
    
    # Pagination
    paginator = Paginator(saved_jobs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'jobs/saved_jobs.html', {'page_obj': page_obj})

@login_required
def save_job(request, pk):
    """Save/unsave a job"""
    job = get_object_or_404(Job, pk=pk)
    saved_job, created = SavedJob.objects.get_or_create(
        job=job,
        user=request.user
    )
    
    if created:
        messages.success(request, f'Job "{job.title}" saved successfully!')
    else:
        saved_job.delete()
        messages.info(request, f'Job "{job.title}" removed from saved jobs.')
    
    return redirect('jobs:job_detail', pk=pk)

@login_required
def job_alerts(request):
    """View for job alerts (placeholder for future implementation)"""
    return render(request, 'jobs/job_alerts.html')
