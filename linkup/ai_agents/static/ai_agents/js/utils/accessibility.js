/**
 * Accessibility Utilities
 * Provides helpers for semantic HTML and ARIA labels
 * Requirements: 12.3, 12.5, 12.9
 */

class AccessibilityUtils {
  /**
   * Add ARIA label to an element
   * @param {HTMLElement} element - Element to label
   * @param {string} label - ARIA label text
   */
  static addAriaLabel(element, label) {
    if (!element) return;
    element.setAttribute('aria-label', label);
  }

  /**
   * Add ARIA labels to all interactive buttons
   */
  static labelAllButtons() {
    document.querySelectorAll('button, [role="button"]').forEach((button) => {
      if (!button.getAttribute('aria-label') && !button.textContent.trim()) {
        const icon = button.querySelector('i');
        if (icon) {
          const iconClass = icon.className;
          const label = this._getIconLabel(iconClass);
          if (label) {
            this.addAriaLabel(button, label);
          }
        }
      }
    });
  }

  /**
   * Add ARIA labels to all form fields
   */
  static labelAllFormFields() {
    document.querySelectorAll('input, textarea, select').forEach((field) => {
      if (!field.getAttribute('aria-label') && !field.getAttribute('aria-labelledby')) {
        const label = document.querySelector(`label[for="${field.id}"]`);
        if (label) {
          field.setAttribute('aria-label', label.textContent);
        } else if (field.placeholder) {
          field.setAttribute('aria-label', field.placeholder);
        } else if (field.name) {
          field.setAttribute('aria-label', field.name);
        }
      }
    });
  }

  /**
   * Add ARIA roles for dynamic content regions
   */
  static setupDynamicRegions() {
    // Feed region
    const feed = document.querySelector('.social-feed');
    if (feed && !feed.getAttribute('role')) {
      feed.setAttribute('role', 'feed');
      feed.setAttribute('aria-label', 'Social feed');
      feed.setAttribute('aria-live', 'polite');
      feed.setAttribute('aria-busy', 'false');
    }

    // Notification region
    const notifications = document.querySelector('.notification-list');
    if (notifications && !notifications.getAttribute('role')) {
      notifications.setAttribute('role', 'region');
      notifications.setAttribute('aria-label', 'Notifications');
      notifications.setAttribute('aria-live', 'assertive');
    }

    // Message thread region
    const messages = document.querySelector('.message-thread');
    if (messages && !messages.getAttribute('role')) {
      messages.setAttribute('role', 'region');
      messages.setAttribute('aria-label', 'Messages');
      messages.setAttribute('aria-live', 'polite');
    }

    // Comment section
    const comments = document.querySelector('.comment-section');
    if (comments && !comments.getAttribute('role')) {
      comments.setAttribute('role', 'region');
      comments.setAttribute('aria-label', 'Comments');
      comments.setAttribute('aria-live', 'polite');
    }
  }

  /**
   * Add ARIA labels to reaction buttons
   */
  static labelReactionButtons() {
    document.querySelectorAll('.reaction-btn').forEach((btn) => {
      const type = btn.getAttribute('data-type');
      const count = btn.querySelector('.count')?.textContent || '0';
      const label = `${type} reaction, ${count} reactions`;
      this.addAriaLabel(btn, label);
    });
  }

  /**
   * Add ARIA labels to follow buttons
   */
  static labelFollowButtons() {
    document.querySelectorAll('.follow-btn').forEach((btn) => {
      const isFollowing = btn.classList.contains('following');
      const label = isFollowing ? 'Unfollow this agent' : 'Follow this agent';
      this.addAriaLabel(btn, label);
    });
  }

  /**
   * Add ARIA labels to comment buttons
   */
  static labelCommentButtons() {
    document.querySelectorAll('.comment-btn').forEach((btn) => {
      const count = btn.textContent.match(/\\d+/) || '0';
      const label = `Comment, ${count} comments`;
      this.addAriaLabel(btn, label);
    });
  }

  /**
   * Add ARIA labels to share buttons
   */
  static labelShareButtons() {
    document.querySelectorAll('.share-btn').forEach((btn) => {
      const count = btn.textContent.match(/\\d+/) || '0';
      const label = `Share post, ${count} shares`;
      this.addAriaLabel(btn, label);
    });
  }

  /**
   * Announce message to screen readers
   * @param {string} message - Message to announce
   * @param {string} priority - 'polite' or 'assertive'
   */
  static announce(message, priority = 'polite') {
    const announcement = document.createElement('div');
    announcement.setAttribute('role', 'status');
    announcement.setAttribute('aria-live', priority);
    announcement.setAttribute('aria-atomic', 'true');
    announcement.className = 'sr-only';
    announcement.textContent = message;

    document.body.appendChild(announcement);

    // Remove after announcement
    setTimeout(() => announcement.remove(), 1000);
  }

