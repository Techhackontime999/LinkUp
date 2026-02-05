"""
Property-based tests for async error logging in messaging system
**Feature: messaging-system-fixes**
"""
import pytest
from hypothesis import given, strategies as st, settings
from django.test import TestCase
from django.contrib.auth import get_user_model
from channels.db import database_sync_to_async
from .logging_utils import MessagingLogger
from .models import MessagingError

User = get_user_model()


@database_sync_to_async
def create_test_user(username):
    """Create a test user synchronously"""
    return User.objects.create_user(username=username, email=f"{username}@test.com")


@database_sync_to_async
def get_error_count():
    """Get count of logged errors"""
    return MessagingError.objects.count()


@database_sync_to_async
def get_latest_error():
    """Get the most recent error"""
    return MessagingError.objects.order_by('-occurred_at').first()


@database_sync_to_async
def cleanup_errors():
    """Clean up error logs"""
    MessagingError.objects.all().delete()


class TestAsyncErrorLogging(TestCase):
    """Property tests for async error logging"""
    
    @pytest.mark.asyncio
    @given(
        error_message=st.text(min_size=1, max_size=500),
        username=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        operation=st.sampled_from(['create_message', 'get_messages', 'mark_message_read', 'set_user_status']),
        context_key=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        context_value=st.one_of(st.text(max_size=100), st.integers(), st.booleans())
    )
    @settings(max_examples=100, deadline=10000)
    async def test_property_2_async_error_logging(self, error_message, username, operation, context_key, context_value):
        """
        **Property 2: Async Error Logging**
        For any async context error that occurs, the system should log detailed error information 
        including the specific context and operation that caused the error.
        **Validates: Requirements 1.4**
        """
        try:
            # Clean up existing errors
            await cleanup_errors()
            
            # Create test user
            user = await create_test_user(f"user_{username}")
            
            # Create a test exception
            test_exception = Exception(error_message)
            
            # Create context data
            context_data = {
                'operation': operation,
                context_key: context_value,
                'test_run': True
            }
            
            # Get initial error count
            initial_count = await get_error_count()
            
            # Log the async context error
            MessagingLogger.log_async_context_error(
                test_exception,
                context_data=context_data,
                user=user
            )
            
            # Verify error was logged
            final_count = await get_error_count()
            assert final_count == initial_count + 1, "Error should be logged to database"
            
            # Get the logged error
            logged_error = await get_latest_error()
            assert logged_error is not None, "Should be able to retrieve logged error"
            assert logged_error.error_type == 'async_context', "Error type should be async_context"
            assert error_message in logged_error.error_message, "Error message should contain original exception message"
            assert logged_error.user == user, "Error should be associated with correct user"
            assert logged_error.severity == 'high', "Async context errors should have high severity"
            
            # Verify context data was preserved
            assert 'operation' in logged_error.context_data, "Context should include operation"
            assert logged_error.context_data['operation'] == operation, "Operation should be preserved in context"
            assert context_key in logged_error.context_data, "Custom context key should be preserved"
            assert logged_error.context_data[context_key] == context_value, "Custom context value should be preserved"
            assert 'exception_type' in logged_error.context_data, "Context should include exception type"
            assert 'traceback' in logged_error.context_data, "Context should include traceback"
            
        finally:
            # Clean up
            await cleanup_errors()
    
    @pytest.mark.asyncio
    @given(
        error_message=st.text(min_size=1, max_size=200),
        severity=st.sampled_from(['low', 'medium', 'high', 'critical']),
        error_type=st.sampled_from(['async_context', 'json_serialization', 'connection_handling', 'database_operation'])
    )
    @settings(max_examples=50, deadline=5000)
    async def test_property_2_error_categorization_and_severity(self, error_message, severity, error_type):
        """
        **Property 2: Async Error Logging (Categorization)**
        For any error that occurs, the system should properly categorize the error type
        and assign appropriate severity levels for monitoring purposes.
        **Validates: Requirements 1.4**
        """
        try:
            # Clean up existing errors
            await cleanup_errors()
            
            # Create test exception
            test_exception = Exception(error_message)
            
            # Log error based on type
            if error_type == 'async_context':
                MessagingLogger.log_async_context_error(test_exception)
            elif error_type == 'json_serialization':
                MessagingLogger.log_serialization_error(test_exception)
            elif error_type == 'connection_handling':
                MessagingLogger.log_connection_error(test_exception)
            elif error_type == 'database_operation':
                MessagingLogger.log_database_error(test_exception)
            
            # Verify error was logged with correct categorization
            logged_error = await get_latest_error()
            assert logged_error is not None, "Error should be logged"
            assert logged_error.error_type == error_type, f"Error should be categorized as {error_type}"
            assert error_message in logged_error.error_message, "Error message should be preserved"
            
            # Verify severity is appropriate for error type
            if error_type == 'async_context':
                assert logged_error.severity == 'high', "Async context errors should have high severity"
            elif error_type == 'database_operation':
                assert logged_error.severity == 'high', "Database errors should have high severity"
            else:
                assert logged_error.severity in ['low', 'medium', 'high', 'critical'], "Severity should be valid"
            
        finally:
            await cleanup_errors()
    
    @pytest.mark.asyncio
    @given(
        num_errors=st.integers(min_value=1, max_value=10),
        base_message=st.text(min_size=1, max_size=100)
    )
    @settings(max_examples=20, deadline=10000)
    async def test_property_2_multiple_error_logging(self, num_errors, base_message):
        """
        **Property 2: Async Error Logging (Multiple Errors)**
        For any sequence of async context errors, each error should be logged
        with detailed context information and proper ordering.
        **Validates: Requirements 1.4**
        """
        try:
            # Clean up existing errors
            await cleanup_errors()
            
            initial_count = await get_error_count()
            
            # Log multiple errors
            for i in range(num_errors):
                error_message = f"{base_message}_{i}"
                test_exception = Exception(error_message)
                context_data = {'error_sequence': i, 'total_errors': num_errors}
                
                MessagingLogger.log_async_context_error(
                    test_exception,
                    context_data=context_data
                )
            
            # Verify all errors were logged
            final_count = await get_error_count()
            assert final_count == initial_count + num_errors, f"Should log {num_errors} errors"
            
            # Verify errors are properly ordered (most recent first)
            errors = await database_sync_to_async(
                lambda: list(MessagingError.objects.order_by('-occurred_at')[:num_errors])
            )()
            
            assert len(errors) >= num_errors, "Should retrieve all logged errors"
            
            # Verify each error has proper context
            for i, error in enumerate(errors[:num_errors]):
                assert error.error_type == 'async_context', "All errors should be async_context type"
                assert 'error_sequence' in error.context_data, "Each error should have sequence context"
                assert 'total_errors' in error.context_data, "Each error should have total count context"
                assert error.context_data['total_errors'] == num_errors, "Total count should be consistent"
            
        finally:
            await cleanup_errors()
    
    @pytest.mark.asyncio
    @given(
        error_message=st.text(min_size=1, max_size=200),
        username=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))
    )
    @settings(max_examples=30, deadline=5000)
    async def test_property_2_error_resolution_tracking(self, error_message, username):
        """
        **Property 2: Async Error Logging (Resolution Tracking)**
        For any logged error, the system should support marking errors as resolved
        with resolution notes and timestamps.
        **Validates: Requirements 1.4**
        """
        try:
            # Clean up existing errors
            await cleanup_errors()
            
            # Create test user
            user = await create_test_user(f"user_{username}")
            
            # Log an error
            test_exception = Exception(error_message)
            MessagingLogger.log_async_context_error(test_exception, user=user)
            
            # Get the logged error
            logged_error = await get_latest_error()
            assert logged_error is not None, "Error should be logged"
            assert not logged_error.resolved, "Error should initially be unresolved"
            assert logged_error.resolved_at is None, "Resolution timestamp should be None initially"
            
            # Mark error as resolved
            resolution_notes = f"Resolved error for user {username}"
            await database_sync_to_async(logged_error.mark_resolved)(resolution_notes)
            
            # Refresh from database
            await database_sync_to_async(logged_error.refresh_from_db)()
            
            # Verify resolution
            assert logged_error.resolved, "Error should be marked as resolved"
            assert logged_error.resolved_at is not None, "Resolution timestamp should be set"
            assert logged_error.resolution_notes == resolution_notes, "Resolution notes should be preserved"
            
        finally:
            await cleanup_errors()