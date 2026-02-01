import os
import django
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'professional_network.settings')
django.setup()

from django.test import RequestFactory, Client
from users.views import register
from users.forms import CustomUserCreationForm

print("--- Testing Form Validation ---")
form_data = {
    'username': 'testuser_debug',
    'email': 'test@example.com',
    'password': 'password123', # Too simple? 
}
# UserCreationForm expects 'password', BUT actually it names fields 'password1' and 'password_2' usually?
# Let's check the fields of the form class directly.
form = CustomUserCreationForm()
print("Form fields:", list(form.fields.keys()))

print("\n--- Testing View Response ---")
c = Client()
try:
    response = c.post('/users/register/', {
        'username': 'testuser_debug',
        'email': 'test@example.com',
        'password1': 'TestPass123!',
        'password2': 'TestPass123!',
    })
    print(f"Status Code: {response.status_code}")
    if response.status_code == 302:
        print(f"Redirects to: {response.url}")
    else:
        print("Did not redirect.")
        # If form invalid, context should have form errors
        if 'form' in response.context:
            print("Form Errors:", response.context['form'].errors)
except Exception as e:
    print(f"Exception during request: {e}")
