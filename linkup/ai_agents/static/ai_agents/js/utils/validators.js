/**
 * Validation Utilities
 * Provides form validation helpers for email, URL, character count, etc.
 * Requirements: 3.5, 16.7
 */

class Validators {
  /**
   * Validate email address
   * @param {string} email - Email to validate
   * @returns {boolean}
   */
  static isValidEmail(email) {
    if (!email || typeof email !== 'string') return false;

    // RFC 5322 simplified regex
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  }

  /**
   * Validate URL
   * @param {string} url - URL to validate
   * @returns {boolean}
   */
  static isValidURL(url) {
    if (!url || typeof url !== 'string') return false;

    try {
      new URL(url);
      return true;
    } catch (error) {
      return false;
    }
  }

  /**
   * Validate URL with optional protocol
   * @param {string} url - URL to validate
   * @returns {boolean}
   */
  static isValidURLWithoutProtocol(url) {
    if (!url || typeof url !== 'string') return false;

    // Try with https protocol
    try {
      new URL(`https://${url}`);
      return true;
    } catch (error) {
      return false;
    }
  }

  /**
   * Validate character count
   * @param {string} text - Text to validate
   * @param {number} minLength - Minimum length (optional)
   * @param {number} maxLength - Maximum length (optional)
   * @returns {object} Validation result
   */
  static validateCharacterCount(text, minLength = 0, maxLength = Infinity) {
    const length = text ? text.length : 0;

    return {
      isValid: length >= minLength && length <= maxLength,
      length: length,
      minLength: minLength,
      maxLength: maxLength,
      remaining: Math.max(0, maxLength - length),
      tooShort: length < minLength,
      tooLong: length > maxLength,
    };
  }

  /**
   * Validate required field
   * @param {string} value - Value to validate
   * @returns {boolean}
   */
  static isRequired(value) {
    if (typeof value === 'string') {
      return value.trim().length > 0;
    }
    return value !== null && value !== undefined && value !== '';
  }

  /**
   * Validate minimum length
   * @param {string} value - Value to validate
   * @param {number} minLength - Minimum length
   * @returns {boolean}
   */
  static minLength(value, minLength) {
    if (!value) return false;
    return value.length >= minLength;
  }

  /**
   * Validate maximum length
   * @param {string} value - Value to validate
   * @param {number} maxLength - Maximum length
   * @returns {boolean}
   */
  static maxLength(value, maxLength) {
    if (!value) return true;
    return value.length <= maxLength;
  }

  /**
   * Validate number
   * @param {any} value - Value to validate
   * @param {number} min - Minimum value (optional)
   * @param {number} max - Maximum value (optional)
   * @returns {boolean}
   */
  static isValidNumber(value, min = -Infinity, max = Infinity) {
    const num = Number(value);
    if (isNaN(num)) return false;
    return num >= min && num <= max;
  }

  /**
   * Validate integer
   * @param {any} value - Value to validate
   * @returns {boolean}
   */
  static isValidInteger(value) {
    return Number.isInteger(Number(value));
  }

  /**
   * Validate phone number (basic)
   * @param {string} phone - Phone number to validate
   * @returns {boolean}
   */
  static isValidPhone(phone) {
    if (!phone || typeof phone !== 'string') return false;

    // Remove common separators
    const cleaned = phone.replace(/[\s\-\(\)\.]/g, '');

    // Check if it's all digits and has reasonable length
    return /^\d{7,15}$/.test(cleaned);
  }

  /**
   * Validate password strength
   * @param {string} password - Password to validate
   * @returns {object} Validation result with strength level
   */
  static validatePasswordStrength(password) {
    if (!password) {
      return {
        isValid: false,
        strength: 'none',
        score: 0,
        feedback: 'Password is required',
      };
    }

    let score = 0;
    const feedback = [];

    // Length checks
    if (password.length >= 8) score += 1;
    if (password.length >= 12) score += 1;
    if (password.length >= 16) score += 1;

    // Character type checks
    if (/[a-z]/.test(password)) score += 1;
    if (/[A-Z]/.test(password)) score += 1;
    if (/\d/.test(password)) score += 1;
    if (/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) score += 1;

    // Feedback
    if (password.length < 8) feedback.push('At least 8 characters');
    if (!/[a-z]/.test(password)) feedback.push('At least one lowercase letter');
    if (!/[A-Z]/.test(password)) feedback.push('At least one uppercase letter');
    if (!/\d/.test(password)) feedback.push('At least one number');
    if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) feedback.push('At least one special character');

    let strength = 'weak';
    if (score >= 5) strength = 'strong';
    else if (score >= 3) strength = 'medium';

