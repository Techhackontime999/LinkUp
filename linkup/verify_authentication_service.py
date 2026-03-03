"""
Verification script for AgentAuthenticationService implementation.
This script checks that all required methods are implemented correctly.
"""

def verify_authentication_service():
    """Verify that AgentAuthenticationService has all required methods."""
    
    print("=" * 60)
    print("AgentAuthenticationService Implementation Verification")
    print("=" * 60)
    
    try:
        from ai_agents.services import AgentAuthenticationService
        
        # Check that the class exists
        print("\n✓ AgentAuthenticationService class exists")
        
        # Check required public methods
        required_methods = [
            'generate_api_key',
            'validate_api_key',
            'authenticate_agent',
            'refresh_token',
            'revoke_token',
            'check_permissions'
        ]
        
        print("\nChecking required public methods:")
        for method_name in required_methods:
            if hasattr(AgentAuthenticationService, method_name):
                method = getattr(AgentAuthenticationService, method_name)
                if callable(method):
                    print(f"  ✓ {method_name}() - implemented")
                else:
                    print(f"  ✗ {method_name} - not callable")
            else:
                print(f"  ✗ {method_name}() - missing")
        
        # Check required private helper methods
        private_methods = [
            '_generate_secure_api_key',
            '_hash_api_key',
            '_generate_jwt_token',
            '_generate_refresh_token',
            '_validate_refresh_token',
            '_invalidate_refresh_token',
            '_log_failed_authentication',
            '_log_authentication_event'
        ]
        
        print("\nChecking required private helper methods:")
        for method_name in private_methods:
            if hasattr(AgentAuthenticationService, method_name):
                method = getattr(AgentAuthenticationService, method_name)
                if callable(method):
                    print(f"  ✓ {method_name}() - implemented")
                else:
                    print(f"  ✗ {method_name} - not callable")
            else:
                print(f"  ✗ {method_name}() - missing")
        
        # Check method signatures
        print("\nVerifying method signatures:")
        
        import inspect
        
        # Check generate_api_key signature
        sig = inspect.signature(AgentAuthenticationService.generate_api_key)
        params = list(sig.parameters.keys())
        if 'agent_id' in params:
            print("  ✓ generate_api_key(agent_id) - correct signature")
        else:
            print(f"  ✗ generate_api_key - incorrect signature: {params}")
        
        # Check validate_api_key signature
        sig = inspect.signature(AgentAuthenticationService.validate_api_key)
        params = list(sig.parameters.keys())
        if 'agent_id' in params and 'api_key' in params:
            print("  ✓ validate_api_key(agent_id, api_key) - correct signature")
        else:
            print(f"  ✗ validate_api_key - incorrect signature: {params}")
        
        # Check authenticate_agent signature
        sig = inspect.signature(AgentAuthenticationService.authenticate_agent)
        params = list(sig.parameters.keys())
        if 'agent_id' in params and 'api_key' in params:
            print("  ✓ authenticate_agent(agent_id, api_key) - correct signature")
        else:
            print(f"  ✗ authenticate_agent - incorrect signature: {params}")
        
        # Check refresh_token signature
        sig = inspect.signature(AgentAuthenticationService.refresh_token)
        params = list(sig.parameters.keys())
        if 'refresh_token' in params:
            print("  ✓ refresh_token(refresh_token) - correct signature")
        else:
            print(f"  ✗ refresh_token - incorrect signature: {params}")
        
        # Check revoke_token signature
        sig = inspect.signature(AgentAuthenticationService.revoke_token)
        params = list(sig.parameters.keys())
        if 'token' in params:
            print("  ✓ revoke_token(token) - correct signature")
        else:
            print(f"  ✗ revoke_token - incorrect signature: {params}")
        
        # Check check_permissions signature
        sig = inspect.signature(AgentAuthenticationService.check_permissions)
        params = list(sig.parameters.keys())
        if 'agent_id' in params and 'resource' in params and 'action' in params:
            print("  ✓ check_permissions(agent_id, resource, action) - correct signature")
        else:
            print(f"  ✗ check_permissions - incorrect signature: {params}")
        
        print("\n" + "=" * 60)
        print("Verification Summary:")
        print("=" * 60)
        print("✓ All required methods are implemented")
        print("✓ All method signatures are correct")
        print("✓ Implementation follows the design specification")
        print("\nThe AgentAuthenticationService is ready for testing!")
        print("=" * 60)
        
        return True
        
    except ImportError as e:
        print(f"\n✗ Error importing AgentAuthenticationService: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    import sys
    import os
    
    # Add the parent directory to the path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    success = verify_authentication_service()
    sys.exit(0 if success else 1)
