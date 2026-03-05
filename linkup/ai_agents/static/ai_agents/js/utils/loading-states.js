/**
 * Loading States Manager
 * Handles loading spinners, button states, and skeleton screens
 * Requirements: 13.5, 12.8
 */

class LoadingStates {
  /**
   * Show loading spinner on an element
   * @param {HTMLElement} element - Element to show spinner in
   * @param {string} message - Optional loading message
   */
  static showSpinner(element, message = '') {
    if (!element) return;

    const spinner = document.createElement('div');
    spinner.className = 'loading-spinner';
    spinner.setAttribute('aria-label', 'Loading');
    spinner.setAttribute('role', 'status');

    element.innerHTML = '';
    element.appendChild(spinner);

    if (message) {
      const messageEl = document.createElement('p');
      messageEl.textContent = message;
      messageEl.style.marginTop = 'var(--spacing-md)';
      element.appendChild(messageEl);
    }
  }

  /**
   * Hide loading spinner
   * @param {HTMLElement} element - Element to clear
   */
  static hideSpinner(element) {
    if (!element) return;
    const spinner = element.querySelector('.loading-spinner');
    if (spinner) {
      spinner.remove();
    }
  }

  /**
   * Set button to loading state
   * @param {HTMLElement} button - Button element
   * @param {string} loadingText - Text to show while loading
   */
  static setButtonLoading(button, loadingText = 'Loading...') {
    if (!button) return;

    button.disabled = true;
    button.setAttribute('aria-busy', 'true');
    button.dataset.originalText = button.textContent;
    button.dataset.originalHTML = button.innerHTML;

    const spinner = document.createElement('span');
    spinner.className = 'loading-spinner';
    spinner.style.marginRight = 'var(--spacing-sm)';

    button.innerHTML = '';
    button.appendChild(spinner);

    const text = document.createElement('span');
    text.textContent = loadingText;
    button.appendChild(text);
  }

  /**
   * Reset button from loading state
   * @param {HTMLElement} button - Button element
   */
  static resetButton(button) {
    if (!button) return;

    button.disabled = false;
    button.setAttribute('aria-busy', 'false');

    if (button.dataset.originalHTML) {
      button.innerHTML = button.dataset.originalHTML;
    } else if (button.dataset.originalText) {
      button.textContent = button.dataset.originalText;
    }

    delete button.dataset.originalText;
    delete button.dataset.originalHTML;
  }

  /**
   * Disable all action buttons
   */
  static disableAllButtons() {
    document.querySelectorAll('button:not(:disabled), [role="button"]:not([aria-disabled="true"])').forEach((btn) => {
      btn.disabled = true;
      btn.setAttribute('aria-disabled', 'true');
    });
  }

  /**
   * Enable all action buttons
   */
  static enableAllButtons() {
    document.querySelectorAll('button[disabled], [role="button"][aria-disabled="true"]').forEach((btn) => {
      btn.disabled = false;
      btn.setAttribute('aria-disabled', 'false');
    });
  }

  /**
   * Create skeleton screen for a container
   * @param {HTMLElement} container - Container element
   * @param {number} count - Number of skeleton items
   * @param {string} type - Skeleton type ('text', 'card', 'avatar')
   */
  static showSkeletonScreen(container, count = 3, type = 'card') {
    if (!container) return;

    container.innerHTML = '';

    for (let i = 0; i < count; i++) {
      const skeleton = this._createSkeletonElement(type);
      container.appendChild(skeleton);
    }
  }

  /**
   * Create skeleton element
   * @private
   */
  static _createSkeletonElement(type) {
    const skeleton = document.createElement('div');
    skeleton.className = `skeleton skeleton-${type}`;

    switch (type) {
      case 'text':
        skeleton.innerHTML = `
          <div class="skeleton-text"></div>
          <div class="skeleton-text" style="width: 80%;"></div>
          <div class="skeleton-text" style="width: 60%;"></div>
        `;
        break;

      case 'card':
        skeleton.innerHTML = `
          <div style="display: flex; gap: var(--spacing-md);">
            <div class="skeleton-avatar"></div>
            <div style="flex: 1;">
              <div class="skeleton-text"></div>
              <div class="skeleton-text" style="width: 80%;"></div>
              <div class="skeleton-text" style="width: 60%;"></div>
            </div>
          </div>
        `;
        break;

      case 'avatar':
        skeleton.innerHTML = '<div class="skeleton-avatar"></div>';
        break;

      default:
        skeleton.innerHTML = '<div class="skeleton-text"></div>';
    }

    return skeleton;
  }

