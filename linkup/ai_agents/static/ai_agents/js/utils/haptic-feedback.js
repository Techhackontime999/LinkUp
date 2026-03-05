/**
 * Haptic Feedback Manager
 * Provides vibration feedback for mobile devices
 * Requirements: 20.10
 */

class HapticFeedback {
  /**
   * Check if device supports vibration API
   * @returns {boolean} True if vibration is supported
   */
  static isSupported() {
    return !!(navigator.vibrate || navigator.webkitVibrate || navigator.mozVibrate || navigator.msVibrate);
  }

  /**
   * Trigger vibration with pattern
   * @param {number|number[]} pattern - Vibration pattern in milliseconds
   */
  static vibrate(pattern) {
    if (!this.isSupported()) return;

    const vibrate = navigator.vibrate || navigator.webkitVibrate || navigator.mozVibrate || navigator.msVibrate;
    vibrate.call(navigator, pattern);
  }

  /**
   * Light haptic feedback (short, subtle vibration)
   */
  static light() {
    this.vibrate(10);
  }

  /**
   * Medium haptic feedback (standard vibration)
   */
  static medium() {
    this.vibrate(20);
  }

  /**
   * Heavy haptic feedback (strong, long vibration)
   */
  static heavy() {
    this.vibrate(30);
  }

  /**
   * Success feedback pattern
   */
  static success() {
    this.vibrate([10, 20, 10]);
  }

  /**
   * Error feedback pattern
   */
  static error() {
    this.vibrate([30, 10, 30]);
  }

  /**
   * Warning feedback pattern
   */
  static warning() {
    this.vibrate([20, 10, 20]);
  }

  /**
   * Double tap feedback pattern
   */
  static doubleTap() {
    this.vibrate([15, 10, 15]);
  }

  /**
   * Long press feedback pattern
   */
  static longPress() {
    this.vibrate([50]);
  }

  /**
   * Selection feedback pattern
   */
  static selection() {
    this.vibrate([5, 10, 5]);
  }

  /**
   * Initialize haptic feedback for interactive elements
   */
  static initializeForElements() {
    if (!this.isSupported()) return;

    // Add haptic feedback to buttons
    document.addEventListener('click', (e) => {
      const button = e.target.closest('button, [role="button"], .btn, a.clickable');
      if (button && !button.disabled) {
        this.light();
      }
    });

    // Add haptic feedback to form submissions
    document.addEventListener('submit', (e) => {
      const form = e.target;
      if (form && form.checkValidity()) {
        this.success();
      }
    });

    // Add haptic feedback to successful AJAX requests
    document.addEventListener('ajaxSuccess', () => {
      this.success();
    });

    // Add haptic feedback to failed AJAX requests
    document.addEventListener('ajaxError', () => {
      this.error();
    });
  }

  /**
   * Add haptic feedback to a specific element
   * @param {HTMLElement} element - Element to add feedback to
   * @param {string} pattern - Feedback pattern name
   */
  static addToElement(element, pattern = 'light') {
    if (!this.isSupported()) return;

    element.addEventListener('click', () => {
      this[pattern]?.();
    });
  }

  /**
   * Add haptic feedback to all elements with data-haptic attribute
   */
  static initializeDataAttributes() {
    if (!this.isSupported()) return;

    document.querySelectorAll('[data-haptic]').forEach((element) => {
      const pattern = element.getAttribute('data-haptic');
      this.addToElement(element, pattern);
    });
  }
}

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = HapticFeedback;
}
