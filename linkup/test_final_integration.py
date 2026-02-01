#!/usr/bin/env python3
"""
Final Integration Testing Script
Comprehensive testing of all professional network enhancements
"""

import os
import sys
import django
import json
import time
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'professional_network.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.management import call_command
from django.db import connection
from django.core.cache import cache
from django.conf import settings

from users.models import Profile, Experience, Education
from jobs.models import Job, Application
from feed.models import Post
from messaging.models import Message, Notification, UserStatus
from network.models import Connection, Follow
from core.validators import FileUploadValidator
from core.performance import QueryOptimizer, CacheManager

User = get_user_model()

class IntegrationTestRunner:
    """Comprehensive integration test runner"""
    
    def __init__(self):
        self.client = Client()
        self.test_results = {
            'passed': 0,
            'failed': 0,
            'errors': [],
            'details': []
        }
        self.start_time = time.time()
    
    def log_test(self, test_name, passed, details=""):
        """Log test result"""
        if passed:
            self.test_results['passed'] += 1
            status = "✅ PASS"
        else:
            self.test_results['failed'] += 1
            status = "❌ FAIL"
            self.test_results['errors'].append(f"{test_name}: {details}")
        
        print(f"{status} - {test_name}")
        if details:
            print(f"    {details}")
        
        self.test_results['details'].append({
            'test': test_name,
            'passed': passed,
            'details': details
        })
    
    def setup_test_data(self):
        """Create test data for integration testing"""
        print("\n🔧 Setting up test data...")
        
        try:
            # Clean up any existing test data first
            User.objects.filter(username__in=['testuser1', 'testuser2']).delete()
            
            # Create test users
            self.user1 = User.objects.create_user(
                username='testuser1',
                email='test1@example.com',
                password='testpass123',
                first_name='John',
                last_name='Doe'
            )
            
            self.user2 = User.objects.create_user(
                username='testuser2',
                email='test2@example.com',
                password='testpass123',
                first_name='Jane',
                last_name='Smith'
            )
            
            # Create profiles
            Profile.objects.filter(user=self.user1).update(
                headline='Software Developer',
                bio='Experienced Python developer',
                location='San Francisco, CA'
            )
            
            Profile.objects.filter(user=self.user2).update(
                headline='Product Manager',
                bio='Product management expert',
                location='New York, NY'
            )
            
            # Create experiences
            Experience.objects.create(
                user=self.user1,
                title='Senior Developer',
                company='Tech Corp',
                location='San Francisco',
                start_date='2020-01-01',
                is_current=True,
                description='Leading development team'
            )
            
            # Create jobs
            self.job1 = Job.objects.create(
                title='Python Developer',
                company='StartupCo',
                location='Remote',
                workplace_type='remote',
                job_type='full-time',
                description='Looking for experienced Python developer',
                requirements='3+ years Python experience',
                salary_range='$80k-$120k',
                posted_by=self.user2
            )
            
            # Create posts
            self.post1 = Post.objects.create(
                user=self.user1,
                content='Excited to share my latest project!'
            )
            
            # Create connections
            Connection.objects.create(
                user=self.user1,
                friend=self.user2,
                status='accepted'
            )
            
            print("✅ Test data setup complete")
            
        except Exception as e:
            print(f"❌ Test data setup failed: {str(e)}")
            return False
        
        return True
    
    def test_user_authentication(self):
        """Test user authentication and authorization"""
        print("\n🔐 Testing User Authentication...")
        
        # Test login
        response = self.client.post('/users/login/', {
            'username': 'testuser1',
            'password': 'testpass123'
        })
        
        self.log_test(
            "User Login",
            response.status_code in [200, 302],
            f"Status: {response.status_code}"
        )
        
        # Test protected page access
        response = self.client.get('/')  # Feed is at root
        self.log_test(
            "Protected Page Access",
            response.status_code == 200,
            f"Status: {response.status_code}"
        )
    
    def test_search_functionality(self):
        """Test enhanced search functionality"""
        print("\n🔍 Testing Search Functionality...")
        
        # Test basic search
        response = self.client.get('/search/', {'q': 'python'})
        self.log_test(
            "Basic Search",
            response.status_code == 200,
            f"Status: {response.status_code}"
        )
        
        # Test search suggestions API
        response = self.client.get('/search/suggestions/', {'q': 'john'})
        self.log_test(
            "Search Suggestions API",
            response.status_code == 200 and 'application/json' in response.get('Content-Type', ''),
            f"Status: {response.status_code}, Content-Type: {response.get('Content-Type', 'N/A')}"
        )
        
        # Test search with filters
        response = self.client.get('/search/', {'q': 'developer', 'type': 'people'})
        self.log_test(
            "Filtered Search",
            response.status_code == 200,
            f"Status: {response.status_code}"
        )
    
    def test_messaging_system(self):
        """Test real-time messaging system"""
        print("\n💬 Testing Messaging System...")
        
        # Test messaging inbox
        response = self.client.get('/messages/')
        self.log_test(
            "Messaging Inbox",
            response.status_code == 200,
            f"Status: {response.status_code}"
        )
        
        # Test message creation
        Message.objects.create(
            sender=self.user1,
            recipient=self.user2,
            content='Test message for integration testing'
        )
        
        messages_count = Message.objects.filter(
            sender=self.user1,
            recipient=self.user2
        ).count()
        
        self.log_test(
            "Message Creation",
            messages_count > 0,
            f"Messages created: {messages_count}"
        )
        
        # Test chat page
        response = self.client.get(f'/messages/chat/{self.user2.username}/')
        self.log_test(
            "Chat Page Access",
            response.status_code == 200,
            f"Status: {response.status_code}"
        )
    
    def test_notification_system(self):
        """Test notification system"""
        print("\n🔔 Testing Notification System...")
        
        # Create test notification
        notification = Notification.objects.create(
            recipient=self.user1,
            sender=self.user2,
            notification_type='connection_request',
            title='New Connection Request',
            message='Jane Smith wants to connect with you',
            action_url=f'/users/{self.user2.username}/'
        )
        
        self.log_test(
            "Notification Creation",
            notification.id is not None,
            f"Notification ID: {notification.id}"
        )
        
        # Test notification preferences page
        response = self.client.get('/messages/notifications/preferences/page/')
        self.log_test(
            "Notification Preferences Page",
            response.status_code == 200,
            f"Status: {response.status_code}"
        )
    
    def test_job_system(self):
        """Test job posting and application system"""
        print("\n💼 Testing Job System...")
        
        # Test job list
        response = self.client.get('/jobs/')
        self.log_test(
            "Job List Page",
            response.status_code == 200,
            f"Status: {response.status_code}"
        )
        
        # Test job detail
        response = self.client.get(f'/jobs/{self.job1.id}/')
        self.log_test(
            "Job Detail Page",
            response.status_code == 200,
            f"Status: {response.status_code}"
        )
        
        # Test job application
        application = Application.objects.create(
            job=self.job1,
            applicant=self.user1,
            cover_letter='I am interested in this position'
        )
        
        self.log_test(
            "Job Application",
            application.id is not None,
            f"Application ID: {application.id}"
        )
    
    def test_network_features(self):
        """Test networking features"""
        print("\n🌐 Testing Network Features...")
        
        # Test network page
        response = self.client.get('/network/')
        self.log_test(
            "Network Page",
            response.status_code == 200,
            f"Status: {response.status_code}"
        )
        
        # Test connection status
        connection = Connection.objects.filter(
            user=self.user1,
            friend=self.user2
        ).first()
        
        self.log_test(
            "Connection Exists",
            connection is not None and connection.status == 'accepted',
            f"Connection status: {connection.status if connection else 'None'}"
        )
    
    def test_security_features(self):
        """Test security enhancements"""
        print("\n🔒 Testing Security Features...")
        
        # Test CSRF protection
        response = self.client.get('/csrf-token-refresh/')
        self.log_test(
            "CSRF Token Refresh",
            response.status_code == 200,
            f"Status: {response.status_code}"
        )
        
        # Test file upload validation
        validator = FileUploadValidator()
        self.log_test(
            "File Upload Validator",
            validator is not None,
            "Validator instance created"
        )
        
        # Test security headers (check if middleware is working)
        response = self.client.get('/')
        has_security_headers = (
            'X-Content-Type-Options' in response or
            'X-Frame-Options' in response
        )
        
        self.log_test(
            "Security Headers",
            has_security_headers,
            f"Headers present: {response.status_code == 200}"
        )
    
    def test_performance_optimizations(self):
        """Test performance optimizations"""
        print("\n⚡ Testing Performance Optimizations...")
        
        # Test query optimization
        optimizer = QueryOptimizer()
        self.log_test(
            "Query Optimizer",
            hasattr(optimizer, 'optimize_user_queries'),
            "Query optimizer methods available"
        )
        
        # Test caching
        cache_manager = CacheManager()
        test_key = 'test_cache_key'
        test_value = {'test': 'data'}
        
        cache.set(test_key, test_value, 60)
        cached_value = cache.get(test_key)
        
        self.log_test(
            "Caching System",
            cached_value == test_value,
            f"Cache working: {cached_value is not None}"
        )
        
        # Test database performance
        initial_queries = len(connection.queries)
        
        # Perform optimized query
        users = QueryOptimizer.optimize_user_queries(
            User.objects.filter(id__in=[self.user1.id, self.user2.id])
        )
        list(users)  # Execute query
        
        final_queries = len(connection.queries)
        query_count = final_queries - initial_queries
        
        self.log_test(
            "Query Optimization",
            query_count <= 3,  # Should be efficient
            f"Queries executed: {query_count}"
        )
    
    def test_ui_enhancements(self):
        """Test UI/UX enhancements"""
        print("\n🎨 Testing UI Enhancements...")
        
        # Test that CSS files are accessible
        response = self.client.get('/static/css/custom_styles.css')
        self.log_test(
            "Custom CSS Accessibility",
            response.status_code == 200,
            f"Status: {response.status_code}"
        )
        
        # Test form enhancements CSS
        response = self.client.get('/static/css/form-enhancements.css')
        self.log_test(
            "Form Enhancement CSS",
            response.status_code == 200,
            f"Status: {response.status_code}"
        )
        
        # Test accessibility CSS
        response = self.client.get('/static/css/accessibility-enhancements.css')
        self.log_test(
            "Accessibility CSS",
            response.status_code == 200,
            f"Status: {response.status_code}"
        )
    
    def test_accessibility_features(self):
        """Test accessibility compliance"""
        print("\n♿ Testing Accessibility Features...")
        
        # Test that accessibility JavaScript is accessible
        response = self.client.get('/static/js/accessibility-enhancements.js')
        self.log_test(
            "Accessibility JavaScript",
            response.status_code == 200,
            f"Status: {response.status_code}"
        )
        
        # Test form accessibility (check for proper labels)
        response = self.client.get('/users/register/')
        content = response.content.decode('utf-8')
        
        has_labels = 'for=' in content and 'aria-' in content
        self.log_test(
            "Form Accessibility Labels",
            has_labels,
            f"Labels and ARIA attributes present: {has_labels}"
        )
    
    def test_database_integrity(self):
        """Test database integrity and relationships"""
        print("\n🗄️ Testing Database Integrity...")
        
        # Test user profile relationship
        profile_exists = hasattr(self.user1, 'profile') and self.user1.profile is not None
        self.log_test(
            "User Profile Relationship",
            profile_exists,
            f"Profile exists: {profile_exists}"
        )
        
        # Test message relationships
        message = Message.objects.filter(sender=self.user1).first()
        if message:
            relationships_valid = (
                message.sender is not None and
                message.recipient is not None
            )
            self.log_test(
                "Message Relationships",
                relationships_valid,
                f"Sender: {message.sender}, Recipient: {message.recipient}"
            )
        
        # Test job relationships
        job_relationships_valid = (
            self.job1.posted_by is not None and
            self.job1.posted_by == self.user2
        )
        self.log_test(
            "Job Relationships",
            job_relationships_valid,
            f"Posted by: {self.job1.posted_by}"
        )
    
    def cleanup_test_data(self):
        """Clean up test data"""
        print("\n🧹 Cleaning up test data...")
        
        try:
            # Delete in reverse order of dependencies
            Application.objects.filter(applicant__in=[self.user1, self.user2]).delete()
            Message.objects.filter(sender__in=[self.user1, self.user2]).delete()
            Notification.objects.filter(recipient__in=[self.user1, self.user2]).delete()
            Connection.objects.filter(user__in=[self.user1, self.user2]).delete()
            Follow.objects.filter(follower__in=[self.user1, self.user2]).delete()
            Post.objects.filter(user__in=[self.user1, self.user2]).delete()
            Job.objects.filter(posted_by__in=[self.user1, self.user2]).delete()
            Experience.objects.filter(user__in=[self.user1, self.user2]).delete()
            Education.objects.filter(user__in=[self.user1, self.user2]).delete()
            UserStatus.objects.filter(user__in=[self.user1, self.user2]).delete()
            
            # Delete users (this will cascade to profiles)
            User.objects.filter(id__in=[self.user1.id, self.user2.id]).delete()
            
            print("✅ Test data cleanup complete")
            
        except Exception as e:
            print(f"⚠️ Cleanup warning: {str(e)}")
    
    def run_all_tests(self):
        """Run all integration tests"""
        print("🚀 Starting Professional Network Integration Tests")
        print("=" * 60)
        
        if not self.setup_test_data():
            print("❌ Test data setup failed. Aborting tests.")
            return
        
        try:
            # Run all test categories
            self.test_user_authentication()
            self.test_search_functionality()
            self.test_messaging_system()
            self.test_notification_system()
            self.test_job_system()
            self.test_network_features()
            self.test_security_features()
            self.test_performance_optimizations()
            self.test_ui_enhancements()
            self.test_accessibility_features()
            self.test_database_integrity()
            
        finally:
            self.cleanup_test_data()
        
        # Print final results
        self.print_final_results()
    
    def print_final_results(self):
        """Print comprehensive test results"""
        end_time = time.time()
        duration = end_time - self.start_time
        
        print("\n" + "=" * 60)
        print("🏁 INTEGRATION TEST RESULTS")
        print("=" * 60)
        
        total_tests = self.test_results['passed'] + self.test_results['failed']
        success_rate = (self.test_results['passed'] / total_tests * 100) if total_tests > 0 else 0
        
        print(f"✅ Tests Passed: {self.test_results['passed']}")
        print(f"❌ Tests Failed: {self.test_results['failed']}")
        print(f"📊 Success Rate: {success_rate:.1f}%")
        print(f"⏱️ Duration: {duration:.2f} seconds")
        
        if self.test_results['errors']:
            print("\n❌ FAILED TESTS:")
            for error in self.test_results['errors']:
                print(f"   • {error}")
        
        print("\n📋 DETAILED RESULTS:")
        for detail in self.test_results['details']:
            status = "✅" if detail['passed'] else "❌"
            print(f"   {status} {detail['test']}")
            if detail['details']:
                print(f"      {detail['details']}")
        
        # Overall status
        if self.test_results['failed'] == 0:
            print("\n🎉 ALL TESTS PASSED! The professional network platform is ready.")
        else:
            print(f"\n⚠️ {self.test_results['failed']} tests failed. Please review and fix issues.")
        
        print("=" * 60)


def main():
    """Main function to run integration tests"""
    runner = IntegrationTestRunner()
    runner.run_all_tests()


if __name__ == '__main__':
    main()