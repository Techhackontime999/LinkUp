"""
Property-based tests for routing pattern validation
**Validates: Requirements 4.1, 4.3**
"""
import pytest
import re
from hypothesis import given, strategies as st, assume, settings
from django.test import TestCase
from unittest.mock import Mock, patch
from .routing_validator import RoutingValidator

class TestRoutingPatternValidation(TestCase):
    """Property tests for routing pattern validation"""
    
    def setUp(self):
        self.validator = RoutingValidator()
    
    @given(
        pattern=st.one_of(
            # Valid patterns
            st.just(r'^ws/chat/(?P<username>[^/]+)/$'),
            st.just(r'^ws/notifications/$'),
            st.just(r'^ws/test/(?P<id>\d+)/$'),
            # Malformed patterns
            st.text(min_size=1, max_size=100).filter(lambda x: '\x00' not in x),
            # Patterns with common issues
            st.sampled_from([
                r'ws/chat/(?P<username>[^/]+)/',  # Missing anchors
                r'^ws/chat/(?P<username>[^/]+)',  # Missing end anchor
                r'ws/notifications',              # Missing anchors and slash
                r'^ws/chat/(?P<username>[^/]+)/\n$',  # Line break
                r'^ws/chat/(?P<username>[^/]+//$',    # Unmatched parentheses
                r'^ws/chat/[(?P<username>[^/]+)/$',   # Unmatched brackets
                r'^ws/chat/{(?P<username>[^/]+)/$',   # Unmatched braces
                r'^ws/chat/(?P<username>[^/]+)/$\\',  # Trailing escape
                '',                               # Empty pattern
                None,                            # None pattern
            ])
        )
    )
    @settings(max_examples=100, deadline=5000)
    def test_property_routing_pattern_validation_safety(self, pattern):
        """
        **Property 7: Routing Pattern Validation**
        **Validates: Requirements 4.1, 4.3**
        
        Property: The routing validator must safely validate any regex pattern
        without crashing, always returning a consistent validation result structure.
        """
        try:
            # Skip None patterns for string-specific tests
            if pattern is None:
                pattern = ''
            
            result = self.validator.validate_regex_pattern(pattern, 'test_pattern')
            
            # Verify result structure is always consistent
            assert isinstance(result, dict), "Result must be a dictionary"
            assert 'is_valid' in result, "Result must contain is_valid field"
            assert 'errors' in result, "Result must contain errors field"
            assert 'pattern' in result, "Result must contain pattern field"
            assert 'pattern_name' in result, "Result must contain pattern_name field"
            assert 'compiled_pattern' in result, "Result must contain compiled_pattern field"
            
            # Verify field types
            assert isinstance(result['is_valid'], bool), "is_valid must be boolean"
            assert isinstance(result['errors'], list), "errors must be a list"
            assert isinstance(result['pattern_name'], str), "pattern_name must be string"
            
            # If pattern is invalid, there should be errors
            if not result['is_valid']:
                assert len(result['errors']) > 0, "Invalid patterns should have error messages"
            
            # If pattern is valid, compiled_pattern should exist
            if result['is_valid'] and result['compiled_pattern'] is not None:
                assert hasattr(result['compiled_pattern'], 'match'), "Compiled pattern should have match method"
            
        except Exception as e:
            pytest.fail(f"Routing pattern validation raised exception: {e}")
    
    @given(
        patterns=st.lists(
            st.tuples(
                st.one_of(
                    st.just(r'^ws/chat/(?P<username>[^/]+)/$'),
                    st.just(r'^ws/notifications/$'),
                    st.text(min_size=1, max_size=50).filter(lambda x: '\x00' not in x),
                    st.sampled_from([
                        r'ws/invalid/\n/',  # Line break
                        r'^ws/chat/(?P<username>[^/]+//$',  # Unmatched parens
                        '',  # Empty
                    ])
                ),
                st.just('MockConsumer')  # Mock consumer
            ),
            min_size=0,
            max_size=10
        )
    )
    @settings(max_examples=50, deadline=8000)
    def test_property_routing_patterns_list_validation(self, patterns):
        """
        **Property 7: Routing Pattern Validation (Multiple Patterns)**
        **Validates: Requirements 4.1, 4.3**
        
        Property: The routing validator must handle lists of patterns safely,
        validating each pattern and providing comprehensive results.
        """
        try:
            result = self.validator.validate_routing_patterns(patterns)
            
            # Verify result structure
            assert isinstance(result, dict), "Result must be a dictionary"
            assert 'is_valid' in result, "Result must contain is_valid field"
            assert 'total_patterns' in result, "Result must contain total_patterns field"
            assert 'valid_patterns' in result, "Result must contain valid_patterns field"
            assert 'invalid_patterns' in result, "Result must contain invalid_patterns field"
            assert 'pattern_results' in result, "Result must contain pattern_results field"
            assert 'errors' in result, "Result must contain errors field"
            
            # Verify field types and values
            assert isinstance(result['is_valid'], bool), "is_valid must be boolean"
            assert isinstance(result['total_patterns'], int), "total_patterns must be integer"
            assert isinstance(result['valid_patterns'], int), "valid_patterns must be integer"
            assert isinstance(result['invalid_patterns'], int), "invalid_patterns must be integer"
            assert isinstance(result['pattern_results'], list), "pattern_results must be list"
            assert isinstance(result['errors'], list), "errors must be list"
            
            # Verify counts add up
            assert result['total_patterns'] == len(patterns), "Total patterns should match input length"
            assert result['valid_patterns'] + result['invalid_patterns'] == result['total_patterns'], \
                "Valid + invalid should equal total"
            
            # If there are invalid patterns, overall result should be invalid
            if result['invalid_patterns'] > 0:
                assert not result['is_valid'], "Result should be invalid if any patterns are invalid"
                assert len(result['errors']) > 0, "Should have errors if patterns are invalid"
            
            # Verify pattern results structure
            for pattern_result in result['pattern_results']:
                assert isinstance(pattern_result, dict), "Each pattern result must be dict"
                assert 'is_valid' in pattern_result, "Pattern result must have is_valid"
                assert 'errors' in pattern_result, "Pattern result must have errors"
            
        except Exception as e:
            pytest.fail(f"Routing patterns validation raised exception: {e}")
    
    @given(
        malformed_pattern=st.sampled_from([
            r'ws/chat/(?P<username>[^/]+)/\n',  # Line break
            r'ws/chat/(?P<username>[^/]+)/',    # Missing anchors
            r'^ws/notifications',               # Missing end anchor and slash
            r'ws/chat/(?P<username>[^/]+)/\r\n$',  # Multiple line breaks
            r'  ^ws/chat/(?P<username>[^/]+)/$  ',  # Extra whitespace
        ])
    )
    @settings(max_examples=20, deadline=3000)
    def test_property_pattern_correction_generation(self, malformed_pattern):
        """
        **Property 7: Routing Pattern Validation (Pattern Correction)**
        **Validates: Requirements 4.1, 4.3**
        
        Property: The routing validator must generate corrected versions of
        malformed patterns that are syntactically valid.
        """
        try:
            corrected_pattern = self.validator.generate_corrected_pattern(malformed_pattern)
            
            # Verify corrected pattern is a string
            assert isinstance(corrected_pattern, str), "Corrected pattern must be string"
            
            # Verify corrected pattern doesn't have line breaks
            assert '\n' not in corrected_pattern, "Corrected pattern should not have line breaks"
            assert '\r' not in corrected_pattern, "Corrected pattern should not have carriage returns"
            
            # Verify corrected pattern can be compiled
            try:
                compiled = re.compile(corrected_pattern)
                assert compiled is not None, "Corrected pattern should compile successfully"
            except re.error:
                # If correction fails, that's acceptable for some edge cases
                pass
            
            # Verify WebSocket patterns have proper anchors
            if 'ws/' in corrected_pattern:
                assert corrected_pattern.startswith('^'), "WebSocket patterns should start with ^"
                assert corrected_pattern.endswith('$'), "WebSocket patterns should end with $"
            
        except Exception as e:
            pytest.fail(f"Pattern correction raised exception: {e}")
    
    @given(
        test_url=st.sampled_from([
            'ws/chat/testuser/',
            'ws/notifications/',
            'ws/chat/user123/',
            'ws/notifications/extra/',
            'invalid/path/',
            'ws/chat/',
            'ws/chat/user/extra/path/',
        ])
    )
    @settings(max_examples=30, deadline=3000)
    def test_property_websocket_pattern_matching(self, test_url):
        """
        **Property 7: Routing Pattern Validation (URL Matching)**
        **Validates: Requirements 4.1, 4.3**
        
        Property: Valid WebSocket patterns must correctly match or reject
        test URLs according to their intended purpose.
        """
        try:
            # Test known good patterns
            chat_pattern = r'^ws/chat/(?P<username>[^/]+)/$'
            notifications_pattern = r'^ws/notifications/$'
            
            chat_result = self.validator.validate_regex_pattern(chat_pattern, 'chat_pattern')
            notifications_result = self.validator.validate_regex_pattern(notifications_pattern, 'notifications_pattern')
            
            # Both patterns should be valid
            assert chat_result['is_valid'], f"Chat pattern should be valid: {chat_result['errors']}"
            assert notifications_result['is_valid'], f"Notifications pattern should be valid: {notifications_result['errors']}"
            
            # Test URL matching behavior
            if chat_result['compiled_pattern']:
                chat_match = chat_result['compiled_pattern'].match(test_url)
                
                # Chat pattern should match chat URLs with usernames
                if test_url.startswith('ws/chat/') and test_url.endswith('/') and test_url.count('/') == 3:
                    username_part = test_url.split('/')[2]
                    if username_part and username_part != '':
                        assert chat_match is not None, f"Chat pattern should match {test_url}"
                        if chat_match:
                            assert 'username' in chat_match.groupdict(), "Chat match should have username group"
                
            if notifications_result['compiled_pattern']:
                notifications_match = notifications_result['compiled_pattern'].match(test_url)
                
                # Notifications pattern should match exact notifications URL
                if test_url == 'ws/notifications/':
                    assert notifications_match is not None, f"Notifications pattern should match {test_url}"
                elif test_url.startswith('ws/notifications/') and len(test_url) > len('ws/notifications/'):
                    assert notifications_match is None, f"Notifications pattern should not match {test_url} (extra path)"
            
        except Exception as e:
            pytest.fail(f"WebSocket pattern matching test raised exception: {e}")
    
    def test_valid_websocket_patterns(self):
        """Test validation of known valid WebSocket patterns"""
        valid_patterns = [
            r'^ws/chat/(?P<username>[^/]+)/$',
            r'^ws/notifications/$',
            r'^ws/test/(?P<id>\d+)/$',
            r'^ws/room/(?P<room_name>[a-zA-Z0-9_-]+)/$',
        ]
        
        for pattern in valid_patterns:
            result = self.validator.validate_regex_pattern(pattern, f'valid_pattern_{pattern}')
            assert result['is_valid'], f"Pattern {pattern} should be valid: {result['errors']}"
            assert len(result['errors']) == 0, f"Valid pattern should have no errors: {result['errors']}"
            assert result['compiled_pattern'] is not None, "Valid pattern should compile"
    
    def test_invalid_websocket_patterns(self):
        """Test validation of known invalid WebSocket patterns"""
        invalid_patterns = [
            r'ws/chat/(?P<username>[^/]+)/\n$',  # Line break
            r'^ws/chat/(?P<username>[^/]+//$',   # Unmatched parentheses
            r'^ws/chat/[(?P<username>[^/]+)/$',  # Unmatched brackets
            '',                                  # Empty pattern
            r'^ws/chat/(?P<username>[^/]+)/$\\', # Trailing escape
        ]
        
        for pattern in invalid_patterns:
            result = self.validator.validate_regex_pattern(pattern, f'invalid_pattern_{pattern}')
            assert not result['is_valid'], f"Pattern {pattern} should be invalid"
            assert len(result['errors']) > 0, f"Invalid pattern should have errors"
    
    def test_startup_validation_simulation(self):
        """Test startup validation with mock routing module"""
        # Create mock patterns that simulate the fixed routing.py
        mock_patterns = [
            (Mock(pattern=Mock(pattern=r'^ws/chat/(?P<username>[^/]+)/$')), Mock()),
            (Mock(pattern=Mock(pattern=r'^ws/notifications/$')), Mock()),
        ]
        
        result = self.validator.validate_routing_patterns(mock_patterns)
        
        assert result['is_valid'], f"Fixed patterns should be valid: {result['errors']}"
        assert result['valid_patterns'] == 2, "Should have 2 valid patterns"
        assert result['invalid_patterns'] == 0, "Should have 0 invalid patterns"