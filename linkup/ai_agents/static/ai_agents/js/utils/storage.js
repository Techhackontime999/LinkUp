/**
 * LocalStorage Wrapper
 * Provides safe get/set methods with error handling and JSON serialization
 * Requirements: 9.5, 9.6
 */

class StorageManager {
  /**
   * Storage quota in bytes (5MB default for most browsers)
   */
  static QUOTA_BYTES = 5 * 1024 * 1024;

  /**
   * Safely get a value from localStorage
   * @param {string} key - The storage key
   * @param {*} defaultValue - Default value if key doesn't exist or error occurs
   * @returns {*} The stored value or default value
   */
  static get(key, defaultValue = null) {
    try {
      if (!this._isStorageAvailable()) {
        return defaultValue;
      }

      const item = localStorage.getItem(key);
      if (item === null) {
        return defaultValue;
      }

      // Try to parse as JSON
      try {
        return JSON.parse(item);
      } catch (e) {
        // If not JSON, return as string
        return item;
      }
    } catch (error) {
      console.error(`Error reading from localStorage (key: ${key}):`, error);
      return defaultValue;
    }
  }

  /**
   * Safely set a value in localStorage
   * @param {string} key - The storage key
   * @param {*} value - The value to store (will be JSON serialized)
   * @returns {boolean} True if successful, false otherwise
   */
  static set(key, value) {
    try {
      if (!this._isStorageAvailable()) {
        console.warn('localStorage is not available');
        return false;
      }

      // Check quota before storing
      if (!this._checkQuota(key, value)) {
        console.warn(`Storage quota exceeded for key: ${key}`);
        return false;
      }

      const serialized = typeof value === 'string' ? value : JSON.stringify(value);
      localStorage.setItem(key, serialized);
      return true;
    } catch (error) {
      if (error.name === 'QuotaExceededError') {
        console.error(`Storage quota exceeded for key: ${key}`);
      } else {
        console.error(`Error writing to localStorage (key: ${key}):`, error);
      }
      return false;
    }
  }

  /**
   * Remove a value from localStorage
   * @param {string} key - The storage key
   * @returns {boolean} True if successful, false otherwise
   */
  static remove(key) {
    try {
      if (!this._isStorageAvailable()) {
        return false;
      }

      localStorage.removeItem(key);
      return true;
    } catch (error) {
      console.error(`Error removing from localStorage (key: ${key}):`, error);
      return false;
    }
  }

  /**
   * Clear all items from localStorage
   * @returns {boolean} True if successful, false otherwise
   */
  static clear() {
    try {
      if (!this._isStorageAvailable()) {
        return false;
      }

      localStorage.clear();
      return true;
    } catch (error) {
      console.error('Error clearing localStorage:', error);
      return false;
    }
  }

  /**
   * Get all keys from localStorage
   * @returns {string[]} Array of storage keys
   */
  static keys() {
    try {
      if (!this._isStorageAvailable()) {
        return [];
      }

      return Object.keys(localStorage);
    } catch (error) {
      console.error('Error getting localStorage keys:', error);
      return [];
    }
  }

  /**
   * Check if a key exists in localStorage
   * @param {string} key - The storage key
   * @returns {boolean} True if key exists, false otherwise
   */
  static has(key) {
    try {
      if (!this._isStorageAvailable()) {
        return false;
      }

      return localStorage.getItem(key) !== null;
    } catch (error) {
      console.error(`Error checking localStorage key (${key}):`, error);
      return false;
    }
  }

  /**
   * Get the current storage usage
   * @returns {object} Object with { used: bytes, available: bytes, percentage: 0-100 }
   */
  static getUsage() {
    try {
      if (!this._isStorageAvailable()) {
        return { used: 0, available: this.QUOTA_BYTES, percentage: 0 };
      }

      let used = 0;
      for (let key in localStorage) {
        if (localStorage.hasOwnProperty(key)) {
          used += key.length + localStorage[key].length;
        }
      }

      const available = this.QUOTA_BYTES - used;
      const percentage = (used / this.QUOTA_BYTES) * 100;

      return {
        used,
        available: Math.max(0, available),
        percentage: Math.min(100, percentage)
      };
    } catch (error) {
      console.error('Error calculating storage usage:', error);
      return { used: 0, available: this.QUOTA_BYTES, percentage: 0 };
    }
  }

  /**
   * Check if storage is available and not full
   * @returns {boolean} True if storage is available, false otherwise
   */
  static isAvailable() {
    return this._isStorageAvailable();
  }

  /**
   * Private: Check if localStorage is available
   * @returns {boolean}
   */
  static _isStorageAvailable() {
    try {
      const test = '__storage_test__';
      localStorage.setItem(test, test);
      localStorage.removeItem(test);
      return true;
    } catch (e) {
      return false;
    }
  }

  /**
   * Private: Check if storing a value would exceed quota
   * @param {string} key - The storage key
   * @param {*} value - The value to store
   * @returns {boolean} True if within quota, false otherwise
   */
  static _checkQuota(key, value) {
    try {
      const serialized = typeof value === 'string' ? value : JSON.stringify(value);
      const size = key.length + serialized.length;
      const usage = this.getUsage();

      return size <= usage.available;
    } catch (error) {
      console.error('Error checking quota:', error);
      return false;
    }
  }
}

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = StorageManager;
}
