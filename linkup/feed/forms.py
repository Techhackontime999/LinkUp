from django import forms
from .models import Post, Comment

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['content', 'image']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'textarea-premium',
                'rows': 4,
                'placeholder': 'Share your thoughts with your professional network...',
                'data-autogrow': 'true'
            }),
            'image': forms.FileInput(attrs={
                'class': 'file-input-premium',
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
                'class': 'input-premium',
                'rows': 2,
                'placeholder': 'Write a comment...',
                'maxlength': '500',
                'style': 'min-height:40px;resize:none'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['content'].required = True
        self.fields['content'].label = ''
