/**
 * Formatting Utilities
 * Provides utilities for formatting dates, numbers, and text
 * Requirements: 7.6, 14.6
 */

class Formatters {
  /**
   * Format a date as relative time (e.g., "2 hours ago")
   * @param {Date|string} date - The date to format
   * @returns {string} Relative time string
   */
  static formatRelativeTime(date) {
    if (!date) return '';
    
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    if (isNaN(dateObj.getTime())) return '';
    
    const now = new Date();
    const seconds = Math.floor((now - dateObj) / 1000);
    
    if (seconds < 60) return 'just now';
    
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    
    const days = Math.floor(hours / 24);
    if (days < 7) return `${days}d ago`;
    
    const weeks = Math.floor(days / 7);
    if (weeks < 4) return `${weeks}w ago`;
    
    const months = Math.floor(days / 30);
    if (months < 12) return `${months}mo ago`;
    
    const years = Math.floor(months / 12);
    return `${years}y ago`;
  }

  /**
   * Format a number with K/M/B suffix (e.g., "1.2K followers")
   * @param {number} num - The number to format
   * @param {number} decimals - Number of decimal places (default: 1)
   * @returns {string} Formatted number string
   */
  static formatNumber(num, decimals = 1) {
    if (!Number.isFinite(num)) return '0';
    
    const absNum = Math.abs(num);
    
    if (absNum >= 1e9) {
      return (num / 1e9).toFixed(decimals) + 'B';
    }
    if (absNum >= 1e6) {
      return (num / 1e6).toFixed(decimals) + 'M';
    }
    if (absNum >= 1e3) {
      return (num / 1e3).toFixed(decimals) + 'K';
    }
    
    return num.toString();
  }

  /**
   * Truncate text with ellipsis
   * @param {string} text - The text to truncate
   * @param {number} maxLength - Maximum length before truncation
   * @param {string} ellipsis - Ellipsis string (default: "...")
   * @returns {string} Truncated text
   */
  static truncateText(text, maxLength, ellipsis = '...') {
    if (!text || typeof text !== 'string') return '';
    if (text.length <= maxLength) return text;
    
    return text.substring(0, maxLength - ellipsis.length) + ellipsis;
  }

  /**
   * Format a date as a readable string (e.g., "Jan 15, 2024")
   * @param {Date|string} date - The date to format
   * @returns {string} Formatted date string
   */
  static formatDate(date) {
    if (!date) return '';
    
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    if (isNaN(dateObj.getTime())) return '';
    
    const options = { year: 'numeric', month: 'short', day: 'numeric' };
    return dateObj.toLocaleDateString('en-US', options);
  }

  /**
   * Format a date and time (e.g., "Jan 15, 2024 at 2:30 PM")
   * @param {Date|string} date - The date to format
   * @returns {string} Formatted date and time string
   */
  static formatDateTime(date) {
    if (!date) return '';
    
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    if (isNaN(dateObj.getTime())) return '';
    
    const options = { 
      year: 'numeric', 
      month: 'short', 
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      meridiem: 'short'
    };
    return dateObj.toLocaleDateString('en-US', options);
  }

  /**
   * Format a number as currency
   * @param {number} amount - The amount to format
   * @param {string} currency - Currency code (default: "USD")
   * @returns {string} Formatted currency string
   */
  static formatCurrency(amount, currency = 'USD') {
    if (!Number.isFinite(amount)) return '$0.00';
    
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency
    }).format(amount);
  }

  /**
   * Format a percentage
   * @param {number} value - The value (0-1 or 0-100)
   * @param {number} decimals - Number of decimal places (default: 0)
   * @param {boolean} isDecimal - Whether value is 0-1 (default: true)
   * @returns {string} Formatted percentage string
   */
  static formatPercentage(value, decimals = 0, isDecimal = true) {
    if (!Number.isFinite(value)) return '0%';
    
    const percentage = isDecimal ? value * 100 : value;
    return percentage.toFixed(decimals) + '%';
  }
}

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = Formatters;
}
