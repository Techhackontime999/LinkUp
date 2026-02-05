"""
Property-based tests for startup routing validation
**Validates: Requirements 4.2, 4.4**
"""
import pytest
from hypothesis import given, strategies as st, assume, settings
from django.test import TestCase
from unittest.mock import Mock, patch, MagicMock
from .routing_validator import RoutingValidator

class TestStartupRoutingValidation(TestCase):
    """Property tests for startup routing validation"""
    
    def setUp(self):
        self.validator = RoutingValidator()
    
    @given(
        module_scenarios=st.sampled_from([
            'valid_module',
            'missing_module',
            'module_without_patterns',
            'module_with_invalid_patterns',
            'module_with_mixed_patterns',
            'module_import_error',
            'module_with_exception',
        ]),
        pattern_count=st.integers(min_value=0, max_value=10)
    )
    @settings(max_examples=50, deadline=8000)
    def test_property_startup_validation_robustness(self, module_scenarios, pattern_count):
        """
        **Property 8: Startup Routing Validation**
        **Validates: Requirements 4.2, 4.4**
        
        Property: Startup routing validation must handle all possible module
        states and pattern configurations without crashing, providing clear
        error messages for any issues found.
        """
        try:
            with patch('importlib.import_module') as mock_import:
                # Configure mock based on scenario
                mock_module = self._create_mock_module(module_scenarios, pattern_count)
                
                if module_scenarios == 'missing_module':
                    mock_import.side_effect = ImportError("Module not found")
                elif module_scenarios == 'module_import_error':
                    mock_import.side_effect = ImportError("Import error")
                elif module_scenarios == 'module_with_exception':
                    mock_import.side_effect = Exception("Unexpected error")
                else:
                    mock_import.return_value = mock_module
                
                # Perform startup validation
                result = self.validator.validate_startup_routing('test.routing')
                
                # Verify result structure is always consistent
                assert isinstance(result, dict), "Result must be a dictionary"
                assert 'is_valid' in result, "Result must contain is_valid field"
                assert 'module_loaded' in result, "Result must contain module_loaded field"
                assert 'patterns_found' in result, "Result must contain patterns_found field"
                assert 'validation_results' in result, "Result must contain validation_results field"
                assert 'errors' in result, "Result must contain errors field"
                
                # Verify field types
                assert isinstance(result['is_valid'], bool), "is_valid must be boolean"
                assert isinstance(result['module_loaded'], bool), "module_loaded must be boolean"
                assert isinstance(result['patterns_found'], int), "patterns_found must be integer"
                assert isinstance(result['errors'], list), "errors must be list"
                
                # Verify behavior based on scenario
                if module_scenarios in ['missing_module', 'module_import_error', 'module_with_exception']:
                    assert not result['is_valid'], "Should be invalid for import errors"
                    assert not result['module_loaded'], "Module should not be loaded for import errors"
                    assert len(result['errors']) > 0, "Should have errors for import failures"
                
                elif module_scenarios == 'module_without_patterns':
                    assert not result['is_valid'], "Should be invalid without patterns"
                    assert result['module_loaded'], "Module should be loaded"
                    assert result['patterns_found'] == 0, "Should find 0 patterns"
                    assert len(result['errors']) > 0, "Should have errors for missing patterns"
                
                elif module_scenarios == 'valid_module':
                    assert result['module_loaded'], "Module should be loaded"
                    assert result['patterns_found'] == pattern_count, "Should find correct pattern count"
                    # Validity depends on pattern quality, but should not crash
                
                # Ensure no exceptions were raised
                assert True, "Startup validation completed without exceptions"
                
        except Exception as e:
            pytest.fail(f"Startup routing validation raised exception: {e}")
    
    @given(
        concurrent_validations=st.integers(min_value=2, max_value=8),
        validation_delay=st.floats(min_value=0.0, max_value=0.1)
    )
    @settings(max_examples=20, deadline=10000)
    def test_property_concurrent_startup_validation(self, concurrent_validations, validation_delay):
        """
        **Property 8: Startup Routing Validation (Concurrency)**
        **Validates: Requirements 4.2, 4.4**
        
        Property: Startup validation must handle concurrent validation requests
        without state corruption or race conditions.
        """
        import threading
        import time
        
        results = []
        errors = []
        
        def perform_startup_validation(validation_id):
            try:
                time.sleep(validation_delay)  # Simulate processing time
                
                with patch('importlib.import_module') as mock_import:
                    # Create a valid mock module for each validation
                    mock_module = Mock()
                    mock_module.websocket_urlpatterns = [
                        Mock(pattern=Mock(pattern=f'^ws/test{validation_id}/$'), callback=Mock())
                    ]
                    mock_import.return_value = mock_module
                    
                    result = self.validator.validate_startup_routing(f'test.routing{validation_id}')
                    results.append((validation_id, result))
                    
            except Exception as e:
                errors.append((validation_id, str(e)))
        
        # Create and start threads for concurrent validations
        threads = []
        for i in range(concurrent_validations):
            thread = threading.Thread(target=perform_startup_validation, args=(i,))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=5.0)
        
        # Verify no errors occurred during concurrent validations
        assert len(errors) == 0, f"Concurrent startup validations failed: {errors}"
        
        # Verify we got results from all validations
        assert len(results) == concurrent_validations, \
            f"Expected {concurrent_validations} results, got {len(results)}"
        
        # Verify all results have proper structure
        for validation_id, result in results:
            assert isinstance(result, dict), f"Result {validation_id} must be dict"
            assert 'is_valid' in result, f"Result {validation_id} must have is_valid"
            assert 'module_loaded' in result, f"Result {validation_id} must have module_loaded"
            assert 'patterns_found' in result, f"Result {validation_id} must have patterns_found"
    
    @given(
        error_injection_scenarios=st.lists(
            st.sampled_from([
                'import_error',
                'attribute_error',
                'type_error',
                'value_error',
                'runtime_error',
            ]),
            min_size=1,
            max_size=5
        ),
        recovery_attempts=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=30, deadline=8000)
    def test_property_startup_validation_error_recovery(self, error_injection_scenarios, recovery_attempts):
        """
        **Property 8: Startup Routing Validation (Error Recovery)**
        **Validates: Requirements 4.2, 4.4**
        
        Property: Startup validation must recover gracefully from various error
        conditions and continue to function properly for subsequent validations.
        """
        successful_validations = 0
        total_validations = 0
        
        for attempt in range(recovery_attempts):
            for error_scenario in error_injection_scenarios:
                total_validations += 1
                
                try:
                    with patch('importlib.import_module') as mock_import:
                        # Inject different types of errors
                        if error_scenario == 'import_error':
                            mock_import.side_effect = ImportError(f"Import error {attempt}")
                        elif error_scenario == 'attribute_error':
                            mock_module = Mock()
                            del mock_module.websocket_urlpatterns  # Remove attribute
                            mock_import.return_value = mock_module
                        elif error_scenario == 'type_error':
                            mock_module = Mock()
                            mock_module.websocket_urlpatterns = "not_a_list"  # Wrong type
                            mock_import.return_value = mock_module
                        elif error_scenario == 'value_error':
                            mock_module = Mock()
                            mock_module.websocket_urlpatterns = [None, "invalid"]  # Invalid values
                            mock_import.return_value = mock_module
                        elif error_scenario == 'runtime_error':
                            mock_import.side_effect = RuntimeError(f"Runtime error {attempt}")
                        
                        # Validation should handle errors gracefully
                        result = self.validator.validate_startup_routing(f'test.routing.{attempt}.{error_scenario}')
                        
                        # Verify result structure is maintained even with errors
                        assert isinstance(result, dict), f"Result must be dict for {error_scenario}"
                        assert 'is_valid' in result, f"Result must have is_valid for {error_scenario}"
                        assert 'errors' in result, f"Result must have errors for {error_scenario}"
                        
                        # Error scenarios should result in invalid validation
                        assert not result['is_valid'], f"Should be invalid for {error_scenario}"
                        assert len(result['errors']) > 0, f"Should have errors for {error_scenario}"
                        
                        successful_validations += 1
                        
                except Exception as e:
                    pytest.fail(f"Startup validation crashed with {error_scenario}: {e}")
        
        # All validations should complete without crashing (error recovery)
        assert successful_validations == total_validations, \
            f"Expected {total_validations} successful validations, got {successful_validations}"
    
    @given(
        module_complexity=st.integers(min_value=1, max_value=20),
        pattern_complexity=st.sampled_from(['simple', 'complex', 'mixed', 'invalid'])
    )
    @settings(max_examples=25, deadline=6000)
    def test_property_startup_validation_scalability(self, module_complexity, pattern_complexity):
        """
        **Property 8: Startup Routing Validation (Scalability)**
        **Validates: Requirements 4.2, 4.4**
        
        Property: Startup validation must handle modules with varying complexity
        and pattern counts efficiently without performance degradation.
        """
        try:
            with patch('importlib.import_module') as mock_import:
                # Create mock module with specified complexity
                mock_module = Mock()
                patterns = self._create_patterns_by_complexity(pattern_complexity, module_complexity)
                mock_module.websocket_urlpatterns = patterns
                mock_import.return_value = mock_module
                
                # Measure validation performance (basic check)
                import time
                start_time = time.time()
                
                result = self.validator.validate_startup_routing('test.complex.routing')
                
                end_time = time.time()
                validation_time = end_time - start_time
                
                # Verify result structure
                assert isinstance(result, dict), "Result must be dictionary"
                assert 'is_valid' in result, "Result must have is_valid"
                assert 'patterns_found' in result, "Result must have patterns_found"
                
                # Verify pattern count matches
                assert result['patterns_found'] == len(patterns), "Pattern count should match"
                
                # Performance should be reasonable (allow generous time for property testing)
                max_allowed_time = 2.0 + (module_complexity * 0.1)  # Scale with complexity
                assert validation_time < max_allowed_time, \
                    f"Validation took {validation_time:.2f}s, max allowed {max_allowed_time:.2f}s"
                
                # Verify validation results based on pattern complexity
                if pattern_complexity == 'invalid':
                    assert not result['is_valid'], "Invalid patterns should result in invalid validation"
                elif pattern_complexity == 'simple':
                    # Simple patterns should generally be valid
                    pass  # Don't assert validity as it depends on specific patterns
                
        except Exception as e:
            pytest.fail(f"Startup validation scalability test raised exception: {e}")
    
    def _create_mock_module(self, scenario, pattern_count):
        """Create mock module based on scenario"""
        mock_module = Mock()
        
        if scenario == 'valid_module':
            patterns = []
            for i in range(pattern_count):
                pattern_mock = Mock()
                pattern_mock.pattern = Mock()
                pattern_mock.pattern.pattern = f'^ws/test{i}/$'
                pattern_mock.callback = Mock()
                patterns.append(pattern_mock)
            mock_module.websocket_urlpatterns = patterns
            
        elif scenario == 'module_without_patterns':
            # Module exists but has no websocket_urlpatterns attribute
            if hasattr(mock_module, 'websocket_urlpatterns'):
                delattr(mock_module, 'websocket_urlpatterns')
                
        elif scenario == 'module_with_invalid_patterns':
            # Module has patterns but they're malformed
            patterns = []
            for i in range(pattern_count):
                pattern_mock = Mock()
                pattern_mock.pattern = Mock()
                pattern_mock.pattern.pattern = f'ws/invalid{i}/\\n$'  # Malformed pattern
                pattern_mock.callback = Mock()
                patterns.append(pattern_mock)
            mock_module.websocket_urlpatterns = patterns
            
        elif scenario == 'module_with_mixed_patterns':
            # Module has mix of valid and invalid patterns
            patterns = []
            for i in range(pattern_count):
                pattern_mock = Mock()
                pattern_mock.pattern = Mock()
                if i % 2 == 0:
                    pattern_mock.pattern.pattern = f'^ws/valid{i}/$'  # Valid
                else:
                    pattern_mock.pattern.pattern = f'ws/invalid{i}/\\n'  # Invalid
                pattern_mock.callback = Mock()
                patterns.append(pattern_mock)
            mock_module.websocket_urlpatterns = patterns
        
        return mock_module
    
    def _create_patterns_by_complexity(self, complexity, count):
        """Create patterns based on complexity level"""
        patterns = []
        
        for i in range(count):
            pattern_mock = Mock()
            pattern_mock.pattern = Mock()
            pattern_mock.callback = Mock()
            
            if complexity == 'simple':
                pattern_mock.pattern.pattern = f'^ws/simple{i}/$'
            elif complexity == 'complex':
                pattern_mock.pattern.pattern = f'^ws/complex/(?P<id>\\d+)/(?P<name>[a-zA-Z0-9_-]+)/action{i}/$'
            elif complexity == 'mixed':
                if i % 2 == 0:
                    pattern_mock.pattern.pattern = f'^ws/simple{i}/$'
                else:
                    pattern_mock.pattern.pattern = f'^ws/complex/(?P<id>\\d+)/action{i}/$'
            elif complexity == 'invalid':
                pattern_mock.pattern.pattern = f'ws/invalid{i}/\\n$'  # Malformed
            
            patterns.append(pattern_mock)
        
        return patterns
    
    def test_successful_startup_validation(self):
        """Test successful startup validation with valid patterns"""
        with patch('importlib.import_module') as mock_import:
            mock_module = Mock()
            mock_module.websocket_urlpatterns = [
                Mock(pattern=Mock(pattern=r'^ws/chat/(?P<username>[^/]+)/$'), callback=Mock()),
                Mock(pattern=Mock(pattern=r'^ws/notifications/$'), callback=Mock()),
            ]
            mock_import.return_value = mock_module
            
            result = self.validator.validate_startup_routing('messaging.routing')
            
            assert result['is_valid'], f"Should be valid: {result['errors']}"
            assert result['module_loaded'], "Module should be loaded"
            assert result['patterns_found'] == 2, "Should find 2 patterns"
            assert len(result['errors']) == 0, "Should have no errors"
    
    def test_failed_startup_validation_missing_module(self):
        """Test startup validation with missing module"""
        with patch('importlib.import_module') as mock_import:
            mock_import.side_effect = ImportError("No module named 'nonexistent'")
            
            result = self.validator.validate_startup_routing('nonexistent.routing')
            
            assert not result['is_valid'], "Should be invalid for missing module"
            assert not result['module_loaded'], "Module should not be loaded"
            assert len(result['errors']) > 0, "Should have errors"
            assert any('import' in error.lower() for error in result['errors']), "Should mention import error"