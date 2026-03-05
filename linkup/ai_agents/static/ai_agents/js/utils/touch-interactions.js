/**
 * Mobile Touch Interactions
 * Handles swipe gestures, pull-to-refresh, and touch optimizations
 * Requirements: 20.1, 20.2, 20.3, 20.4, 20.5, 20.7, 20.8
 */

class TouchInteractions {
  /**
   * Initialize touch interactions for the page
   */
  static init() {
    this._initSwipeGestures();
    this._initPullToRefresh();
    this._initAutoFocus();
    this._initNativeScrolling();
    this._initDoubleTapZoomPrevention();
    this._initSlideInMenu();
  }

  /**
   * Initialize swipe gestures for tab navigation
   * @private
   */
  static _initSwipeGestures() {
    let touchStartX = 0;
    let touchEndX = 0;
    const minSwipeDistance = 50;

    document.addEventListener('touchstart', (e) => {
      touchStartX = e.changedTouches[0].screenX;
    }, false);

    document.addEventListener('touchend', (e) => {
      touchEndX = e.changedTouches[0].screenX;
      this._handleSwipe(touchStartX, touchEndX, minSwipeDistance);
    }, false);
  }

  /**
   * Handle swipe gesture
   * @private
   */
  static _handleSwipe(startX, endX, minDistance) {
    const distance = startX - endX;
    const isLeftSwipe = distance > minDistance;
    const isRightSwipe = distance < -minDistance;

    if (isLeftSwipe || isRightSwipe) {
      const event = new CustomEvent('swipe', {
        detail: {
          direction: isLeftSwipe ? 'left' : 'right',
          distance: Math.abs(distance)
        }
      });
      document.dispatchEvent(event);
    }
  }

  /**
   * Initialize pull-to-refresh gesture
   * @private
   */
  static _initPullToRefresh() {
    let touchStartY = 0;
    let isPulling = false;
    const pullThreshold = 100;
    const feedElement = document.querySelector('.social-feed');

    if (!feedElement) return;

    feedElement.addEventListener('touchstart', (e) => {
      touchStartY = e.touches[0].clientY;
      isPulling = feedElement.scrollTop === 0;
    }, false);

    feedElement.addEventListener('touchmove', (e) => {
      if (!isPulling) return;

      const touchCurrentY = e.touches[0].clientY;
      const pullDistance = touchCurrentY - touchStartY;

      if (pullDistance > 0) {
        e.preventDefault();
        this._showPullIndicator(pullDistance, pullThreshold);
      }
    }, { passive: false });

    feedElement.addEventListener('touchend', (e) => {
      const touchEndY = e.changedTouches[0].clientY;
      const pullDistance = touchEndY - touchStartY;

      if (isPulling && pullDistance > pullThreshold) {
        this._triggerRefresh();
      }

      this._hidePullIndicator();
      isPulling = false;
    }, false);
  }

  /**
   * Show pull-to-refresh indicator
   * @private
   */
  static _showPullIndicator(distance, threshold) {
    let indicator = document.querySelector('.pull-indicator');

    if (!indicator) {
      indicator = document.createElement('div');
      indicator.className = 'pull-indicator';
      indicator.innerHTML = '<i class="fas fa-arrow-down"></i>';
      document.querySelector('.social-feed').prepend(indicator);
    }

    const rotation = Math.min((distance / threshold) * 180, 180);
    indicator.style.transform = `translateY(${distance}px) rotate(${rotation}deg)`;
    indicator.style.opacity = Math.min(distance / threshold, 1);
  }

  /**
   * Hide pull-to-refresh indicator
   * @private
   */
  static _hidePullIndicator() {
    const indicator = document.querySelector('.pull-indicator');
    if (indicator) {
      indicator.style.opacity = '0';
      setTimeout(() => indicator.remove(), 300);
    }
  }

  /**
   * Trigger refresh action
   * @private
   */
  static _triggerRefresh() {
    const event = new CustomEvent('pullToRefresh');
    document.dispatchEvent(event);
  }

  /**
   * Auto-focus comment inputs on mobile tap
   * @private
   */
  static _initAutoFocus() {
    document.addEventListener('click', (e) => {
      const commentInput = e.target.closest('.comment-input');
      if (commentInput) {
        const textarea = commentInput.querySelector('textarea');
        if (textarea && this._isMobileDevice()) {
          setTimeout(() => {
            textarea.focus();
            // Scroll into view
            textarea.scrollIntoView({ behavior: 'smooth', block: 'center' });
          }, 100);
        }
      }
    });
  }

