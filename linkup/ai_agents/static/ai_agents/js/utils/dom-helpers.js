/**
 * DOM Helper Utilities
 * Provides convenient DOM manipulation and event delegation helpers
 * Requirements: General utility for all components
 */

class DOMHelpers {
  /**
   * Create an element with optional attributes and content
   * @param {string} tag - HTML tag name
   * @param {object} options - Element options
   * @param {string} options.className - CSS class name(s)
   * @param {string} options.id - Element ID
   * @param {object} options.attributes - Additional attributes
   * @param {string} options.text - Text content
   * @param {string} options.html - HTML content
   * @param {array} options.children - Child elements
   * @returns {HTMLElement}
   */
  static createElement(tag, options = {}) {
    const element = document.createElement(tag);

    if (options.className) {
      if (Array.isArray(options.className)) {
        element.classList.add(...options.className);
      } else {
        element.className = options.className;
      }
    }

    if (options.id) {
      element.id = options.id;
    }

    if (options.attributes) {
      Object.entries(options.attributes).forEach(([key, value]) => {
        if (value === true) {
          element.setAttribute(key, '');
        } else if (value !== false && value !== null) {
          element.setAttribute(key, value);
        }
      });
    }

    if (options.text) {
      element.textContent = options.text;
    }

    if (options.html) {
      element.innerHTML = options.html;
    }

    if (options.children && Array.isArray(options.children)) {
      options.children.forEach((child) => {
        if (child instanceof HTMLElement) {
          element.appendChild(child);
        } else if (typeof child === 'string') {
          element.appendChild(document.createTextNode(child));
        }
      });
    }

    return element;
  }

  /**
   * Query selector wrapper with error handling
   * @param {string} selector - CSS selector
   * @param {HTMLElement} context - Context element (defaults to document)
   * @returns {HTMLElement|null}
   */
  static querySelector(selector, context = document) {
    try {
      return context.querySelector(selector);
    } catch (error) {
      console.error(`Invalid selector: ${selector}`, error);
      return null;
    }
  }

  /**
   * Query selector all wrapper with error handling
   * @param {string} selector - CSS selector
   * @param {HTMLElement} context - Context element (defaults to document)
   * @returns {NodeList}
   */
  static querySelectorAll(selector, context = document) {
    try {
      return context.querySelectorAll(selector);
    } catch (error) {
      console.error(`Invalid selector: ${selector}`, error);
      return [];
    }
  }

  /**
   * Get element by ID
   * @param {string} id - Element ID
   * @returns {HTMLElement|null}
   */
  static getElementById(id) {
    return document.getElementById(id);
  }

  /**
   * Add event listener with automatic cleanup
   * @param {HTMLElement} element - Target element
   * @param {string} event - Event name
   * @param {function} handler - Event handler
   * @param {object} options - Event listener options
   * @returns {function} Cleanup function
   */
  static addEventListener(element, event, handler, options = {}) {
    if (!element) {
      console.warn('Element not found for event listener');
      return () => {};
    }

    element.addEventListener(event, handler, options);

    // Return cleanup function
    return () => {
      element.removeEventListener(event, handler, options);
    };
  }

  /**
   * Event delegation - attach handler to parent for child elements
   * @param {HTMLElement} parent - Parent element
   * @param {string} selector - Child selector
   * @param {string} event - Event name
   * @param {function} handler - Event handler
   * @returns {function} Cleanup function
   */
  static delegate(parent, selector, event, handler) {
    if (!parent) {
      console.warn('Parent element not found for event delegation');
      return () => {};
    }

    const delegatedHandler = (e) => {
      const target = e.target.closest(selector);
      if (target && parent.contains(target)) {
        handler.call(target, e);
      }
    };

    parent.addEventListener(event, delegatedHandler);

    // Return cleanup function
    return () => {
      parent.removeEventListener(event, delegatedHandler);
    };
  }

  /**
   * Add class to element
   * @param {HTMLElement} element - Target element
   * @param {string|array} className - Class name(s)
   */
  static addClass(element, className) {
    if (!element) return;
    if (Array.isArray(className)) {
      element.classList.add(...className);
    } else {
      element.classList.add(className);
    }
  }

  /**
   * Remove class from element
   * @param {HTMLElement} element - Target element
   * @param {string|array} className - Class name(s)
   */
  static removeClass(element, className) {
    if (!element) return;
    if (Array.isArray(className)) {
      element.classList.remove(...className);
    } else {
      element.classList.remove(className);
    }
  }

  /**
   * Toggle class on element
   * @param {HTMLElement} element - Target element
   * @param {string} className - Class name
   * @returns {boolean} Whether class is now present
   */
  static toggleClass(element, className) {
    if (!element) return false;
    return element.classList.toggle(className);
  }

  /**
   * Check if element has class
   * @param {HTMLElement} element - Target element
   * @param {string} className - Class name
   * @returns {boolean}
   */
  static hasClass(element, className) {
    if (!element) return false;
    return element.classList.contains(className);
  }

  /**
   * Set multiple attributes on element
   * @param {HTMLElement} element - Target element
   * @param {object} attributes - Attributes to set
   */
  static setAttributes(element, attributes) {
    if (!element) return;
    Object.entries(attributes).forEach(([key, value]) => {
      if (value === true) {
        element.setAttribute(key, '');
      } else if (value === false || value === null) {
        element.removeAttribute(key);
      } else {
        element.setAttribute(key, value);
      }
    });
  }

