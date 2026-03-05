/**
 * Error Handler Module
 * 
 * Global error handling for AJAX failures, network errors, and exceptions.
 * Provides user-friendly error messages and logging.
 */

export class ErrorHandler {
  constructor() {
    this.errorContainer = null;
    this.setupGlobalHandlers();
  }

  /**
   * Set up global error handlers
   */
  setupGlobalHandlers() {
    // Handle unhandled promise rejections
    window.addEventListener('unhandledrejection', (event) => {
      console.error('Unhandled promise rejection:', event.reason);
      this.logError(event.reason);
    });

    // Handle global errors
    window.addEventListener('error', (event) => {
      console.error('Global error:', event.error);
      this.logError(event.error);
    });
  }

  /**
   * Handle API errors
   */
  handleAPIError(error, context = '') {
    console.error(`API Error ${context}:`, error);
    
    let message = 'An error occurred. Please try again.';
    
    if (error.message) {
      if (error.message.includes('401') || error.message.includes('Authentication')) {
        message = 'Please log in to continue.';
        setTimeout(() => {
          window.location.href = '/login/';
        }, 2000);
      } else if (error.message.includes('404')) {
        message = 'The requested resource was not found.';
      } else if (error.message.includes('500')) {
        message = 'Server error. Please try again later.';
      } else if (error.message.includes('Network')) {
        message = 'Network error. Please check your connection.';
      } else {
        message = error.message;
      }
    }
    
    this.showError(message);
    this.logError(error, context);
  }

  /**
   * Handle validation errors
   */
  handleValidationError(errors, formElement = null) {
    if (typeof errors === 'object') {
      Object.entries(errors).forEach(([field, messages]) => {
        const errorMessage = Array.isArray(messages) ? messages.join(', ') : messages;
        
        if (formElement) {
          const fieldElement = formElement.querySelector(`[name="${field}"]`);
          if (fieldElement) {
            this.showFieldError(fieldElement, errorMessage);
          }
        } else {
          this.showError(`${field}: ${errorMessage}`);
        }
      });
    } else {
      this.showError(errors);
    }
  }

  /**
   * Show error notification
   */
  showError(message, duration = 5000) {
    this.showNotification(message, 'error', duration);
  }

  /**
   * Show success notification
   */
  showSuccess(message, duration = 3000) {
    this.showNotification(message, 'success', duration);
  }

  /**
   * Show info notification
   */
  showInfo(message, duration = 3000) {
    this.showNotification(message, 'info', duration);
  }

  /**
   * Show warning notification
   */
  showWarning(message, duration = 4000) {
    this.showNotification(message, 'warning', duration);
  }

  /**
   * Show notification toast
   */
  showNotification(message, type = 'info', duration = 3000) {
    // Create toast container if it doesn't exist
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.className = 'position-fixed top-0 end-0 p-3';
      container.style.zIndex = '9999';
      document.body.appendChild(container);
    }

    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${this.getBootstrapColor(type)} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
      <div class="d-flex">
        <div class="toast-body">
          ${this.escapeHtml(message)}
        </div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
      </div>
    `;

    container.appendChild(toast);

    // Initialize and show toast
    const bsToast = new bootstrap.Toast(toast, { autohide: true, delay: duration });
    bsToast.show();

    // Remove toast element after it's hidden
    toast.addEventListener('hidden.bs.toast', () => {
      toast.remove();
    });
  }

  /**
   * Show field-specific error
   */
  showFieldError(fieldElement, message) {
    // Remove existing error
    this.clearFieldError(fieldElement);

    // Add error class
    fieldElement.classList.add('is-invalid');

    // Create error message element
    const errorDiv = document.createElement('div');
    errorDiv.className = 'invalid-feedback';
    errorDiv.textContent = message;
    errorDiv.setAttribute('role', 'alert');

    // Insert after field
    fieldElement.parentNode.insertBefore(errorDiv, fieldElement.nextSibling);
  }

  /**
   * Clear field error
   */
  clearFieldError(fieldElement) {
    fieldElement.classList.remove('is-invalid');
    const errorDiv = fieldElement.parentNode.querySelector('.invalid-feedback');
    if (errorDiv) {
      errorDiv.remove();
    }
  }

  /**
   * Log error to console and optionally to server
   */
  logError(error, context = '') {
    const errorInfo = {
      message: error.message || String(error),
      stack: error.stack,
      context,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href,
    };

    console.error('Error logged:', errorInfo);

    // TODO: Send to server logging endpoint in production
    // this.sendErrorToServer(errorInfo);
  }

  /**
   * Get Bootstrap color class for notification type
   */
  getBootstrapColor(type) {
    const colorMap = {
      success: 'success',
      error: 'danger',
      warning: 'warning',
      info: 'info',
    };
    return colorMap[type] || 'info';
  }

  /**
   * Escape HTML to prevent XSS
   */
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

// Export singleton instance
export const errorHandler = new ErrorHandler();
