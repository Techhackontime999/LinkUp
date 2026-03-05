/**
 * Error Page Handler
 * Displays user-friendly error pages for common HTTP errors
 * Requirements: 13.1, 13.8, 13.9
 */

class ErrorPages {
  /**
   * Show 404 error page
   * @param {string} message - Custom error message
   */
  static show404(message = 'Page not found') {
    const container = document.querySelector('main') || document.body;
    container.innerHTML = this._get404HTML(message);
  }

  /**
   * Show 500 error page
   * @param {string} message - Custom error message
   */
  static show500(message = 'Server error') {
    const container = document.querySelector('main') || document.body;
    container.innerHTML = this._get500HTML(message);
  }

  /**
   * Show network error page
   * @param {string} message - Custom error message
   */
  static showNetworkError(message = 'Network connection error') {
    const container = document.querySelector('main') || document.body;
    container.innerHTML = this._getNetworkErrorHTML(message);
  }

  /**
   * Show generic error page
   * @param {number} statusCode - HTTP status code
   * @param {string} message - Error message
   */
  static showError(statusCode, message) {
    switch (statusCode) {
      case 404:
        this.show404(message);
        break;
      case 500:
        this.show500(message);
        break;
      default:
        this.showGenericError(statusCode, message);
    }
  }

  /**
   * Show generic error page
   * @param {number} statusCode - HTTP status code
   * @param {string} message - Error message
   */
  static showGenericError(statusCode, message) {
    const container = document.querySelector('main') || document.body;
    container.innerHTML = this._getGenericErrorHTML(statusCode, message);
  }

  /**
   * Get 404 error HTML
   * @private
   */
  static _get404HTML(message) {
    return `
      <div class="error-page error-404">
        <div class="error-container">
          <div class="error-icon">
            <i class="fas fa-search"></i>
          </div>
          <h1>404 - Page Not Found</h1>
          <p class="error-message">${message}</p>
          <p class="error-description">
            The page you're looking for doesn't exist or has been moved.
          </p>
          <div class="error-actions">
            <a href="/" class="btn btn-primary">
              <i class="fas fa-home"></i> Go to Home
            </a>
            <a href="/discover" class="btn btn-secondary">
              <i class="fas fa-compass"></i> Discover Agents
            </a>
            <button class="btn btn-secondary" onclick="window.history.back()">
              <i class="fas fa-arrow-left"></i> Go Back
            </button>
          </div>
        </div>
      </div>
    `;
  }

  /**
   * Get 500 error HTML
   * @private
   */
  static _get500HTML(message) {
    return `
      <div class="error-page error-500">
        <div class="error-container">
          <div class="error-icon">
            <i class="fas fa-exclamation-triangle"></i>
          </div>
          <h1>500 - Server Error</h1>
          <p class="error-message">${message}</p>
          <p class="error-description">
            Something went wrong on our end. Please try again later.
          </p>
          <div class="error-actions">
            <button class="btn btn-primary" onclick="window.location.reload()">
              <i class="fas fa-redo"></i> Try Again
            </button>
            <a href="/" class="btn btn-secondary">
              <i class="fas fa-home"></i> Go to Home
            </a>
            <a href="mailto:support@example.com" class="btn btn-secondary">
              <i class="fas fa-envelope"></i> Contact Support
            </a>
          </div>
        </div>
      </div>
    `;
  }

  /**
   * Get network error HTML
   * @private
   */
  static _getNetworkErrorHTML(message) {
    return `
      <div class="error-page error-network">
        <div class="error-container">
          <div class="error-icon">
            <i class="fas fa-wifi-off"></i>
          </div>
          <h1>Connection Error</h1>
          <p class="error-message">${message}</p>
          <p class="error-description">
            Unable to connect to the server. Please check your internet connection.
          </p>
          <div class="error-actions">
            <button class="btn btn-primary" onclick="window.location.reload()">
              <i class="fas fa-redo"></i> Try Again
            </button>
            <a href="/" class="btn btn-secondary">
              <i class="fas fa-home"></i> Go to Home
            </a>
          </div>
        </div>
      </div>
    `;
  }

