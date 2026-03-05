/**
 * Auth Manager Module
 * 
 * Handles authentication, CSRF tokens, and session management.
 */

export class AuthManager {
  constructor() {
    this.csrfToken = this.getCSRFToken();
    this.sessionToken = this.getSessionToken();
  }

  /**
   * Get CSRF token from cookie
   */
  getCSRFToken() {
    const name = 'csrftoken';
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
      const [key, value] = cookie.trim().split('=');
      if (key === name) {
        return decodeURIComponent(value);
      }
    }
    return null;
  }

  /**
   * Get session token from cookie
   */
  getSessionToken() {
    const name = 'sessionid';
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
      const [key, value] = cookie.trim().split('=');
      if (key === name) {
        return decodeURIComponent(value);
      }
    }
    return null;
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated() {
    return this.sessionToken !== null;
  }

  /**
   * Validate session (check if still valid)
   */
  async validateSession() {
    try {
      const response = await fetch('/api/auth/validate/', {
        method: 'GET',
        credentials: 'same-origin',
      });
      return response.ok;
    } catch (error) {
      console.error('Session validation error:', error);
      return false;
    }
  }

  /**
   * Handle logout
   */
  logout() {
    window.location.href = '/logout/';
  }

  /**
   * Redirect to login page
   */
  redirectToLogin() {
    const currentPath = window.location.pathname;
    window.location.href = `/login/?next=${encodeURIComponent(currentPath)}`;
  }
}

// Export singleton instance
export const authManager = new AuthManager();
