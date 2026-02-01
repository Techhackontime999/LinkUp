from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from .models import User, Profile, Experience, Education

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, help_text="Required. Enter a valid email address.")
    
    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            # Give auth inputs a premium look with enhanced form classes
            field.widget.attrs.update({
                'class': 'auth-input form-field-enhanced',
                'data-validation': '{}' if field.required else '{"required": false}'
            })
            if getattr(field.widget, 'input_type', '') == 'password':
                field.widget.attrs.update({
                    'placeholder': 'Create a secure password',
                    'data-validation': '{"minLength": 8, "required": true}'
                })
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email
    
    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords don't match")
        if password1:
            validate_password(password1)
        return password2

class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'form-input form-field-enhanced',
                'data-validation': '{}' if field.required else '{"required": false}'
            })
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError("A user with this email already exists.")
        return email

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['headline', 'bio', 'location', 'avatar']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Tell us about yourself...'}),
            'headline': forms.TextInput(attrs={'placeholder': 'Your professional headline'}),
            'location': forms.TextInput(attrs={'placeholder': 'City, Country'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if field.widget.__class__.__name__ != 'ClearableFileInput':
                field.widget.attrs.update({
                    'class': 'form-input form-field-enhanced',
                    'data-validation': '{}' if field.required else '{"required": false}'
                })
    
    def clean_headline(self):
        headline = self.cleaned_data.get('headline')
        if headline and len(headline) > 255:
            raise ValidationError("Headline must be 255 characters or less.")
        return headline

class ExperienceForm(forms.ModelForm):
    class Meta:
        model = Experience
        fields = ['title', 'company', 'location', 'start_date', 'end_date', 'is_current', 'description']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Describe your role and achievements...'}),
            'title': forms.TextInput(attrs={'placeholder': 'Job Title'}),
            'company': forms.TextInput(attrs={'placeholder': 'Company Name'}),
            'location': forms.TextInput(attrs={'placeholder': 'City, Country'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if field.widget.input_type != 'checkbox':
                field.widget.attrs.update({
                    'class': 'form-input form-field-enhanced',
                    'data-validation': '{}' if field.required else '{"required": false}'
                })
            if field.widget.input_type == 'textarea':
                field.widget.attrs.update({'class': 'form-textarea form-field-enhanced'})
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        is_current = cleaned_data.get('is_current')
        
        if not is_current and not end_date:
            raise ValidationError("End date is required unless this is your current position.")
        
        if start_date and end_date and start_date > end_date:
            raise ValidationError("Start date cannot be after end date.")
        
        return cleaned_data

class EducationForm(forms.ModelForm):
    class Meta:
        model = Education
        fields = ['school', 'degree', 'field_of_study', 'start_date', 'end_date', 'description']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Additional details about your education...'}),
            'school': forms.TextInput(attrs={'placeholder': 'School/University Name'}),
            'degree': forms.TextInput(attrs={'placeholder': 'Degree Type (e.g., Bachelor of Science)'}),
            'field_of_study': forms.TextInput(attrs={'placeholder': 'Field of Study (e.g., Computer Science)'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if field.widget.input_type != 'checkbox':
                field.widget.attrs.update({
                    'class': 'form-input form-field-enhanced',
                    'data-validation': '{}' if field.required else '{"required": false}'
                })
            if field.widget.input_type == 'textarea':
                field.widget.attrs.update({'class': 'form-textarea form-field-enhanced'})
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise ValidationError("Start date cannot be after end date.")
        
        return cleaned_data
