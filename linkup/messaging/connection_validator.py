"""
Connection data validation for messaging system WebSocket connections
"""
from typing import Any, Dict, Optional, Union, List
from django.contrib.auth import get_user_model
from .logging_utils import MessagingLogger

User = get_user_model()


class ConnectionValidator:
    """Validator for WebSocket connection data and safe attribute access"""
    
    def __init__(self):
        self.logger = MessagingLogger()
    
    def validate_connection_scope(self, scope: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate WebSocket connection scope data structure
        
        Args:
            scope: WebSocket connection scope dictionary
            
        Returns:
            Dictionary with validation results and safe data access
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'user': None,
            'url_route': {},
            'headers': {},
            'query_string': '',
        }
        
        try:
            # Validate scope is a dictionary
            if not isinstance(scope, dict):
                validation_result['is_valid'] = False
                validation_result['errors'].append('Scope is not a dictionary')
                self.logger.log_connection_error(
                    'Invalid scope type',
                    context_data={'scope_type': type(scope).__name__}
                )
                return validation_result
            
            # Safely extract user
            user = self.safe_get_user(scope)
            validation_result['user'] = user
            
            if user is None:
                validation_result['is_valid'] = False
                validation_result['errors'].append('No authenticated user found')
            
            # Safely extract URL route information
            url_route = self.safe_get_url_route(scope)
            validation_result['url_route'] = url_route
            
            # Safely extract headers
            headers = self.safe_get_headers(scope)
            validation_result['headers'] = headers
            
            # Safely extract query string
            query_string = self.safe_get_query_string(scope)
            validation_result['query_string'] = query_string
            
            return validation_result
            
        except Exception as e:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f'Validation error: {str(e)}')
            self.logger.log_connection_error(
                f'Connection scope validation failed: {e}',
                context_data={'scope_keys': list(scope.keys()) if isinstance(scope, dict) else 'not_dict'}
            )
            return validation_result
    
    def safe_get_user(self, scope: Dict[str, Any]) -> Optional[User]:
        """
        Safely extract user from connection scope
        
        Args:
            scope: WebSocket connection scope
            
        Returns:
            User instance or None if not found/invalid
        """
        try:
            user = scope.get('user')
            
            if user is None:
                return None
            
            # Check if user is authenticated
            if not hasattr(user, 'is_authenticated') or not user.is_authenticated:
                self.logger.log_debug(
                    'User not authenticated in connection scope',
                    context_data={'user_id': getattr(user, 'id', None)}
                )
                return None
            
            # Validate user is active
            if hasattr(user, 'is_active') and not user.is_active:
                self.logger.log_debug(
                    'Inactive user in connection scope',
                    context_data={'user_id': user.id}
                )
                return None
            
            return user
            
        except Exception as e:
            self.logger.log_connection_error(
                f'Error extracting user from scope: {e}',
                context_data={'scope_has_user': 'user' in scope if isinstance(scope, dict) else False}
            )
            return None
    
    def safe_get_url_route(self, scope: Dict[str, Any]) -> Dict[str, Any]:
        """
        Safely extract URL route information from connection scope
        
        Args:
            scope: WebSocket connection scope
            
        Returns:
            Dictionary with URL route information
        """
        try:
            url_route = scope.get('url_route', {})
            
            if not isinstance(url_route, dict):
                self.logger.log_connection_error(
                    'URL route is not a dictionary',
                    context_data={'url_route_type': type(url_route).__name__}
                )
                return {}
            
            # Safely extract kwargs
            kwargs = url_route.get('kwargs', {})
            if not isinstance(kwargs, dict):
                self.logger.log_connection_error(
                    'URL route kwargs is not a dictionary',
                    context_data={'kwargs_type': type(kwargs).__name__}
                )
                kwargs = {}
            
            return {
                'kwargs': kwargs,
                'args': url_route.get('args', []),
                'route': url_route.get('route'),
                'app_name': url_route.get('app_name'),
                'url_name': url_route.get('url_name'),
            }
            
        except Exception as e:
            self.logger.log_connection_error(
                f'Error extracting URL route from scope: {e}',
                context_data={'scope_has_url_route': 'url_route' in scope if isinstance(scope, dict) else False}
            )
            return {}
    
    def safe_get_headers(self, scope: Dict[str, Any]) -> Dict[str, str]:
        """
        Safely extract headers from connection scope
        
        Args:
            scope: WebSocket connection scope
            
        Returns:
            Dictionary with header information
        """
        try:
            headers = scope.get('headers', [])
            
            if not isinstance(headers, (list, tuple)):
                self.logger.log_connection_error(
                    'Headers is not a list or tuple',
                    context_data={'headers_type': type(headers).__name__}
                )
                return {}
            
            # Convert headers list to dictionary
            header_dict = {}
            for header_item in headers:
                try:
                    if isinstance(header_item, (list, tuple)) and len(header_item) >= 2:
                        key = header_item[0]
                        value = header_item[1]
                        
                        # Convert bytes to string if needed
                        if isinstance(key, bytes):
                            key = key.decode('utf-8', errors='ignore')
                        if isinstance(value, bytes):
                            value = value.decode('utf-8', errors='ignore')
                        
                        header_dict[str(key)] = str(value)
                        
                except Exception as header_error:
                    self.logger.log_debug(
                        f'Error processing header item: {header_error}',
                        context_data={'header_item': str(header_item)}
                    )
                    continue
            
            return header_dict
            
        except Exception as e:
            self.logger.log_connection_error(
                f'Error extracting headers from scope: {e}',
                context_data={'scope_has_headers': 'headers' in scope if isinstance(scope, dict) else False}
            )
            return {}
    
    def safe_get_query_string(self, scope: Dict[str, Any]) -> str:
        """
        Safely extract query string from connection scope
        
        Args:
            scope: WebSocket connection scope
            
        Returns:
            Query string as string
        """
        try:
            query_string = scope.get('query_string', b'')
            
            if isinstance(query_string, bytes):
                return query_string.decode('utf-8', errors='ignore')
            elif isinstance(query_string, str):
                return query_string
            else:
                self.logger.log_debug(
                    'Query string is not bytes or string',
                    context_data={'query_string_type': type(query_string).__name__}
                )
                return str(query_string)
                
        except Exception as e:
            self.logger.log_connection_error(
                f'Error extracting query string from scope: {e}',
                context_data={'scope_has_query_string': 'query_string' in scope if isinstance(scope, dict) else False}
            )
            return ''
    
    def validate_message_data(self, data: Any) -> Dict[str, Any]:
        """
        Validate incoming WebSocket message data
        
        Args:
            data: Raw message data from WebSocket
            
        Returns:
            Dictionary with validation results and parsed data
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'message_type': None,
            'content': None,
            'parsed_data': {},
        }
        
        try:
            # Check if data is a dictionary
            if not isinstance(data, dict):
                validation_result['is_valid'] = False
                validation_result['errors'].append('Message data is not a dictionary')
                self.logger.log_connection_error(
                    'Invalid message data type',
                    context_data={'data_type': type(data).__name__}
                )
                return validation_result
            
            # Safely extract message type
            message_type = self.safe_get_string_field(data, 'type', 'message')
            validation_result['message_type'] = message_type
            validation_result['parsed_data']['type'] = message_type
            
            # Validate message type
            valid_types = ['message', 'typing', 'read_receipt', 'ping', 'mark_read', 'mark_all_read', 'get_notifications', 'get_connection_status', 'bulk_read_receipt', 'mark_chat_read', 'force_reconnect', 'sync_request']
            if message_type not in valid_types:
                validation_result['errors'].append(f'Invalid message type: {message_type}')
                self.logger.log_connection_error(
                    f'Invalid message type received: {message_type}',
                    context_data={'valid_types': valid_types}
                )
            
            # Extract and validate content based on message type
            if message_type == 'message':
                content = self.safe_get_string_field(data, 'message')
                if not content:
                    validation_result['errors'].append('Message content is required for message type')
                validation_result['content'] = content
                validation_result['parsed_data']['message'] = content
                validation_result['parsed_data']['retry_id'] = self.safe_get_string_field(data, 'retry_id')
                
            elif message_type == 'typing':
                validation_result['parsed_data']['is_typing'] = self.safe_get_boolean_field(data, 'is_typing', False)
                
            elif message_type == 'read_receipt':
                message_id = self.safe_get_integer_field(data, 'message_id')
                if message_id is None:
                    validation_result['errors'].append('Message ID is required for read receipt')
                validation_result['parsed_data']['message_id'] = message_id
                
            elif message_type == 'ping':
                validation_result['parsed_data']['timestamp'] = self.safe_get_string_field(data, 'timestamp')
                
            elif message_type in ['mark_read', 'get_notifications']:
                validation_result['parsed_data']['notification_id'] = self.safe_get_integer_field(data, 'notification_id')
                validation_result['parsed_data']['limit'] = self.safe_get_integer_field(data, 'limit', 20)
                validation_result['parsed_data']['offset'] = self.safe_get_integer_field(data, 'offset', 0)
                validation_result['parsed_data']['unread_only'] = self.safe_get_boolean_field(data, 'unread_only', False)
                validation_result['parsed_data']['notification_type'] = self.safe_get_string_field(data, 'notification_type')
            
            # If there are errors, mark as invalid
            if validation_result['errors']:
                validation_result['is_valid'] = False
            
            return validation_result
            
        except Exception as e:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f'Message validation error: {str(e)}')
            self.logger.log_connection_error(
                f'Message data validation failed: {e}',
                context_data={'data_keys': list(data.keys()) if isinstance(data, dict) else 'not_dict'}
            )
            return validation_result
    
    def safe_get_string_field(self, data: Dict[str, Any], field_name: str, default: Optional[str] = None) -> Optional[str]:
        """Safely extract string field from data dictionary"""
        try:
            value = data.get(field_name, default)
            if value is None:
                return None
            return str(value).strip() if str(value).strip() else None
        except Exception as e:
            self.logger.log_debug(f'Error extracting string field {field_name}: {e}')
            return default
    
    def safe_get_integer_field(self, data: Dict[str, Any], field_name: str, default: Optional[int] = None) -> Optional[int]:
        """Safely extract integer field from data dictionary"""
        try:
            value = data.get(field_name, default)
            if value is None:
                return None
            return int(value)
        except (ValueError, TypeError) as e:
            self.logger.log_debug(f'Error extracting integer field {field_name}: {e}')
            return default
    
    def safe_get_boolean_field(self, data: Dict[str, Any], field_name: str, default: bool = False) -> bool:
        """Safely extract boolean field from data dictionary"""
        try:
            value = data.get(field_name, default)
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes', 'on')
            return bool(value)
        except Exception as e:
            self.logger.log_debug(f'Error extracting boolean field {field_name}: {e}')
            return default
    
    def safe_get(self, data: Dict[str, Any], field_name: str, default: Any = None) -> Any:
        """Safely extract any field from data dictionary with fallback"""
        try:
            if not isinstance(data, dict):
                self.logger.log_debug(f'Data is not a dictionary when accessing {field_name}')
                return default
            return data.get(field_name, default)
        except Exception as e:
            self.logger.log_debug(f'Error extracting field {field_name}: {e}')
            return default
    
    def generate_error_response(self, errors: List[str], message_type: str = 'error') -> Dict[str, Any]:
        """
        Generate standardized error response for WebSocket
        
        Args:
            errors: List of error messages
            message_type: Type of error response
            
        Returns:
            Dictionary with error response data
        """
        try:
            return {
                'type': message_type,
                'error': True,
                'errors': errors,
                'message': '; '.join(errors) if errors else 'Unknown error occurred',
                'timestamp': self._get_current_timestamp(),
            }
        except Exception as e:
            self.logger.log_connection_error(f'Error generating error response: {e}')
            return {
                'type': 'error',
                'error': True,
                'message': 'Error processing request',
            }
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        try:
            from django.utils import timezone
            return timezone.now().isoformat()
        except Exception:
            import datetime
            return datetime.datetime.now().isoformat()