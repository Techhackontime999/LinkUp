/**
 * Theme Manager
 * Manages light and dark theme switching with localStorage persistence
 * Requirements: 12.6, 12.7
 */

class ThemeManager {
  static STORAGE_KEY = 'social_platform_theme';
  static LIGHT_THEME = 'light';
  static DARK_THEME = 'dark';

  /**
   * Initialize theme manager
   */
  static init() {
    this._loadThemePreference();
    this._setupThemeToggle();
    this._setupSystemPreference();
  }

  /**
   * Load theme preference from localStorage or system preference
   * @private
   */
  static _loadThemePreference() {
    const savedTheme = this._getSavedTheme();
    const systemTheme = this._getSystemTheme();
    const theme = savedTheme || systemTheme || this.LIGHT_THEME;

    this.setTheme(theme);
  }

  /**
   * Get saved theme from localStorage
   * @private
   */
  static _getSavedTheme() {
    try {
      return localStorage.getItem(this.STORAGE_KEY);
    } catch (e) {
      console.error('Error reading theme from localStorage:', e);
      return null;
    }
  }

  /**
   * Get system theme preference
   * @private
   */
  static _getSystemTheme() {
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return this.DARK_THEME;
    }
    return this.LIGHT_THEME;
  }

  /**
   * Set theme
   * @param {string} theme - 'light' or 'dark'
   */
  static setTheme(theme) {
    if (theme !== this.LIGHT_THEME && theme !== this.DARK_THEME) {
      theme = this.LIGHT_THEME;
    }

    document.documentElement.setAttribute('data-theme', theme);
    this._saveTheme(theme);
    this._updateThemeToggle(theme);
    this._dispatchThemeChangeEvent(theme);
  }

  /**
   * Get current theme
   * @returns {string} Current theme ('light' or 'dark')
   */
  static getTheme() {
    return document.documentElement.getAttribute('data-theme') || this.LIGHT_THEME;
  }

  /**
   * Toggle between light and dark theme
   */
  static toggleTheme() {
    const currentTheme = this.getTheme();
    const newTheme = currentTheme === this.LIGHT_THEME ? this.DARK_THEME : this.LIGHT_THEME;
    this.setTheme(newTheme);
  }

  /**
   * Save theme to localStorage
   * @private
   */
  static _saveTheme(theme) {
    try {
      localStorage.setItem(this.STORAGE_KEY, theme);
    } catch (e) {
      console.error('Error saving theme to localStorage:', e);
    }
  }

  /**
   * Setup theme toggle button
   * @private
   */
  static _setupThemeToggle() {
    const toggleButton = document.querySelector('.theme-toggle');
    if (!toggleButton) return;

    toggleButton.addEventListener('click', () => {
      this.toggleTheme();
    });
  }

  /**
   * Update theme toggle button appearance
   * @private
   */
  static _updateThemeToggle(theme) {
    const toggleButton = document.querySelector('.theme-toggle');
    if (!toggleButton) return;

    const icon = toggleButton.querySelector('i');
    if (icon) {
      icon.className = theme === this.LIGHT_THEME ? 'fas fa-moon' : 'fas fa-sun';
    }

    const label = toggleButton.getAttribute('aria-label');
    if (label) {
      const newLabel = theme === this.LIGHT_THEME ? 'Switch to dark theme' : 'Switch to light theme';
      toggleButton.setAttribute('aria-label', newLabel);
    }
  }

  /**
   * Setup system preference listener
   * @private
   */
  static _setupSystemPreference() {
    if (!window.matchMedia) return;

    const darkModeQuery = window.matchMedia('(prefers-color-scheme: dark)');
    darkModeQuery.addEventListener('change', (e) => {
      // Only apply system preference if no saved preference
      if (!this._getSavedTheme()) {
        const theme = e.matches ? this.DARK_THEME : this.LIGHT_THEME;
        this.setTheme(theme);
      }
    });
  }

  /**
   * Dispatch theme change event
   * @private
   */
  static _dispatchThemeChangeEvent(theme) {
    const event = new CustomEvent('themeChange', {
      detail: { theme }
    });
    document.dispatchEvent(event);
  }

  /**
   * Get CSS variable value
   * @param {string} variableName - CSS variable name (without --)
   * @returns {string} CSS variable value
   */
  static getCSSVariable(variableName) {
    return getComputedStyle(document.documentElement)
      .getPropertyValue(`--${variableName}`)
      .trim();
  }

  /**
   * Set CSS variable value
   * @param {string} variableName - CSS variable name (without --)
   * @param {string} value - CSS variable value
   */
  static setCSSVariable(variableName, value) {
    document.documentElement.style.setProperty(`--${variableName}`, value);
  }

  /**
   * Get color palette for current theme
   * @returns {object} Color palette object
   */
  static getColorPalette() {
    const theme = this.getTheme();
    return {
      primary: this.getCSSVariable('primary-color'),
      secondary: this.getCSSVariable('secondary-color'),
      success: this.getCSSVariable('success-color'),
      danger: this.getCSSVariable('danger-color'),
      warning: this.getCSSVariable('warning-color'),
      info: this.getCSSVariable('info-color'),
      bgPrimary: this.getCSSVariable('bg-primary'),
      bgSecondary: this.getCSSVariable('bg-secondary'),
      textPrimary: this.getCSSVariable('text-primary'),
      textSecondary: this.getCSSVariable('text-secondary'),
      borderColor: this.getCSSVariable('border-color'),
      theme
    };
  }

  /**
   * Check if dark theme is active
   * @returns {boolean} True if dark theme is active
   */
  static isDarkTheme() {
    return this.getTheme() === this.DARK_THEME;
  }

  /**
   * Check if light theme is active
   * @returns {boolean} True if light theme is active
   */
  static isLightTheme() {
    return this.getTheme() === this.LIGHT_THEME;
  }

  /**
   * Verify color contrast ratio
   * @param {string} foreground - Foreground color
   * @param {string} background - Background color
   * @returns {object} Contrast info { ratio, wcagAA, wcagAAA }
   */
  static verifyContrast(foreground, background) {
    // This would use the AccessibilityUtils.getContrastRatio method
    // For now, we'll provide a placeholder
    return {
      ratio: 4.5,
      wcagAA: true,
      wcagAAA: false
    };
  }
}

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ThemeManager;
}
