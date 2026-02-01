#!/usr/bin/env python3
"""
Test script for messaging enhancements
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'professional_network.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from messaging.models import Message, QueuedMessage, UserStatus
import json

User = get_user_model()

def test_messaging_enhancements():
    """Test the enhanced messaging features"""
    print("Testing messaging enhancements...")
    
    # Create test users or get existing ones
    user1, created = User.objects.get_or_create(
        username='testuser1', 
        defaults={'email': 'test1@example.com'}
    )
    if created:
        user1.set_password('testpass123')
        user1.save()
    
    user2, created = User.objects.get_or_create(
        username='testuser2', 
        defaults={'email': 'test2@example.com'}
    )
    if created:
        user2.set_password('testpass123')
        user2.save()
    
    client = Client()
    client.login(username='testuser1', password='testpass123')
    
    print("✓ Test users ready and logged in")
    
    # Test 1: Progressive message loading endpoint
    try:
        response = client.get(reverse('messaging:fetch_history', args=['testuser2']))
        print(f"Response status: {response.status_code}")
        if response.status_code != 200:
            print(f"Response content: {response.content}")
        else:
            data = response.json()
            assert 'messages' in data
            assert 'pagination' in data
            print("✓ Progressive message loading endpoint works")
    except Exception as e:
        print(f"✗ Progressive message loading failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Queue message functionality
    try:
        response = client.post(
            reverse('messaging:queue_message', args=['testuser2']),
            data=json.dumps({'message': 'Test queued message'}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get('queued') == True
        assert QueuedMessage.objects.filter(sender=user1, recipient=user2).exists()
        print("✓ Message queuing functionality works")
    except Exception as e:
        print(f"✗ Message queuing failed: {e}")
    
    # Test 3: Load older messages endpoint
    try:
        # Create some test messages first
        msg1 = Message.objects.create(sender=user1, recipient=user2, content="Message 1")
        msg2 = Message.objects.create(sender=user2, recipient=user1, content="Message 2")
        
        response = client.get(
            reverse('messaging:load_older_messages', args=['testuser2']) + 
            f'?before_id={msg2.id}&page_size=10'
        )
        assert response.status_code == 200
        data = response.json()
        assert 'messages' in data
        assert 'has_more' in data
        print("✓ Load older messages endpoint works")
    except Exception as e:
        print(f"✗ Load older messages failed: {e}")
    
    # Test 4: User status tracking
    try:
        status, created = UserStatus.objects.get_or_create(user=user1)
        status.is_online = True
        status.save()
        
        response = client.get(reverse('messaging:user_status', args=['testuser1']))
        assert response.status_code == 200
        data = response.json()
        assert data.get('is_online') == True
        print("✓ User status tracking works")
    except Exception as e:
        print(f"✗ User status tracking failed: {e}")
    
    # Test 5: Message retry queue processing
    try:
        from messaging.management.commands.process_queued_messages import Command
        command = Command()
        # This would normally process queued messages
        print("✓ Message retry queue command exists")
    except Exception as e:
        print(f"✗ Message retry queue failed: {e}")
    
    print("\nMessaging enhancements test completed!")
    
    # Don't delete existing users in case they're being used elsewhere
    print("Test completed - users preserved")

if __name__ == '__main__':
    test_messaging_enhancements()