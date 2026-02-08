from django import forms
from django.core.exceptions import ValidationError
from .models import Job, Application

class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = ['title', 'company', 'location', 'workplace_type', 'job_type', 
                 'description', 'requirements', 'salary_range']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-100 rounded-xl focus:border-purple-400 focus:ring-2 focus:ring-purple-100 transition-all outline-none',
                'placeholder': 'e.g., Senior Software Engineer',
                'required': True
            }),
            'company': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-100 rounded-xl focus:border-purple-400 focus:ring-2 focus:ring-purple-100 transition-all outline-none',
                'placeholder': 'Company Name',
                'required': True
            }),
            'location': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-100 rounded-xl focus:border-purple-400 focus:ring-2 focus:ring-purple-100 transition-all outline-none',
                'placeholder': 'City, Country or Remote',
                'required': True
            }),
            'workplace_type': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-100 rounded-xl focus:border-purple-400 focus:ring-2 focus:ring-purple-100 transition-all outline-none bg-white'
            }),
            'job_type': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-100 rounded-xl focus:border-purple-400 focus:ring-2 focus:ring-purple-100 transition-all outline-none bg-white'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-100 rounded-xl focus:border-purple-400 focus:ring-2 focus:ring-purple-100 transition-all outline-none resize-none',
                'rows': 5,
                'placeholder': 'Describe the role, responsibilities, and what makes this opportunity exciting...',
                'required': True
            }),
            'requirements': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-100 rounded-xl focus:border-purple-400 focus:ring-2 focus:ring-purple-100 transition-all outline-none resize-none',
                'rows': 4,
                'placeholder': 'List the required skills, experience, and qualifications...'
            }),
            'salary_range': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-100 rounded-xl focus:border-purple-400 focus:ring-2 focus:ring-purple-100 transition-all outline-none',
                'placeholder': 'e.g., $80,000 - $120,000 or Competitive'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make certain fields required
        self.fields['title'].required = True
        self.fields['company'].required = True
        self.fields['location'].required = True
        self.fields['description'].required = True
        
        # Add help text
        self.fields['workplace_type'].help_text = "Select the work arrangement for this position"
        self.fields['job_type'].help_text = "Select the employment type"
        self.fields['salary_range'].help_text = "Optional: Provide salary range or 'Competitive'"
    
    def clean_title(self):
        title = self.cleaned_data.get('title')
        if title and len(title.strip()) < 3:
            raise ValidationError("Job title must be at least 3 characters long.")
        return title.strip() if title else title
    
    def clean_company(self):
        company = self.cleaned_data.get('company')
        if company and len(company.strip()) < 2:
            raise ValidationError("Company name must be at least 2 characters long.")
        return company.strip() if company else company
    
    def clean_description(self):
        description = self.cleaned_data.get('description')
        if description and len(description.strip()) < 50:
            raise ValidationError("Job description must be at least 50 characters long.")
        return description.strip() if description else description
    
    def clean_salary_range(self):
        salary_range = self.cleaned_data.get('salary_range')
        if salary_range:
            salary_range = salary_range.strip()
            # Basic validation for salary format
            if salary_range and not any(keyword in salary_range.lower() for keyword in 
                                      ['competitive', 'negotiable', '$', '€', '£', 'usd', 'eur', 'gbp']):
                raise ValidationError("Please provide a valid salary range or use 'Competitive'.")
        return salary_range


class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ['resume', 'cover_letter']
        widgets = {
            'resume': forms.FileInput(attrs={
                'class': 'form-file-input form-field-enhanced',
                'accept': '.pdf,.doc,.docx',
                'data-validation': '{"required": true}'
            }),
            'cover_letter': forms.Textarea(attrs={
                'class': 'form-textarea form-field-enhanced',
                'rows': 8,
                'placeholder': 'Write a compelling cover letter explaining why you\'re the perfect fit for this role...',
                'data-validation': '{"minLength": 100, "required": true}'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cover_letter'].required = True
        self.fields['resume'].help_text = "Upload your resume (PDF, DOC, or DOCX format, max 5MB)"
        self.fields['cover_letter'].help_text = "Tell us why you're interested in this position"
    
    def clean_resume(self):
        resume = self.cleaned_data.get('resume')
        if resume:
            # Check file size (5MB limit)
            if resume.size > 5 * 1024 * 1024:
                raise ValidationError("Resume file size must be less than 5MB.")
            
            # Check file extension
            allowed_extensions = ['.pdf', '.doc', '.docx']
            file_extension = resume.name.lower().split('.')[-1]
            if f'.{file_extension}' not in allowed_extensions:
                raise ValidationError("Resume must be in PDF, DOC, or DOCX format.")
        
        return resume
    
    def clean_cover_letter(self):
        cover_letter = self.cleaned_data.get('cover_letter')
        if cover_letter and len(cover_letter.strip()) < 100:
            raise ValidationError("Cover letter must be at least 100 characters long.")
        return cover_letter.strip() if cover_letter else cover_letter


class JobSearchForm(forms.Form):
    """Form for job search functionality"""
    query = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500',
            'placeholder': 'Search jobs by title, company, or keywords...'
        })
    )
    location = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500',
            'placeholder': 'Location'
        })
    )
    workplace_type = forms.ChoiceField(
        choices=[('', 'Any Workplace Type')] + list(Job.WORKPLACE_TYPE_CHOICES),
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white'
        })
    )
    job_type = forms.ChoiceField(
        choices=[('', 'Any Job Type')] + list(Job.JOB_TYPE_CHOICES),
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white'
        })
    )