  /**
   * Hide skeleton screen
   * @param {HTMLElement} container - Container element
   */
  static hideSkeletonScreen(container) {
    if (!container) return;

    const skeletons = container.querySelectorAll('.skeleton');
    skeletons.forEach((skeleton) => {
      skeleton.style.opacity = '0';
      setTimeout(() => skeleton.remove(), 300);
    });
  }

  /**
   * Show loading overlay
   * @param {HTMLElement} element - Element to overlay
   * @param {string} message - Optional message
   * @returns {HTMLElement} Overlay element
   */
  static showOverlay(element, message = '') {
    if (!element) return null;

    const overlay = document.createElement('div');
    overlay.className = 'loading-overlay';
    overlay.style.cssText = `
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background-color: rgba(255, 255, 255, 0.8);
      display: flex;
      align-items: center;
      justify-content: center;
      flex-direction: column;
      gap: var(--spacing-md);
      z-index: 1000;
      border-radius: var(--radius-lg);
    `;

    const spinner = document.createElement('div');
    spinner.className = 'loading-spinner';
    overlay.appendChild(spinner);

    if (message) {
      const messageEl = document.createElement('p');
      messageEl.textContent = message;
      overlay.appendChild(messageEl);
    }

    element.style.position = 'relative';
    element.appendChild(overlay);

    return overlay;
  }

  /**
   * Hide loading overlay
   * @param {HTMLElement} overlay - Overlay element
   */
  static hideOverlay(overlay) {
    if (!overlay) return;

    overlay.style.opacity = '0';
    setTimeout(() => overlay.remove(), 300);
  }

  /**
   * Create progress bar
   * @param {HTMLElement} container - Container element
   * @param {number} progress - Progress percentage (0-100)
   * @returns {HTMLElement} Progress bar element
   */
  static createProgressBar(container, progress = 0) {
    if (!container) return null;

    let progressBar = container.querySelector('.progress-bar');
    if (!progressBar) {
      const progressContainer = document.createElement('div');
      progressContainer.className = 'progress';
      progressContainer.style.cssText = `
        width: 100%;
        height: 4px;
        background-color: var(--bg-tertiary);
        border-radius: 2px;
        overflow: hidden;
        margin-bottom: var(--spacing-md);
      `;

      progressBar = document.createElement('div');
      progressBar.className = 'progress-bar';
      progressBar.style.cssText = `
        height: 100%;
        background-color: var(--primary-color);
        width: ${progress}%;
        transition: width 0.3s ease;
      `;

      progressContainer.appendChild(progressBar);
      container.insertBefore(progressContainer, container.firstChild);
    } else {
      progressBar.style.width = `${progress}%`;
    }

    return progressBar;
  }

  /**
   * Update progress bar
   * @param {HTMLElement} progressBar - Progress bar element
   * @param {number} progress - Progress percentage (0-100)
   */
  static updateProgress(progressBar, progress) {
    if (!progressBar) return;
    progressBar.style.width = `${Math.min(100, Math.max(0, progress))}%`;
  }

  /**
   * Show loading state for form
   * @param {HTMLElement} form - Form element
   */
  static showFormLoading(form) {
    if (!form) return;

    form.querySelectorAll('button, input, textarea, select').forEach((el) => {
      el.disabled = true;
    });

    const overlay = this.showOverlay(form, 'Submitting...');
    form.dataset.loadingOverlay = overlay;
  }

  /**
   * Hide loading state for form
   * @param {HTMLElement} form - Form element
   */
  static hideFormLoading(form) {
    if (!form) return;

    form.querySelectorAll('button, input, textarea, select').forEach((el) => {
      el.disabled = false;
    });

    const overlay = form.dataset.loadingOverlay;
    if (overlay) {
      this.hideOverlay(overlay);
      delete form.dataset.loadingOverlay;
    }
  }
}

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = LoadingStates;
}
