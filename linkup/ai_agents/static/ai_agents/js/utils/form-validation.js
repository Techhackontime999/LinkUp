/**
 * Form Validation Utility
 * Provides real-time validation and error display
 * Requirements: 13.3, 13.7
 */

class FormValidation {
  /**
   * Validate a form
   * @param {HTMLElement} form - Form element
   * @returns {boolean} True if form is valid
   */
  static validateForm(form) {
    if (!form) return false;

    let isValid = true;
    const fields = form.querySelectorAll('input, textarea, select');

    fields.forEach((field) => {
      if (!this.validateField(field)) {
        isValid = false;
      }
    });

    return isValid;
  }

  /**
   * Validate a single field
   * @param {HTMLElement} field - Form field element
   * @returns {boolean} True if field is valid
   */
  static validateField(field) {
    if (!field) return true;

    const errors = this._getFieldErrors(field);

    if (errors.length > 0) {
      this._showFieldError(field, errors);
      return false;
    } else {
      this._clearFieldError(field);
      return true;
    }
  }

  /**
   * Get validation errors for a field
   * @private
   */
  static _getFieldErrors(field) {
    const errors = [];
    const value = field.value.trim();
    const type = field.type;
    const required = field.hasAttribute('required');
    const minLength = field.getAttribute('minlength');
    const maxLength = field.getAttribute('maxlength');
    const pattern = field.getAttribute('pattern');
    const customValidation = field.dataset.validate;

    // Required validation
    if (required && !value) {
      const label = this._getFieldLabel(field);
      errors.push(`${label} is required`);
      return errors;
    }

    if (!value) return errors;

    // Type validation
    if (type === 'email' && !this._isValidEmail(value)) {
      errors.push('Please enter a valid email address');
    }

    if (type === 'url' && !this._isValidURL(value)) {
      errors.push('Please enter a valid URL');
    }

    if (type === 'number') {
      const min = field.getAttribute('min');
      const max = field.getAttribute('max');

      if (min && parseFloat(value) < parseFloat(min)) {
        errors.push(`Value must be at least ${min}`);
      }

      if (max && parseFloat(value) > parseFloat(max)) {
        errors.push(`Value must be at most ${max}`);
      }
    }

    // Length validation
    if (minLength && value.length < parseInt(minLength)) {
      errors.push(`Minimum length is ${minLength} characters`);
    }

    if (maxLength && value.length > parseInt(maxLength)) {
      errors.push(`Maximum length is ${maxLength} characters`);
    }

    // Pattern validation
    if (pattern && !new RegExp(pattern).test(value)) {
      errors.push('Invalid format');
    }

    // Custom validation
    if (customValidation) {
      const customError = this._runCustomValidation(field, customValidation, value);
      if (customError) {
        errors.push(customError);
      }
    }

    return errors;
  }

  /**
   * Show field error
   * @private
   */
  static _showFieldError(field, errors) {
    field.classList.add('is-invalid');
    field.setAttribute('aria-invalid', 'true');

    let errorContainer = field.parentElement.querySelector('.error-message');
    if (!errorContainer) {
      errorContainer = document.createElement('div');
      errorContainer.className = 'error-message';
      errorContainer.setAttribute('role', 'alert');
      field.parentElement.appendChild(errorContainer);
    }

    errorContainer.innerHTML = errors.map((error) => `<p>${error}</p>`).join('');
    errorContainer.style.display = 'block';
  }

  /**
   * Clear field error
   * @private
   */
  static _clearFieldError(field) {
    field.classList.remove('is-invalid');
    field.setAttribute('aria-invalid', 'false');

    const errorContainer = field.parentElement.querySelector('.error-message');
    if (errorContainer) {
      errorContainer.style.display = 'none';
      errorContainer.innerHTML = '';
    }
  }

  /**
   * Get field label
   * @private
   */
  static _getFieldLabel(field) {
    const label = document.querySelector(`label[for="${field.id}"]`);
    if (label) {
      return label.textContent.replace('*', '').trim();
    }
    return field.name || field.id || 'This field';
  }

  /**
   * Validate email
   * @private
   */
  static _isValidEmail(email) {
    const emailRegex = /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/;
    return emailRegex.test(email);
  }