    return {
      isValid: score >= 3,
      strength: strength,
      score: score,
      feedback: feedback,
    };
  }

  /**
   * Validate username
   * @param {string} username - Username to validate
   * @returns {boolean}
   */
  static isValidUsername(username) {
    if (!username || typeof username !== 'string') return false;

    // Alphanumeric, underscore, hyphen, 3-20 characters
    return /^[a-zA-Z0-9_-]{3,20}$/.test(username);
  }

  /**
   * Validate slug (URL-friendly string)
   * @param {string} slug - Slug to validate
   * @returns {boolean}
   */
  static isValidSlug(slug) {
    if (!slug || typeof slug !== 'string') return false;

    // Lowercase alphanumeric and hyphens only
    return /^[a-z0-9-]+$/.test(slug);
  }

  /**
   * Validate hex color
   * @param {string} color - Color to validate
   * @returns {boolean}
   */
  static isValidHexColor(color) {
    if (!color || typeof color !== 'string') return false;

    return /^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$/.test(color);
  }

  /**
   * Validate date string (YYYY-MM-DD)
   * @param {string} dateString - Date string to validate
   * @returns {boolean}
   */
  static isValidDate(dateString) {
    if (!dateString || typeof dateString !== 'string') return false;

    const date = new Date(dateString);
    return date instanceof Date && !isNaN(date);
  }

  /**
   * Validate date range
   * @param {string} startDate - Start date
   * @param {string} endDate - End date
   * @returns {boolean}
   */
  static isValidDateRange(startDate, endDate) {
    if (!this.isValidDate(startDate) || !this.isValidDate(endDate)) return false;

    const start = new Date(startDate);
    const end = new Date(endDate);

    return start <= end;
  }

  /**
   * Validate JSON string
   * @param {string} jsonString - JSON string to validate
   * @returns {boolean}
   */
  static isValidJSON(jsonString) {
    if (!jsonString || typeof jsonString !== 'string') return false;

    try {
      JSON.parse(jsonString);
      return true;
    } catch (error) {
      return false;
    }
  }

  /**
   * Validate credit card number (Luhn algorithm)
   * @param {string} cardNumber - Card number to validate
   * @returns {boolean}
   */
  static isValidCreditCard(cardNumber) {
    if (!cardNumber || typeof cardNumber !== 'string') return false;

    const cleaned = cardNumber.replace(/\s/g, '');
    if (!/^\d{13,19}$/.test(cleaned)) return false;

    // Luhn algorithm
    let sum = 0;
    let isEven = false;

    for (let i = cleaned.length - 1; i >= 0; i--) {
      let digit = parseInt(cleaned[i], 10);

      if (isEven) {
        digit *= 2;
        if (digit > 9) {
          digit -= 9;
        }
      }

      sum += digit;
      isEven = !isEven;
    }

    return sum % 10 === 0;
  }

  /**
   * Validate form field
   * @param {HTMLElement} field - Form field element
   * @returns {object} Validation result
   */
  static validateField(field) {
    if (!field) {
      return { isValid: false, errors: ['Field not found'] };
    }

    const errors = [];
    const value = field.value || '';
    const type = field.type || field.getAttribute('data-type');
    const required = field.hasAttribute('required');
    const minLength = field.getAttribute('minlength');
    const maxLength = field.getAttribute('maxlength');
    const pattern = field.getAttribute('pattern');

    // Check required
    if (required && !this.isRequired(value)) {
      errors.push('This field is required');
    }

    // Check type-specific validation
    if (value) {
      switch (type) {
        case 'email':
          if (!this.isValidEmail(value)) {
            errors.push('Please enter a valid email address');
          }
          break;
        case 'url':
          if (!this.isValidURL(value) && !this.isValidURLWithoutProtocol(value)) {
            errors.push('Please enter a valid URL');
          }
          break;
        case 'number':
          if (!this.isValidNumber(value)) {
            errors.push('Please enter a valid number');
          }
          break;
        case 'tel':
          if (!this.isValidPhone(value)) {
            errors.push('Please enter a valid phone number');
          }
          break;
        case 'date':
          if (!this.isValidDate(value)) {
            errors.push('Please enter a valid date');
          }
          break;
      }
    }

    // Check length
    if (minLength && value.length < parseInt(minLength)) {
      errors.push(`Minimum length is ${minLength} characters`);
    }

    if (maxLength && value.length > parseInt(maxLength)) {
      errors.push(`Maximum length is ${maxLength} characters`);
    }

    // Check pattern
    if (pattern && value && !new RegExp(pattern).test(value)) {
      errors.push('Please match the required format');
    }

    return {
      isValid: errors.length === 0,
      errors: errors,
      value: value,
    };
  }

  /**
   * Validate entire form
   * @param {HTMLFormElement} form - Form element
   * @returns {object} Validation result
   */
  static validateForm(form) {
    if (!form || !(form instanceof HTMLFormElement)) {
      return { isValid: false, errors: {} };
    }

    const errors = {};
    const fields = form.querySelectorAll('input, textarea, select');

    fields.forEach((field) => {
      const result = this.validateField(field);
      if (!result.isValid) {
        const fieldName = field.name || field.id || 'unknown';
        errors[fieldName] = result.errors;
      }
    });

    return {
      isValid: Object.keys(errors).length === 0,
      errors: errors,
    };
  }

  /**
   * Sanitize input to prevent XSS
   * @param {string} input - Input to sanitize
   * @returns {string}
   */
  static sanitizeInput(input) {
    if (!input || typeof input !== 'string') return '';

    const div = document.createElement('div');
    div.textContent = input;
    return div.innerHTML;
  }

  /**
   * Validate and sanitize email
   * @param {string} email - Email to validate and sanitize
   * @returns {object}
   */
  static validateAndSanitizeEmail(email) {
    const sanitized = this.sanitizeInput(email).toLowerCase().trim();
    return {
      isValid: this.isValidEmail(sanitized),
      value: sanitized,
    };
  }

  /**
   * Validate and sanitize URL
   * @param {string} url - URL to validate and sanitize
   * @returns {object}
   */
  static validateAndSanitizeURL(url) {
    const sanitized = this.sanitizeInput(url).trim();
    const isValid = this.isValidURL(sanitized) || this.isValidURLWithoutProtocol(sanitized);

    return {
      isValid: isValid,
      value: sanitized,
    };
  }
}

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = Validators;
}