  /**
   * Set up keyboard navigation
   */
  static setupKeyboardNavigation() {
    // Tab navigation is automatic, but we can enhance it
    document.addEventListener('keydown', (e) => {
      // Enter/Space activation for buttons
      if ((e.key === 'Enter' || e.key === ' ') && e.target.matches('[role="button"]')) {
        e.preventDefault();
        e.target.click();
      }

      // Escape to close modals
      if (e.key === 'Escape') {
        const modal = document.querySelector('.modal.show');
        if (modal) {
          modal.classList.remove('show');
        }
      }

      // Arrow keys for navigation in lists
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        const list = e.target.closest('[role="listbox"], [role="menu"]');
        if (list) {
          this._handleArrowNavigation(e, list);
        }
      }
    });
  }

  /**
   * Handle arrow key navigation in lists
   * @private
   */
  static _handleArrowNavigation(e, list) {
    const items = Array.from(list.querySelectorAll('[role="option"], [role="menuitem"]'));
    const currentIndex = items.indexOf(e.target);

    if (currentIndex === -1) return;

    let nextIndex;
    if (e.key === 'ArrowDown') {
      nextIndex = (currentIndex + 1) % items.length;
    } else {
      nextIndex = (currentIndex - 1 + items.length) % items.length;
    }

    items[nextIndex].focus();
    e.preventDefault();
  }

  /**
   * Add skip to main content link
   */
  static addSkipLink() {
    const skipLink = document.createElement('a');
    skipLink.href = '#main-content';
    skipLink.className = 'skip-to-main';
    skipLink.textContent = 'Skip to main content';

    document.body.insertBefore(skipLink, document.body.firstChild);
  }

  /**
   * Ensure main content has ID for skip link
   */
  static ensureMainContentId() {
    const main = document.querySelector('main');
    if (main && !main.id) {
      main.id = 'main-content';
    }
  }

  /**
   * Add focus visible class to elements
   */
  static addFocusVisibleClass() {
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Tab') {
        document.body.classList.add('keyboard-nav');
      }
    });

    document.addEventListener('mousedown', () => {
      document.body.classList.remove('keyboard-nav');
    });
  }

  /**
   * Validate color contrast ratio
   * @param {string} foreground - Foreground color (hex or rgb)
   * @param {string} background - Background color (hex or rgb)
   * @returns {number} Contrast ratio
   */
  static getContrastRatio(foreground, background) {
    const fgLum = this._getLuminance(foreground);
    const bgLum = this._getLuminance(background);

    const lighter = Math.max(fgLum, bgLum);
    const darker = Math.min(fgLum, bgLum);

    return (lighter + 0.05) / (darker + 0.05);
  }

  /**
   * Get relative luminance of a color
   * @private
   */
  static _getLuminance(color) {
    const rgb = this._hexToRgb(color);
    if (!rgb) return 0;

    const [r, g, b] = rgb.map((val) => {
      val = val / 255;
      return val <= 0.03928 ? val / 12.92 : Math.pow((val + 0.055) / 1.055, 2.4);
    });

    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  }

  /**
   * Convert hex color to RGB
   * @private
   */
  static _hexToRgb(hex) {
    const result = /^#?([a-f\\d]{2})([a-f\\d]{2})([a-f\\d]{2})$/i.exec(hex);
    return result
      ? [parseInt(result[1], 16), parseInt(result[2], 16), parseInt(result[3], 16)]
      : null;
  }

  /**
   * Get icon label from Font Awesome class
   * @private
   */
  static _getIconLabel(iconClass) {
    const labels = {
      'fa-heart': 'Like',
      'fa-thumbs-up': 'Like',
      'fa-comment': 'Comment',
      'fa-share': 'Share',
      'fa-bell': 'Notifications',
      'fa-user': 'Profile',
      'fa-search': 'Search',
      'fa-menu': 'Menu',
      'fa-close': 'Close',
      'fa-times': 'Close',
      'fa-trash': 'Delete',
      'fa-edit': 'Edit',
      'fa-save': 'Save',
      'fa-cancel': 'Cancel',
      'fa-lightbulb': 'Insightful',
      'fa-hands-helping': 'Helpful',
      'fa-trophy': 'Celebrate'
    };

    for (const [key, label] of Object.entries(labels)) {
      if (iconClass.includes(key)) {
        return label;
      }
    }

    return null;
  }

  /**
   * Initialize all accessibility features
   */
  static initializeAll() {
    this.addSkipLink();
    this.ensureMainContentId();
    this.labelAllButtons();
    this.labelAllFormFields();
    this.setupDynamicRegions();
    this.setupKeyboardNavigation();
    this.addFocusVisibleClass();
  }
}

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = AccessibilityUtils;
}
