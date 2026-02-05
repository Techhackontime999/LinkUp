"""
Routing pattern validation for WebSocket URL patterns
"""
import re
from typing import List, Dict, Any, Optional, Tuple
from django.urls import re_path
from django.core.exceptions import ImproperlyConfigured
from .logging_utils import MessagingLogger


class RoutingValidator:
    """Validator for WebSocket routing patterns and startup validation"""
    
    def __init__(self):
        self.logger = MessagingLogger()
        self.validated_patterns = []
        self.validation_errors = []
    
    def validate_regex_pattern(self, pattern: str, pattern_name: str = None) -> Dict[str, Any]:
        """
        Validate a single regex pattern for syntax correctness
        
        Args:
            pattern: Regex pattern string to validate
            pattern_name: Optional name for the pattern (for error reporting)
            
        Returns:
            Dictionary with validation results
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'pattern': pattern,
            'pattern_name': pattern_name or 'unnamed',
            'compiled_pattern': None,
        }
        
        try:
            # Check if pattern is a string
            if not isinstance(pattern, str):
                validation_result['is_valid'] = False
                validation_result['errors'].append(f'Pattern must be a string, got {type(pattern).__name__}')
                return validation_result
            
            # Check for empty pattern
            if not pattern.strip():
                validation_result['is_valid'] = False
                validation_result['errors'].append('Pattern cannot be empty')
                return validation_result
            
            # Check for common malformed patterns
            malformed_issues = self._check_malformed_patterns(pattern)
            if malformed_issues:
                validation_result['is_valid'] = False
                validation_result['errors'].extend(malformed_issues)
            
            # Attempt to compile the regex pattern
            try:
                compiled_pattern = re.compile(pattern)
                validation_result['compiled_pattern'] = compiled_pattern
                
                # Additional validation for WebSocket patterns
                websocket_issues = self._validate_websocket_pattern(pattern, compiled_pattern)
                if websocket_issues:
                    validation_result['errors'].extend(websocket_issues)
                    if any('critical' in issue.lower() for issue in websocket_issues):
                        validation_result['is_valid'] = False
                
            except re.error as e:
                validation_result['is_valid'] = False
                validation_result['errors'].append(f'Regex compilation error: {str(e)}')
                self.logger.log_routing_error(
                    f'Regex pattern compilation failed for {pattern_name}: {e}',
                    context_data={'pattern': pattern, 'error': str(e)}
                )
            
            # Log validation result
            if not validation_result['is_valid']:
                self.logger.log_routing_error(
                    f'Pattern validation failed for {pattern_name}',
                    context_data={
                        'pattern': pattern,
                        'errors': validation_result['errors']
                    }
                )
            else:
                self.logger.log_debug(
                    f'Pattern validation successful for {pattern_name}',
                    context_data={'pattern': pattern}
                )
            
            return validation_result
            
        except Exception as e:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f'Validation error: {str(e)}')
            self.logger.log_routing_error(
                f'Pattern validation exception for {pattern_name}: {e}',
                context_data={'pattern': pattern}
            )
            return validation_result
    
    def _check_malformed_patterns(self, pattern: str) -> List[str]:
        """Check for common malformed pattern issues"""
        issues = []
        
        # Check for line breaks in pattern (common issue)
        if '\n' in pattern or '\r' in pattern:
            issues.append('Pattern contains line breaks - regex patterns must be on single line')
        
        # Check for unmatched parentheses
        open_parens = pattern.count('(')
        close_parens = pattern.count(')')
        if open_parens != close_parens:
            issues.append(f'Unmatched parentheses: {open_parens} open, {close_parens} close')
        
        # Check for unmatched brackets
        open_brackets = pattern.count('[')
        close_brackets = pattern.count(']')
        if open_brackets != close_brackets:
            issues.append(f'Unmatched brackets: {open_brackets} open, {close_brackets} close')
        
        # Check for unmatched braces
        open_braces = pattern.count('{')
        close_braces = pattern.count('}')
        if open_braces != close_braces:
            issues.append(f'Unmatched braces: {open_braces} open, {close_braces} close')
        
        # Check for incomplete escape sequences
        if pattern.endswith('\\'):
            issues.append('Pattern ends with incomplete escape sequence')
        
        # Check for common WebSocket pattern issues
        if 'ws/' in pattern and not pattern.startswith('^'):
            issues.append('WebSocket patterns should typically start with ^ anchor')
        
        if 'ws/' in pattern and not pattern.endswith('$'):
            issues.append('WebSocket patterns should typically end with $ anchor')
        
        return issues
    
    def _validate_websocket_pattern(self, pattern: str, compiled_pattern: re.Pattern) -> List[str]:
        """Validate WebSocket-specific pattern requirements"""
        issues = []
        
        try:
            # Check if pattern matches expected WebSocket URLs
            test_urls = [
                'ws/chat/testuser/',
                'ws/notifications/',
                'ws/chat/user123/',
                'ws/notifications/user456/',
            ]
            
            matches_found = 0
            for test_url in test_urls:
                if compiled_pattern.match(test_url):
                    matches_found += 1
            
            # Pattern should match at least some test URLs if it's a WebSocket pattern
            if 'ws/' in pattern and matches_found == 0:
                issues.append('Pattern does not match any expected WebSocket URLs')
            
            # Check for named groups in patterns that should have them
            if 'chat' in pattern and '(?P<username>' not in pattern:
                issues.append('Chat patterns should include named username group: (?P<username>...)')
            
            # Check for proper URL ending
            if 'ws/' in pattern and not ('/$' in pattern or '/?' in pattern):
                issues.append('WebSocket patterns should handle trailing slash properly')
            
        except Exception as e:
            issues.append(f'WebSocket pattern validation error: {str(e)}')
        
        return issues
    
    def validate_routing_patterns(self, patterns: List[Tuple[str, Any]]) -> Dict[str, Any]:
        """
        Validate a list of routing patterns
        
        Args:
            patterns: List of (pattern, consumer) tuples
            
        Returns:
            Dictionary with overall validation results
        """
        validation_result = {
            'is_valid': True,
            'total_patterns': len(patterns),
            'valid_patterns': 0,
            'invalid_patterns': 0,
            'pattern_results': [],
            'errors': [],
        }
        
        try:
            for i, pattern_tuple in enumerate(patterns):
                try:
                    if not isinstance(pattern_tuple, (list, tuple)) or len(pattern_tuple) < 2:
                        validation_result['errors'].append(f'Pattern {i}: Invalid pattern tuple structure')
                        validation_result['invalid_patterns'] += 1
                        continue
                    
                    pattern = pattern_tuple[0]
                    consumer = pattern_tuple[1]
                    
                    # Extract pattern string from re_path object if needed
                    if hasattr(pattern, 'pattern'):
                        pattern_str = pattern.pattern.pattern if hasattr(pattern.pattern, 'pattern') else str(pattern.pattern)
                        pattern_name = f'pattern_{i}'
                    else:
                        pattern_str = str(pattern)
                        pattern_name = f'pattern_{i}'
                    
                    # Validate individual pattern
                    pattern_result = self.validate_regex_pattern(pattern_str, pattern_name)
                    pattern_result['consumer'] = str(consumer)
                    validation_result['pattern_results'].append(pattern_result)
                    
                    if pattern_result['is_valid']:
                        validation_result['valid_patterns'] += 1
                    else:
                        validation_result['invalid_patterns'] += 1
                        validation_result['errors'].extend([
                            f"{pattern_name}: {error}" for error in pattern_result['errors']
                        ])
                
                except Exception as e:
                    validation_result['invalid_patterns'] += 1
                    validation_result['errors'].append(f'Pattern {i}: Validation exception: {str(e)}')
                    self.logger.log_routing_error(
                        f'Pattern validation exception for pattern {i}: {e}',
                        context_data={'pattern_index': i}
                    )
            
            # Overall validation fails if any patterns are invalid
            if validation_result['invalid_patterns'] > 0:
                validation_result['is_valid'] = False
            
            # Log overall results
            self.logger.log_info(
                f'Routing validation completed: {validation_result["valid_patterns"]}/{validation_result["total_patterns"]} patterns valid',
                context_data={
                    'valid_patterns': validation_result['valid_patterns'],
                    'invalid_patterns': validation_result['invalid_patterns'],
                    'total_patterns': validation_result['total_patterns']
                }
            )
            
            return validation_result
            
        except Exception as e:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f'Routing validation error: {str(e)}')
            self.logger.log_routing_error(f'Routing validation failed: {e}')
            return validation_result
    
    def validate_startup_routing(self, routing_module_path: str = 'messaging.routing') -> Dict[str, Any]:
        """
        Validate routing patterns at application startup
        
        Args:
            routing_module_path: Path to routing module to validate
            
        Returns:
            Dictionary with startup validation results
        """
        validation_result = {
            'is_valid': True,
            'module_loaded': False,
            'patterns_found': 0,
            'validation_results': {},
            'errors': [],
        }
        
        try:
            # Import the routing module
            import importlib
            routing_module = importlib.import_module(routing_module_path)
            validation_result['module_loaded'] = True
            
            # Get websocket_urlpatterns
            if hasattr(routing_module, 'websocket_urlpatterns'):
                patterns = routing_module.websocket_urlpatterns
                validation_result['patterns_found'] = len(patterns)
                
                # Validate the patterns
                pattern_validation = self.validate_routing_patterns(patterns)
                validation_result['validation_results'] = pattern_validation
                
                if not pattern_validation['is_valid']:
                    validation_result['is_valid'] = False
                    validation_result['errors'].extend(pattern_validation['errors'])
                
            else:
                validation_result['is_valid'] = False
                validation_result['errors'].append('No websocket_urlpatterns found in routing module')
            
            # Log startup validation results
            if validation_result['is_valid']:
                self.logger.log_info(
                    f'Startup routing validation successful for {routing_module_path}',
                    context_data={'patterns_found': validation_result['patterns_found']}
                )
            else:
                self.logger.log_routing_error(
                    f'Startup routing validation failed for {routing_module_path}',
                    context_data={
                        'errors': validation_result['errors'],
                        'patterns_found': validation_result['patterns_found']
                    }
                )
            
            return validation_result
            
        except ImportError as e:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f'Could not import routing module {routing_module_path}: {str(e)}')
            self.logger.log_routing_error(f'Routing module import failed: {e}')
            return validation_result
            
        except Exception as e:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f'Startup validation error: {str(e)}')
            self.logger.log_routing_error(f'Startup routing validation failed: {e}')
            return validation_result
    
    def generate_corrected_pattern(self, malformed_pattern: str) -> str:
        """
        Generate a corrected version of a malformed pattern
        
        Args:
            malformed_pattern: The malformed regex pattern
            
        Returns:
            Corrected pattern string
        """
        try:
            corrected = malformed_pattern
            
            # Remove line breaks and extra whitespace
            corrected = re.sub(r'\s*\n\s*', '', corrected)
            corrected = corrected.strip()
            
            # Add anchors if missing for WebSocket patterns
            if 'ws/' in corrected:
                if not corrected.startswith('^'):
                    corrected = '^' + corrected
                if not corrected.endswith('$'):
                    corrected = corrected + '$'
            
            # Fix common pattern issues
            if 'ws/chat/' in corrected and '(?P<username>' not in corrected:
                corrected = corrected.replace('ws/chat/', 'ws/chat/(?P<username>[^/]+)/')
            
            self.logger.log_info(
                f'Generated corrected pattern',
                context_data={
                    'original': malformed_pattern,
                    'corrected': corrected
                }
            )
            
            return corrected
            
        except Exception as e:
            self.logger.log_routing_error(f'Pattern correction failed: {e}')
            return malformed_pattern
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get summary of all validation results"""
        return {
            'validated_patterns': len(self.validated_patterns),
            'validation_errors': len(self.validation_errors),
            'patterns': self.validated_patterns,
            'errors': self.validation_errors,
        }