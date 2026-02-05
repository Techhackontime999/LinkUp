"""
Property-based tests for connection stability
**Validates: Requirements 3.4**
"""
import pytest
from hypothesis import given, strategies as st, assume, settings
from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest.mock import Mock, MagicMock, patch
from .connection_validator import ConnectionValidator
from .logging_utils import MessagingLogger

User = get_user_model()


class TestConnectionStability(TestCase):
    """Property tests for connection stability under various error conditions"""
    
    def setUp(self):
        self.validator = ConnectionValidator()
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    @given(
        error_scenarios=st.lists(
            st.sampled_from([
                'database_error',
                'network_error',
                'serialization_error',
                'validation_error',
                'timeout_error',
                'memory_error',
                'permission_error'
            ]),
            min_size=1,
            max_size=5
        ),
        connection_count=st.integers(min_value=1, max_value=20)
    )
    @settings(max_examples=50, deadline=10000)
    def test_property_connection_stability_under_errors(self, error_scenarios, connection_count):
        """
        **Property 6: Connection Stability**
        **Validates: Requirements 3.4**
        
        Property: The connection validator must maintain stability and continue
        processing connections even when individual operations encounter errors.
        """
        successful_validations = 0
        total_validations = 0
        
        for i in range(connection_count):
            for error_type in error_scenarios:
                total_validations += 1
                
                try:
                    # Simulate different error scenarios
                    scope = self._create_scope_with_error_scenario(error_type, i)
                    
                    # Validation should not crash even with error scenarios
                    result = self.validator.validate_connection_scope(scope)
                    
                    # Verify result structure is maintained
                    assert isinstance(result, dict), "Result must be dictionary even with errors"
                    assert 'is_valid' in result, "Result must contain is_valid field"
                    assert 'errors' in result, "Result must contain errors field"
                    
                    # Count successful validations (not crashing is success)
                    successful_validations += 1
                    
                except Exception as e:
                    # Connection stability means we should not crash
                    pytest.fail(f"Connection validation crashed with {error_type}: {e}")
        
        # All validations should complete without crashing
        assert successful_validations == total_validations, \
            f"Expected {total_validations} successful validations, got {successful_validations}"
    
    @given(
        concurrent_operations=st.integers(min_value=2, max_value=10),
        operation_types=st.lists(
            st.sampled_from(['validate_scope', 'validate_message', 'extract_user', 'generate_error']),
            min_size=2,
            max_size=8
        )
    )
    @settings(max_examples=30, deadline=8000)
    def test_property_concurrent_operation_stability(self, concurrent_operations, operation_types):
        """
        **Property 6: Connection Stability (Concurrent Operations)**
        **Validates: Requirements 3.4**
        
        Property: The connection validator must handle concurrent operations
        without state corruption or crashes.
        """
        import threading
        import time
        
        results = []
        errors = []
        
        def perform_operation(operation_type, operation_id):
            try:
                if operation_type == 'validate_scope':
                    scope = self._create_test_scope(operation_id)
                    result = self.validator.validate_connection_scope(scope)
                    results.append(('scope', operation_id, result))
                    
                elif operation_type == 'validate_message':
                    message = self._create_test_message(operation_id)
                    result = self.validator.validate_message_data(message)
                    results.append(('message', operation_id, result))
                    
                elif operation_type == 'extract_user':
                    scope = self._create_test_scope(operation_id)
                    user = self.validator.safe_get_user(scope)
                    results.append(('user', operation_id, user))
                    
                elif operation_type == 'generate_error':
                    error_list = [f'Error {operation_id}']
                    response = self.validator.generate_error_response(error_list)
                    results.append(('error', operation_id, response))
                    
            except Exception as e:
                errors.append((operation_type, operation_id, str(e)))
        
        # Create and start threads for concurrent operations
        threads = []
        for i in range(concurrent_operations):
            operation_type = operation_types[i % len(operation_types)]
            thread = threading.Thread(target=perform_operation, args=(operation_type, i))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=5.0)  # 5 second timeout per thread
        
        # Verify no errors occurred during concurrent operations
        assert len(errors) == 0, f"Concurrent operations failed: {errors}"
        
        # Verify we got results from all operations
        assert len(results) == concurrent_operations, \
            f"Expected {concurrent_operations} results, got {len(results)}"
        
        # Verify all results have proper structure
        for result_type, operation_id, result in results:
            if result_type in ['scope', 'message']:
                assert isinstance(result, dict), f"Result {operation_id} must be dict"
                assert 'is_valid' in result, f"Result {operation_id} must have is_valid"
            elif result_type == 'error':
                assert isinstance(result, dict), f"Error response {operation_id} must be dict"
                assert 'error' in result, f"Error response {operation_id} must have error field"
    
    @given(
        memory_pressure_size=st.integers(min_value=100, max_value=1000),
        validation_cycles=st.integers(min_value=5, max_value=20)
    )
    @settings(max_examples=20, deadline=15000)
    def test_property_memory_stability_under_pressure(self, memory_pressure_size, validation_cycles):
        """
        **Property 6: Connection Stability (Memory Pressure)**
        **Validates: Requirements 3.4**
        
        Property: The connection validator must maintain stability under memory pressure
        and not leak memory during repeated operations.
        """
        import gc
        
        # Force garbage collection before test
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        for cycle in range(validation_cycles):
            # Create large scope data to simulate memory pressure
            large_scope = self._create_large_scope_data(memory_pressure_size)
            
            try:
                # Perform validation under memory pressure
                result = self.validator.validate_connection_scope(large_scope)
                
                # Verify result structure is maintained
                assert isinstance(result, dict), f"Cycle {cycle}: Result must be dictionary"
                assert 'is_valid' in result, f"Cycle {cycle}: Result must contain is_valid"
                
                # Clear large data to prevent accumulation
                del large_scope
                
                # Periodic garbage collection
                if cycle % 5 == 0:
                    gc.collect()
                    
            except MemoryError:
                # Memory errors are acceptable under extreme pressure
                # but should not crash the validator
                pass
            except Exception as e:
                pytest.fail(f"Cycle {cycle}: Unexpected error under memory pressure: {e}")
        
        # Force final garbage collection
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # Memory usage should not grow excessively (allow some growth for test overhead)
        memory_growth = final_objects - initial_objects
        max_allowed_growth = validation_cycles * 50  # Allow 50 objects per cycle
        
        assert memory_growth < max_allowed_growth, \
            f"Excessive memory growth: {memory_growth} objects (max allowed: {max_allowed_growth})"
    
    @given(
        error_injection_rate=st.floats(min_value=0.1, max_value=0.8),
        recovery_cycles=st.integers(min_value=3, max_value=15)
    )
    @settings(max_examples=25, deadline=10000)
    def test_property_error_recovery_stability(self, error_injection_rate, recovery_cycles):
        """
        **Property 6: Connection Stability (Error Recovery)**
        **Validates: Requirements 3.4**
        
        Property: The connection validator must recover gracefully from errors
        and continue processing subsequent requests normally.
        """
        successful_operations = 0
        total_operations = 0
        
        for cycle in range(recovery_cycles):
            # Inject errors based on rate
            inject_error = (cycle / recovery_cycles) < error_injection_rate
            
            try:
                if inject_error:
                    # Create problematic data that should cause validation errors
                    scope = self._create_problematic_scope(cycle)
                else:
                    # Create valid data
                    scope = self._create_valid_scope(cycle)
                
                total_operations += 1
                result = self.validator.validate_connection_scope(scope)
                
                # Verify result structure is always maintained
                assert isinstance(result, dict), f"Cycle {cycle}: Result must be dictionary"
                assert 'is_valid' in result, f"Cycle {cycle}: Result must contain is_valid"
                assert 'errors' in result, f"Cycle {cycle}: Result must contain errors"
                
                # For injected errors, validation should fail gracefully
                if inject_error:
                    assert not result['is_valid'], f"Cycle {cycle}: Problematic data should be invalid"
                    assert len(result['errors']) > 0, f"Cycle {cycle}: Should have error messages"
                else:
                    # Valid data should pass validation
                    assert result['is_valid'], f"Cycle {cycle}: Valid data should pass validation"
                
                successful_operations += 1
                
            except Exception as e:
                pytest.fail(f"Cycle {cycle}: Error recovery failed: {e}")
        
        # All operations should complete (error recovery means no crashes)
        assert successful_operations == total_operations, \
            f"Expected {total_operations} successful operations, got {successful_operations}"
    
    def _create_scope_with_error_scenario(self, error_type, operation_id):
        """Create scope data that simulates specific error scenarios"""
        base_scope = {
            'user': self.test_user,
            'url_route': {'kwargs': {'username': f'user_{operation_id}'}},
            'headers': [[b'host', b'localhost']],
            'query_string': b'test=1'
        }
        
        if error_type == 'database_error':
            # Create user mock that raises database errors
            mock_user = Mock()
            mock_user.is_authenticated = True
            mock_user.is_active = True
            mock_user.id = operation_id
            base_scope['user'] = mock_user
            
        elif error_type == 'serialization_error':
            # Add non-serializable objects
            base_scope['complex_object'] = Mock()
            
        elif error_type == 'validation_error':
            # Create malformed data structures
            base_scope['url_route'] = 'not_a_dict'
            
        elif error_type == 'network_error':
            # Simulate network-related data corruption
            base_scope['headers'] = [['corrupted', None, 'extra']]
            
        elif error_type == 'timeout_error':
            # Create large data that might cause timeouts
            base_scope['large_data'] = 'x' * 10000
            
        elif error_type == 'memory_error':
            # Create memory-intensive structures
            base_scope['memory_intensive'] = ['data'] * 1000
            
        elif error_type == 'permission_error':
            # Create user without proper permissions
            mock_user = Mock()
            mock_user.is_authenticated = False
            mock_user.is_active = False
            base_scope['user'] = mock_user
        
        return base_scope
    
    def _create_test_scope(self, operation_id):
        """Create test scope for concurrent operations"""
        mock_user = Mock()
        mock_user.is_authenticated = True
        mock_user.is_active = True
        mock_user.id = operation_id
        
        return {
            'user': mock_user,
            'url_route': {'kwargs': {'username': f'user_{operation_id}'}},
            'headers': [[b'host', b'localhost']],
            'query_string': b'test=1'
        }
    
    def _create_test_message(self, operation_id):
        """Create test message for concurrent operations"""
        return {
            'type': 'message',
            'message': f'Test message {operation_id}',
            'retry_id': f'retry_{operation_id}'
        }
    
    def _create_large_scope_data(self, size):
        """Create large scope data for memory pressure testing"""
        return {
            'user': self.test_user,
            'url_route': {'kwargs': {'username': 'testuser'}},
            'headers': [[b'host', b'localhost']],
            'query_string': b'test=1',
            'large_data': ['x' * 100] * size  # Create large data structure
        }
    
    def _create_problematic_scope(self, cycle):
        """Create scope data that should cause validation errors"""
        problematic_scopes = [
            None,  # None scope
            'not_a_dict',  # String instead of dict
            {'user': None},  # No user
            {'user': 'not_a_user'},  # Invalid user type
            {'url_route': 'invalid'},  # Invalid url_route type
        ]
        
        return problematic_scopes[cycle % len(problematic_scopes)]
    
    def _create_valid_scope(self, cycle):
        """Create valid scope data"""
        mock_user = Mock()
        mock_user.is_authenticated = True
        mock_user.is_active = True
        mock_user.id = cycle
        
        return {
            'user': mock_user,
            'url_route': {'kwargs': {'username': f'user_{cycle}'}},
            'headers': [[b'host', b'localhost']],
            'query_string': b'test=1'
        }