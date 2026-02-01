"""
CSRF failure handling views for enhanced security.
"""

import logging
from django.shortcuts import render
from django.http import HttpResponseForbidden
from django.views.decorators.csrf import requires_csrf_token
from django.utils.translation import gettext as _

logger = logging.getLogger('django.security')


@requires_csrf_token
def csrf_failure(request, reason=""):
    """
    Custom CSRF failure view that provides better user experience
    and security logging.
    """
    
    # Log CSRF failure for security monitoring
    client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', 'unknown'))
    user_agent = request.META.get('HTTP_USER_AGENT', 'unknown')
    referer = request.META.get('HTTP_REFERER', 'unknown')
    
    logger.warning(
        f"CSRF failure - IP: {client_ip}, User-Agent: {user_agent}, "
        f"Referer: {referer}, Reason: {reason}, Path: {request.path}"
    )
    
    # Provide user-friendly error page
    context = {
        'title': _('Security Error'),
        'message': _('Your request could not be processed due to a security check failure.'),
        'suggestions': [
            _('Please refresh the page and try again.'),
            _('Make sure cookies are enabled in your browser.'),
            _('If the problem persists, please contact support.'),
        ],
        'reason': reason,
    }
    
    return render(
        request, 
        'core/csrf_failure.html', 
        context, 
        status=403
    )