  /**
   * Validate URL
   * @private
   */
  static _isValidURL(url) {
    try {
      new URL(url);
      return true;
    } catch (e) {
      return false;
    }
  }

  /**
   * Run custom validation
   * @private
   */
  static _runCustomValidation(field, validationType, value) {
    const validations = {
      'password-strength': () => {
        if (value.length < 8) return 'Password must be at least 8 characters';
        if (!/[A-Z]/.test(value)) return 'Password must contain uppercase letter';
        if (!/[a-z]/.test(value)) return 'Password must contain lowercase letter';
        if (!/[0-9]/.test(value)) return 'Password must contain number';
        return null;
      },
      'match-field': () => {
        const matchFieldId = field.dataset.matchField;
        const matchField = document.getElementById(matchFieldId);
        if (matchField && value !== matchField.value) {
          return 'Fields do not match';
        }
        return null;
      },
      'unique-username': () => {
        // This would typically make an AJAX call
        return null;
      }
    };

    const validator = validations[validationType];
    return validator ? validator() : null;
  }

  /**
   * Setup real-time validation for a form
   * @param {HTMLElement} form - Form element
   */
  static setupRealtimeValidation(form) {
    if (!form) return;

    const fields = form.querySelectorAll('input, textarea, select');

    fields.forEach((field) => {
      // Validate on blur
      field.addEventListener('blur', () => {
        this.validateField(field);
      });

      // Validate on input (with debounce for performance)
      let timeout;
      field.addEventListener('input', () => {
        clearTimeout(timeout);
        timeout = setTimeout(() => {
          this.validateField(field);
        }, 300);
      });

      // Validate on change
      field.addEventListener('change', () => {
        this.validateField(field);
      });
    });

    // Prevent form submission if invalid
    form.addEventListener('submit', (e) => {
      if (!this.validateForm(form)) {
        e.preventDefault();
        this._focusFirstInvalidField(form);
      }
    });
  }

  /**
   * Focus first invalid field
   * @private
   */
  static _focusFirstInvalidField(form) {
    const invalidField = form.querySelector('.is-invalid');
    if (invalidField) {
      invalidField.focus();
      invalidField.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }

  /**
   * Add CSS for validation states
   */
  static addValidationStyles() {
    const style = document.createElement('style');
    style.textContent = `
      .form-control.is-invalid,
      .form-select.is-invalid {
        border-color: var(--danger-color);
        background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 12 12' width='12' height='12' fill='none' stroke='%23dc3545'%3e%3ccircle cx='6' cy='6' r='4.5'/%3e%3cpath fill='%23dc3545' d='M8 4a.5.5 0 0 0-.5-.5h-3a.5.5 0 0 0 0 1h3A.5.5 0 0 0 8 4z'/%3e%3c/svg%3e");
        background-repeat: no-repeat;
        background-position: right var(--spacing-sm) center;
        background-size: calc(var(--spacing-md) + var(--spacing-xs)) calc(var(--spacing-md) + var(--spacing-xs));
        padding-right: calc(1.5em + var(--spacing-md));
      }

      .form-control.is-invalid:focus,
      .form-select.is-invalid:focus {
        border-color: var(--danger-color);
        box-shadow: 0 0 0 0.2rem rgba(220, 53, 69, 0.25);
      }

      .error-message {
        color: var(--danger-color);
        font-size: 0.875rem;
        margin-top: var(--spacing-xs);
        display: none;
      }

      .error-message p {
        margin: 0;
        padding: var(--spacing-xs) 0;
      }

      .form-group {
        margin-bottom: var(--spacing-md);
      }

      .form-group label {
        display: block;
        margin-bottom: var(--spacing-xs);
        font-weight: 500;
      }

      .form-group label .required {
        color: var(--danger-color);
      }
    `;
    document.head.appendChild(style);
  }

  /**
   * Clear all validation errors in a form
   * @param {HTMLElement} form - Form element
   */
  static clearAllErrors(form) {
    if (!form) return;

    form.querySelectorAll('.is-invalid').forEach((field) => {
      this._clearFieldError(field);
    });
  }

  /**
   * Reset form to initial state
   * @param {HTMLElement} form - Form element
   */
  static resetForm(form) {
    if (!form) return;

    form.reset();
    this.clearAllErrors(form);
  }
}

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = FormValidation;
}
