/**
 * CSRF Token Management Utilities
 * Provides functions for handling CSRF tokens in AJAX requests and forms
 */

class CSRFManager {
    constructor() {
        this.token = this.getTokenFromCookie();
        this.setupAjaxDefaults();
        this.setupAutoRefresh();
    }

    /**
     * Get CSRF token from cookie
     */
    getTokenFromCookie() {
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    /**
     * Get CSRF token from meta tag
     */
    getTokenFromMeta() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : null;
    }

    /**
     * Get current CSRF token (try cookie first, then meta tag)
     */
    getToken() {
        return this.getTokenFromCookie() || this.getTokenFromMeta();
    }

    /**
     * Update CSRF token in all forms
     */
    updateFormsToken(newToken) {
        document.querySelectorAll('input[name="csrfmiddlewaretoken"]').forEach(input => {
            input.value = newToken;
        });
        this.token = newToken;
    }

    /**
     * Setup default AJAX headers for CSRF protection
     */
    setupAjaxDefaults() {
        // jQuery setup
        if (window.jQuery) {
            const self = this;
            $.ajaxSetup({
                beforeSend: function(xhr, settings) {
                    if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                        xhr.setRequestHeader("X-CSRFToken", self.getToken());
                    }
                }
            });
        }

        // Fetch API setup
        const originalFetch = window.fetch;
        window.fetch = function(url, options = {}) {
            if (options.method && !/^(GET|HEAD|OPTIONS|TRACE)$/i.test(options.method)) {
                options.headers = options.headers || {};
                options.headers['X-CSRFToken'] = csrfManager.getToken();
            }
            return originalFetch(url, options);
        };
    }

    /**
     * Setup automatic token refresh
     */
    setupAutoRefresh() {
        // Refresh token every 30 minutes
        setInterval(() => {
            this.refreshToken();
        }, 30 * 60 * 1000);

        // Refresh token when page becomes visible (user returns to tab)
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                this.refreshToken();
            }
        });
    }

    /**
     * Refresh CSRF token from server
     */
    async refreshToken() {
        try {
            const response = await fetch('/csrf-token-refresh/', {
                method: 'GET',
                credentials: 'same-origin'
            });

            if (response.ok) {
                const data = await response.json();
                if (data.csrf_token) {
                    this.updateFormsToken(data.csrf_token);
                    console.log('CSRF token refreshed successfully');
                }
            }
        } catch (error) {
            console.warn('Failed to refresh CSRF token:', error);
        }
    }

    /**
     * Handle CSRF failure in AJAX requests
     */
    handleCSRFFailure(xhr) {
        if (xhr.status === 403 && xhr.responseJSON && xhr.responseJSON.code === 'csrf_failure') {
            // Show user-friendly error message
            this.showCSRFError(xhr.responseJSON.message);
            
            // Try to refresh token
            this.refreshToken();
            
            return true; // Indicates CSRF failure was handled
        }
        return false;
    }

    /**
     * Show CSRF error message to user
     */
    showCSRFError(message) {
        // Create or update error notification
        let errorDiv = document.getElementById('csrf-error-notification');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.id = 'csrf-error-notification';
            errorDiv.className = 'fixed top-4 right-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded shadow-lg z-50';
            document.body.appendChild(errorDiv);
        }

        errorDiv.innerHTML = `
            <div class="flex items-center">
                <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
                </svg>
                <span>${message}</span>
                <button onclick="this.parentElement.parentElement.remove()" class="ml-4 text-red-500 hover:text-red-700">
                    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>
                    </svg>
                </button>
            </div>
        `;

        // Auto-hide after 10 seconds
        setTimeout(() => {
            if (errorDiv.parentElement) {
                errorDiv.remove();
            }
        }, 10000);
    }

    /**
     * Validate form before submission
     */
    validateForm(form) {
        const csrfInput = form.querySelector('input[name="csrfmiddlewaretoken"]');
        if (!csrfInput || !csrfInput.value) {
            console.warn('CSRF token missing in form');
            return false;
        }
        return true;
    }
}

// Initialize CSRF manager
const csrfManager = new CSRFManager();

// Global error handler for AJAX requests
$(document).ajaxError(function(event, xhr, settings) {
    if (!csrfManager.handleCSRFFailure(xhr)) {
        // Handle other types of errors
        console.error('AJAX error:', xhr.status, xhr.statusText);
    }
});

// Form submission validation
document.addEventListener('submit', function(event) {
    const form = event.target;
    if (form.method.toLowerCase() === 'post') {
        if (!csrfManager.validateForm(form)) {
            event.preventDefault();
            csrfManager.showCSRFError('Security token missing. Please refresh the page and try again.');
        }
    }
});

// Export for use in other scripts
window.csrfManager = csrfManager;