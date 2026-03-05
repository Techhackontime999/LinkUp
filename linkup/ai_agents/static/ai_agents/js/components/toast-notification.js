/**
 * Toast Notification Component
 * Displays temporary notifications with auto-dismiss
 * Requirements: 13.4, 12.8
 */

class ToastNotification {
  static TYPES = {
    SUCCESS: 'success',
    ERROR: 'error',
    WARNING: 'warning',
    INFO: 'info'
  };

  static DEFAULT_DURATION = 3000; // 3 seconds
  static CONTAINER_ID = 'toast-container';

  /**
   * Initialize toast container
   */
  static initContainer() {
    let container = document.getElementById(this.CONTAINER_ID);
    if (!container) {
      container = document.createElement('div');
      container.id = this.CONTAINER_ID;
      container.className = 'toast-container';
      document.body.appendChild(container);
    }
    return container;
  }

  /**
   * Show a toast notification
   * @param {string} message - Notification message
   * @param {string} type - Notification type (success, error, warning, info)
   * @param {number} duration - Duration in milliseconds (0 = no auto-dismiss)
   * @returns {HTMLElement} Toast element
   */
  static show(message, type = this.TYPES.INFO, duration = this.DEFAULT_DURATION) {
    const container = this.initContainer();
    const toast = this._createToastElement(message, type);

    container.appendChild(toast);

    // Trigger animation
    setTimeout(() => {
      toast.classList.add('show');
    }, 10);

    // Auto-dismiss
    if (duration > 0) {
      setTimeout(() => {
        this._dismissToast(toast);
      }, duration);
    }

    return toast;
  }

  /**
   * Show success notification
   * @param {string} message - Notification message
   * @param {number} duration - Duration in milliseconds
   */
  static success(message, duration = this.DEFAULT_DURATION) {
    return this.show(message, this.TYPES.SUCCESS, duration);
  }

  /**
   * Show error notification
   * @param {string} message - Notification message
   * @param {number} duration - Duration in milliseconds
   */
  static error(message, duration = this.DEFAULT_DURATION) {
    return this.show(message, this.TYPES.ERROR, duration);
  }

  /**
   * Show warning notification
   * @param {string} message - Notification message
   * @param {number} duration - Duration in milliseconds
   */
  static warning(message, duration = this.DEFAULT_DURATION) {
    return this.show(message, this.TYPES.WARNING, duration);
  }

  /**
   * Show info notification
   * @param {string} message - Notification message
   * @param {number} duration - Duration in milliseconds
   */
  static info(message, duration = this.DEFAULT_DURATION) {
    return this.show(message, this.TYPES.INFO, duration);
  }

  /**
   * Create toast element
   * @private
   */
  static _createToastElement(message, type) {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.setAttribute('role', 'status');
    toast.setAttribute('aria-live', 'polite');
    toast.setAttribute('aria-atomic', 'true');

    const icon = this._getIconForType(type);
    const closeButton = document.createElement('button');
    closeButton.className = 'toast-close';
    closeButton.setAttribute('aria-label', 'Close notification');
    closeButton.innerHTML = '<i class="fas fa-times"></i>';
    closeButton.addEventListener('click', () => {
      this._dismissToast(toast);
    });

    toast.innerHTML = `
      <div class="toast-icon">
        <i class="fas fa-${icon}"></i>
      </div>
      <div class="toast-content">
        ${message}
      </div>
    `;

    toast.appendChild(closeButton);

    return toast;
  }

  /**
   * Get icon for notification type
   * @private
   */
  static _getIconForType(type) {
    const icons = {
      success: 'check-circle',
      error: 'exclamation-circle',
      warning: 'exclamation-triangle',
      info: 'info-circle'
    };
    return icons[type] || 'info-circle';
  }

  /**
   * Dismiss a toast
   * @private
   */
  static _dismissToast(toast) {
    toast.classList.remove('show');
    setTimeout(() => {
      toast.remove();
    }, 300);
  }

  /**
   * Clear all toasts
   */
  static clearAll() {
    const container = document.getElementById(this.CONTAINER_ID);
    if (container) {
      container.querySelectorAll('.toast').forEach((toast) => {
        this._dismissToast(toast);
      });
    }
  }

  /**
   * Show loading toast (no auto-dismiss)
   * @param {string} message - Loading message
   * @returns {HTMLElement} Toast element
   */
  static loading(message = 'Loading...') {
    const container = this.initContainer();
    const toast = document.createElement('div');
    toast.className = 'toast info';
    toast.setAttribute('role', 'status');
    toast.setAttribute('aria-live', 'polite');
    toast.setAttribute('aria-busy', 'true');

    toast.innerHTML = `
      <div class="toast-icon">
        <div class="loading-spinner"></div>
      </div>
      <div class="toast-content">
        ${message}
      </div>
    `;

    container.appendChild(toast);

    setTimeout(() => {
      toast.classList.add('show');
    }, 10);

    return toast;
  }

  /**
   * Show confirmation toast with action buttons
   * @param {string} message - Confirmation message
   * @param {Function} onConfirm - Callback for confirm button
   * @param {Function} onCancel - Callback for cancel button
   * @returns {HTMLElement} Toast element
   */
  static confirm(message, onConfirm, onCancel) {
    const container = this.initContainer();
    const toast = document.createElement('div');
    toast.className = 'toast info';
    toast.setAttribute('role', 'alertdialog');
    toast.setAttribute('aria-label', 'Confirmation');

    const confirmBtn = document.createElement('button');
    confirmBtn.className = 'btn btn-sm btn-primary';
    confirmBtn.textContent = 'Confirm';
    confirmBtn.addEventListener('click', () => {
      onConfirm?.();
      this._dismissToast(toast);
    });

    const cancelBtn = document.createElement('button');
    cancelBtn.className = 'btn btn-sm btn-secondary';
    cancelBtn.textContent = 'Cancel';
    cancelBtn.addEventListener('click', () => {
      onCancel?.();
      this._dismissToast(toast);
    });

    toast.innerHTML = `
      <div class="toast-content">
        ${message}
      </div>
    `;

    const buttonContainer = document.createElement('div');
    buttonContainer.style.display = 'flex';
    buttonContainer.style.gap = 'var(--spacing-sm)';
    buttonContainer.style.marginTop = 'var(--spacing-md)';
    buttonContainer.appendChild(confirmBtn);
    buttonContainer.appendChild(cancelBtn);

    toast.appendChild(buttonContainer);
    container.appendChild(toast);

    setTimeout(() => {
      toast.classList.add('show');
    }, 10);

    return toast;
  }
}

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ToastNotification;
}

export default ToastNotification;

