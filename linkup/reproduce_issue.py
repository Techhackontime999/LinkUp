
import os
import django
from django.urls import reverse

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'professional_network.settings')
django.setup()

try:
    print(f"Reverse 'network': {reverse('network')}")
    print(f"Reverse 'send_request' with id 1: {reverse('send_request', args=[1])}")
    print(f"Reverse 'search': {reverse('search')}")
except Exception as e:
    print(f"Error: {e}")
