from django import forms
from .models import Post, Comment

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['content', 'image']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-textarea form-field-enhanced',
                'rows': 4,
                'placeholder': 'What\'s on your mind? Share your thoughts with your professional network...',
                'data-validation': '{"minLength": 10, "maxLength": 1000}'
            }),
            'image': forms.FileInput(attrs={
                'class': 'file-input file-input-bordered w-full max-w-xs form-field-enhanced',
                'accept': 'image/*'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['content'].required = True
        self.fields['image'].required = False


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none',
                'rows': 2,
                'placeholder': 'Write a comment...',
                'maxlength': '500'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['content'].required = True
        self.fields['content'].label = ''