  /**
   * Get attribute value
   * @param {HTMLElement} element - Target element
   * @param {string} attribute - Attribute name
   * @returns {string|null}
   */
  static getAttribute(element, attribute) {
    if (!element) return null;
    return element.getAttribute(attribute);
  }

  /**
   * Set element text content
   * @param {HTMLElement} element - Target element
   * @param {string} text - Text content
   */
  static setText(element, text) {
    if (!element) return;
    element.textContent = text;
  }

  /**
   * Set element HTML content
   * @param {HTMLElement} element - Target element
   * @param {string} html - HTML content
   */
  static setHTML(element, html) {
    if (!element) return;
    element.innerHTML = html;
  }

  /**
   * Get element text content
   * @param {HTMLElement} element - Target element
   * @returns {string}
   */
  static getText(element) {
    if (!element) return '';
    return element.textContent;
  }

  /**
   * Append child element(s)
   * @param {HTMLElement} parent - Parent element
   * @param {HTMLElement|array} children - Child element(s)
   */
  static append(parent, children) {
    if (!parent) return;
    if (Array.isArray(children)) {
      children.forEach((child) => {
        if (child instanceof HTMLElement) {
          parent.appendChild(child);
        }
      });
    } else if (children instanceof HTMLElement) {
      parent.appendChild(children);
    }
  }

  /**
   * Remove element from DOM
   * @param {HTMLElement} element - Element to remove
   */
  static remove(element) {
    if (!element) return;
    element.remove();
  }

  /**
   * Clear element content
   * @param {HTMLElement} element - Element to clear
   */
  static clear(element) {
    if (!element) return;
    element.innerHTML = '';
  }

  /**
   * Show element
   * @param {HTMLElement} element - Element to show
   * @param {string} display - Display value (defaults to 'block')
   */
  static show(element, display = 'block') {
    if (!element) return;
    element.style.display = display;
  }

  /**
   * Hide element
   * @param {HTMLElement} element - Element to hide
   */
  static hide(element) {
    if (!element) return;
    element.style.display = 'none';
  }

  /**
   * Toggle element visibility
   * @param {HTMLElement} element - Element to toggle
   * @param {string} display - Display value when shown
   */
  static toggleVisibility(element, display = 'block') {
    if (!element) return;
    element.style.display = element.style.display === 'none' ? display : 'none';
  }

  /**
   * Get element position and size
   * @param {HTMLElement} element - Target element
   * @returns {object} Position and size info
   */
  static getRect(element) {
    if (!element) return null;
    return element.getBoundingClientRect();
  }

  /**
   * Check if element is visible in viewport
   * @param {HTMLElement} element - Target element
   * @returns {boolean}
   */
  static isInViewport(element) {
    if (!element) return false;
    const rect = element.getBoundingClientRect();
    return (
      rect.top >= 0 &&
      rect.left >= 0 &&
      rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
      rect.right <= (window.innerWidth || document.documentElement.clientWidth)
    );
  }

  /**
   * Scroll element into view
   * @param {HTMLElement} element - Element to scroll to
   * @param {object} options - Scroll options
   */
  static scrollIntoView(element, options = { behavior: 'smooth', block: 'center' }) {
    if (!element) return;
    element.scrollIntoView(options);
  }

  /**
   * Get computed style of element
   * @param {HTMLElement} element - Target element
   * @param {string} property - CSS property name
   * @returns {string}
   */
  static getComputedStyle(element, property) {
    if (!element) return '';
    return window.getComputedStyle(element).getPropertyValue(property);
  }

  /**
   * Set multiple styles on element
   * @param {HTMLElement} element - Target element
   * @param {object} styles - Styles to set
   */
  static setStyles(element, styles) {
    if (!element) return;
    Object.entries(styles).forEach(([key, value]) => {
      element.style[key] = value;
    });
  }

  /**
   * Escape HTML special characters
   * @param {string} text - Text to escape
   * @returns {string}
   */
  static escapeHTML(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Debounce function execution
   * @param {function} func - Function to debounce
   * @param {number} wait - Wait time in milliseconds
   * @returns {function}
   */
  static debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }

  /**
   * Throttle function execution
   * @param {function} func - Function to throttle
   * @param {number} limit - Time limit in milliseconds
   * @returns {function}
   */
  static throttle(func, limit) {
    let inThrottle;
    return function (...args) {
      if (!inThrottle) {
        func.apply(this, args);
        inThrottle = true;
        setTimeout(() => (inThrottle = false), limit);
      }
    };
  }

  /**
   * Wait for element to appear in DOM
   * @param {string} selector - Element selector
   * @param {number} timeout - Timeout in milliseconds
   * @returns {Promise<HTMLElement>}
   */
  static waitForElement(selector, timeout = 5000) {
    return new Promise((resolve, reject) => {
      const element = document.querySelector(selector);
      if (element) {
        resolve(element);
        return;
      }

      const observer = new MutationObserver(() => {
        const element = document.querySelector(selector);
        if (element) {
          observer.disconnect();
          resolve(element);
        }
      });

      observer.observe(document.body, {
        childList: true,
        subtree: true,
      });

      setTimeout(() => {
        observer.disconnect();
        reject(new Error(`Element ${selector} not found within ${timeout}ms`));
      }, timeout);
    });
  }
}

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = DOMHelpers;
}