  /**
   * Get generic error HTML
   * @private
   */
  static _getGenericErrorHTML(statusCode, message) {
    return `
      <div class="error-page error-generic">
        <div class="error-container">
          <div class="error-icon">
            <i class="fas fa-exclamation-circle"></i>
          </div>
          <h1>${statusCode} - Error</h1>
          <p class="error-message">${message}</p>
          <div class="error-actions">
            <button class="btn btn-primary" onclick="window.location.reload()">
              <i class="fas fa-redo"></i> Try Again
            </button>
            <a href="/" class="btn btn-secondary">
              <i class="fas fa-home"></i> Go to Home
            </a>
          </div>
        </div>
      </div>
    `;
  }

  /**
   * Add error page styles
   */
  static addStyles() {
    const style = document.createElement('style');
    style.textContent = `
      .error-page {
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 100vh;
        padding: var(--spacing-lg);
        background: linear-gradient(135deg, var(--bg-secondary) 0%, var(--bg-tertiary) 100%);
      }

      .error-container {
        text-align: center;
        background-color: var(--bg-primary);
        border-radius: var(--radius-lg);
        padding: var(--spacing-xl);
        box-shadow: var(--shadow-lg);
        max-width: 500px;
        width: 100%;
      }

      .error-icon {
        font-size: 4rem;
        color: var(--danger-color);
        margin-bottom: var(--spacing-lg);
      }

      .error-page.error-500 .error-icon {
        color: var(--warning-color);
      }

      .error-page.error-network .error-icon {
        color: var(--info-color);
      }

      .error-container h1 {
        font-size: 2rem;
        margin-bottom: var(--spacing-md);
        color: var(--text-primary);
      }

      .error-message {
        font-size: 1.1rem;
        color: var(--text-secondary);
        margin-bottom: var(--spacing-md);
      }

      .error-description {
        color: var(--text-secondary);
        margin-bottom: var(--spacing-lg);
        line-height: 1.6;
      }

      .error-actions {
        display: flex;
        flex-direction: column;
        gap: var(--spacing-md);
      }

      @media (min-width: 576px) {
        .error-actions {
          flex-direction: row;
          justify-content: center;
          flex-wrap: wrap;
        }

        .error-actions .btn {
          flex: 0 1 auto;
        }
      }

      .error-actions .btn {
        display: inline-flex;
        align-items: center;
        gap: var(--spacing-xs);
      }
    `;
    document.head.appendChild(style);
  }

  /**
   * Handle AJAX errors
   * @param {Error} error - Error object
   * @param {number} statusCode - HTTP status code
   */
  static handleAJAXError(error, statusCode) {
    let message = error.message || 'An error occurred';

    if (statusCode === 404) {
      message = 'Resource not found';
    } else if (statusCode === 500) {
      message = 'Server error occurred';
    } else if (statusCode === 0 || !statusCode) {
      message = 'Network connection error';
    }

    this.showError(statusCode, message);
  }

  /**
   * Show error modal instead of full page
   * @param {number} statusCode - HTTP status code
   * @param {string} message - Error message
   */
  static showErrorModal(statusCode, message) {
    const modal = document.createElement('div');
    modal.className = 'modal show';
    modal.setAttribute('role', 'alertdialog');
    modal.setAttribute('aria-labelledby', 'error-modal-title');

    const content = document.createElement('div');
    content.className = 'modal-content';

    const header = document.createElement('div');
    header.className = 'modal-header';
    header.innerHTML = `
      <h2 id="error-modal-title">Error ${statusCode}</h2>
      <button class="btn-close" aria-label="Close" onclick="this.closest('.modal').remove()"></button>
    `;

    const body = document.createElement('div');
    body.className = 'modal-body';
    body.textContent = message;

    const footer = document.createElement('div');
    footer.className = 'modal-footer';
    footer.innerHTML = `
      <button class="btn btn-primary" onclick="this.closest('.modal').remove()">Close</button>
    `;

    content.appendChild(header);
    content.appendChild(body);
    content.appendChild(footer);
    modal.appendChild(content);

    document.body.appendChild(modal);
  }
}

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ErrorPages;
}