  /**
   * Enable native mobile scrolling
   * @private
   */
  static _initNativeScrolling() {
    // Use -webkit-overflow-scrolling for smooth momentum scrolling on iOS
    const scrollableElements = document.querySelectorAll(
      '.social-feed, .message-thread, .notification-list'
    );

    scrollableElements.forEach((el) => {
      el.style.webkitOverflowScrolling = 'touch';
    });
  }

  /**
   * Prevent double-tap zoom on interactive elements
   * @private
   */
  static _initDoubleTapZoomPrevention() {
    let lastTouchEnd = 0;

    document.addEventListener('touchend', (e) => {
      const now = Date.now();
      if (now - lastTouchEnd <= 300) {
        // Double tap detected
        if (this._isInteractiveElement(e.target)) {
          e.preventDefault();
        }
      }
      lastTouchEnd = now;
    }, false);

    // Also set viewport meta tag to prevent zoom
    let viewportMeta = document.querySelector('meta[name="viewport"]');
    if (!viewportMeta) {
      viewportMeta = document.createElement('meta');
      viewportMeta.name = 'viewport';
      document.head.appendChild(viewportMeta);
    }
    viewportMeta.content = 'width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no';
  }

  /**
   * Initialize slide-in navigation menu
   * @private
   */
  static _initSlideInMenu() {
    const hamburger = document.querySelector('.hamburger-menu');
    const navMenu = document.querySelector('.nav-menu-mobile');

    if (!hamburger || !navMenu) return;

    hamburger.addEventListener('click', () => {
      hamburger.classList.toggle('active');
      navMenu.classList.toggle('active');
    });

    // Close menu when a link is clicked
    navMenu.querySelectorAll('a').forEach((link) => {
      link.addEventListener('click', () => {
        hamburger.classList.remove('active');
        navMenu.classList.remove('active');
      });
    });

    // Close menu when clicking outside
    document.addEventListener('click', (e) => {
      if (!e.target.closest('.hamburger-menu') && !e.target.closest('.nav-menu-mobile')) {
        hamburger.classList.remove('active');
        navMenu.classList.remove('active');
      }
    });
  }

  /**
   * Check if element is interactive
   * @private
   */
  static _isInteractiveElement(element) {
    const interactiveSelectors = [
      'button',
      'a',
      'input',
      'textarea',
      'select',
      '[role="button"]',
      '.btn',
      '.clickable'
    ];

    return interactiveSelectors.some((selector) => element.closest(selector));
  }

  /**
   * Check if device is mobile
   * @private
   */
  static _isMobileDevice() {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
      navigator.userAgent
    );
  }

  /**
   * Enable native share sheet on mobile
   * @param {string} title - Share title
   * @param {string} text - Share text
   * @param {string} url - Share URL
   */
  static async shareContent(title, text, url) {
    if (navigator.share && this._isMobileDevice()) {
      try {
        await navigator.share({
          title,
          text,
          url
        });
        return true;
      } catch (error) {
        if (error.name !== 'AbortError') {
          console.error('Error sharing:', error);
        }
        return false;
      }
    }
    return false;
  }

  /**
   * Trigger haptic feedback on supported devices
   * @param {string} pattern - Vibration pattern ('light', 'medium', 'heavy', or array of ms)
   */
  static triggerHaptic(pattern = 'medium') {
    if (!navigator.vibrate) return;

    const patterns = {
      light: [10],
      medium: [20],
      heavy: [30],
      success: [10, 20, 10],
      error: [30, 10, 30],
      warning: [20, 10, 20]
    };

    const vibrationPattern = patterns[pattern] || pattern;
    navigator.vibrate(vibrationPattern);
  }

  /**
   * Get touch target size (for accessibility)
   * @returns {number} Minimum touch target size in pixels
   */
  static getTouchTargetSize() {
    return 44; // WCAG 2.1 Level AAA recommendation
  }

  /**
   * Check if element meets touch target size requirements
   * @param {HTMLElement} element - Element to check
   * @returns {boolean} True if element meets minimum size
   */
  static meetsMinimumTouchSize(element) {
    const rect = element.getBoundingClientRect();
    const minSize = this.getTouchTargetSize();
    return rect.width >= minSize && rect.height >= minSize;
  }
}

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = TouchInteractions;
}
