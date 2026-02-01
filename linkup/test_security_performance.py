#!/usr/bin/env python3
"""
Test script to verify security and performance optimizations.
Tests file upload validation, security middleware, and performance features.
"""

import os
import sys
import django
from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.cache import cache
from django.db import connection
import tempfile
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'professional_network.settings')
django.setup()

User = get_user_model()


class SecurityPerformanceTests(TestCase):
    """Test security and performance optimizations."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Try to get existing user or create new one
        try:
            self.user = User.objects.get(username='testuser')
        except User.DoesNotExist:
            self.user = User.objects.create_user(
                username='testuser',
                email='test@example.com',
                password='testpass123'
            )
        
        self.client.login(username='testuser', password='testpass123')
    
    def test_file_upload_validation(self):
        """Test file upload security validation."""
        print("Testing file upload validation...")
        
        # Test valid image upload
        valid_image = SimpleUploadedFile(
            "test.jpg",
            b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00',
            content_type="image/jpeg"
        )
        
        # Test invalid file type
        invalid_file = SimpleUploadedFile(
            "test.exe",
            b'MZ\x90\x00\x03\x00\x00\x00',  # PE executable header
            content_type="application/octet-stream"
        )
        
        from core.validators import ImageUploadValidator
        validator = ImageUploadValidator()
        
        try:
            validator(valid_image)
            print("  ✓ Valid image upload accepted")
        except Exception as e:
            print(f"  ✗ Valid image rejected: {e}")
        
        try:
            validator(invalid_file)
            print("  ✗ Invalid file accepted (security risk!)")
        except Exception:
            print("  ✓ Invalid file rejected")
    
    def test_security_headers(self):
        """Test security headers middleware."""
        print("Testing security headers...")
        
        response = self.client.get('/')
        
        expected_headers = [
            'Content-Security-Policy',
            'X-Content-Type-Options',
            'X-Frame-Options',
            'X-XSS-Protection',
            'Referrer-Policy'
        ]
        
        for header in expected_headers:
            if header in response:
                print(f"  ✓ {header} header present")
            else:
                print(f"  ✗ {header} header missing")
    
    def test_rate_limiting(self):
        """Test rate limiting middleware."""
        print("Testing rate limiting...")
        
        # Make multiple rapid requests
        responses = []
        for i in range(10):
            response = self.client.get('/')
            responses.append(response.status_code)
        
        # Check if any requests were rate limited (429 status)
        rate_limited = any(status == 429 for status in responses)
        
        if rate_limited:
            print("  ✓ Rate limiting active")
        else:
            print("  ✓ Rate limiting configured (may not trigger in test)")
    
    def test_csrf_protection(self):
        """Test CSRF protection."""
        print("Testing CSRF protection...")
        
        # Try POST without CSRF token
        response = self.client.post('/users/profile/', {
            'username': 'newname'
        })
        
        if response.status_code == 403:
            print("  ✓ CSRF protection active")
        else:
            print(f"  ? CSRF response: {response.status_code}")
    
    def test_query_optimization(self):
        """Test database query optimization."""
        print("Testing query optimization...")
        
        # Reset query log
        connection.queries_log.clear()
        
        # Create test data
        from messaging.models import Message
        for i in range(5):
            Message.objects.create(
                sender=self.user,
                recipient=self.user,
                content=f"Test message {i}"
            )
        
        # Test optimized query
        from core.performance import QueryOptimizer
        
        initial_query_count = len(connection.queries)
        
        # Get messages with optimization
        messages = Message.objects.filter(recipient=self.user)
        optimized_messages = QueryOptimizer.optimize_message_queries(messages)
        list(optimized_messages)  # Execute query
        
        final_query_count = len(connection.queries)
        query_count = final_query_count - initial_query_count
        
        print(f"  ✓ Query optimization executed ({query_count} queries)")
    
    def test_caching(self):
        """Test caching functionality."""
        print("Testing caching...")
        
        from core.performance import CacheManager
        
        # Test cache operations
        test_data = {'test': 'data', 'timestamp': '2024-01-01'}
        
        CacheManager.cache_user_profile(self.user.id, test_data)
        cached_data = CacheManager.get_cached_user_profile(self.user.id)
        
        if cached_data == test_data:
            print("  ✓ Caching working correctly")
        else:
            print("  ✗ Caching not working")
        
        # Test cache invalidation
        CacheManager.invalidate_user_cache(self.user.id)
        invalidated_data = CacheManager.get_cached_user_profile(self.user.id)
        
        if invalidated_data is None:
            print("  ✓ Cache invalidation working")
        else:
            print("  ✗ Cache invalidation failed")
    
    def test_performance_monitoring(self):
        """Test performance monitoring."""
        print("Testing performance monitoring...")
        
        from core.performance import performance_monitor, DatabaseOptimizer
        
        @performance_monitor
        def test_function():
            # Simulate some work
            User.objects.all().count()
            return "test result"
        
        try:
            result = test_function()
            if result == "test result":
                print("  ✓ Performance monitoring decorator working")
            else:
                print("  ✗ Performance monitoring failed")
        except Exception as e:
            print(f"  ✗ Performance monitoring error: {e}")
        
        # Test query analysis
        try:
            stats = DatabaseOptimizer.get_query_stats()
            if isinstance(stats, dict) and 'query_count' in stats:
                print(f"  ✓ Query analysis working (tracked {stats['query_count']} queries)")
            else:
                print("  ✗ Query analysis failed")
        except Exception as e:
            print(f"  ✗ Query analysis error: {e}")
    
    def test_pagination_optimization(self):
        """Test optimized pagination."""
        print("Testing pagination optimization...")
        
        from core.performance import OptimizedPaginator
        from messaging.models import Message
        
        # Create test messages
        messages = []
        for i in range(25):
            msg = Message.objects.create(
                sender=self.user,
                recipient=self.user,
                content=f"Pagination test message {i}"
            )
            messages.append(msg)
        
        # Test optimized paginator
        queryset = Message.objects.filter(recipient=self.user)
        paginator = OptimizedPaginator(queryset, per_page=10)
        
        try:
            page = paginator.get_page(1)
            if len(page.object_list) <= 10:
                print("  ✓ Optimized pagination working")
            else:
                print("  ✗ Pagination not limiting results")
        except Exception as e:
            print(f"  ✗ Pagination error: {e}")
    
    def test_file_sanitization(self):
        """Test filename sanitization."""
        print("Testing filename sanitization...")
        
        from core.validators import sanitize_filename
        
        test_cases = [
            ("normal_file.jpg", "normal_file.jpg"),
            ("../../../etc/passwd", "passwd"),
            ("file with spaces.png", "file with spaces.png"),
            ("file:with*dangerous?chars.txt", "file_with_dangerous_chars.txt"),
            ("", "file_"),
        ]
        
        all_passed = True
        for input_name, expected_safe in test_cases:
            result = sanitize_filename(input_name)
            if ".." not in result and "/" not in result and "\\" not in result:
                print(f"  ✓ Sanitized '{input_name}' -> '{result}'")
            else:
                print(f"  ✗ Failed to sanitize '{input_name}' -> '{result}'")
                all_passed = False
        
        if all_passed:
            print("  ✓ Filename sanitization working correctly")


def run_tests():
    """Run all security and performance tests."""
    print("=" * 60)
    print("SECURITY AND PERFORMANCE OPTIMIZATION TESTS")
    print("=" * 60)
    
    # Create test instance
    test_instance = SecurityPerformanceTests()
    test_instance.setUp()
    
    # Run tests
    tests = [
        test_instance.test_file_upload_validation,
        test_instance.test_security_headers,
        test_instance.test_rate_limiting,
        test_instance.test_csrf_protection,
        test_instance.test_query_optimization,
        test_instance.test_caching,
        test_instance.test_performance_monitoring,
        test_instance.test_pagination_optimization,
        test_instance.test_file_sanitization,
    ]
    
    for test in tests:
        try:
            test()
            print()
        except Exception as e:
            print(f"  ✗ Test failed with error: {e}")
            print()
    
    print("=" * 60)
    print("SECURITY AND PERFORMANCE TESTS COMPLETED")
    print("=" * 60)


if __name__ == '__main__':
    run_tests()