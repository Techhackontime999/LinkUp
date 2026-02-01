import os
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'professional_network.settings')
django.setup()

from django.test import Client
from django.urls import reverse

print("--- Testing Search URL Resolution ---")
try:
    url = reverse('search')
    print(f"URL for 'search': {url}")
except Exception as e:
    print(f"URL Resolution Failed: {e}")

print("\n--- Testing Search View ---")
c = Client()
try:
    response = c.get(reverse('search'), {'q': 'test'})
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("Search successful")
        print("Context keys:", list(response.context.keys()))
        print("Users found:", len(response.context['users']))
        print("Posts found:", len(response.context['posts']))
    else:
        print("Search failed or redirected")
except Exception as e:
    print(f"Exception during request: {e}")
