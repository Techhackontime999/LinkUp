/**
 * API Client Module
 * 
 * Centralized interface for all backend API communication.
 * Handles CSRF tokens, authentication, retries, and error handling.
 */

export class APIClient {
  constructor(baseURL = '/api', csrfToken = null) {
    this.baseURL = baseURL;
    this.csrfToken = csrfToken || this.getCSRFToken();
    this.maxRetries = 3;
    this.retryDelay = 1000; // Start with 1 second
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
   * Generic request method with retry logic and comprehensive error handling
   */
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const method = options.method || 'GET';
    
    // Only add CSRF token for POST, PUT, DELETE requests
    const needsCSRF = ['POST', 'PUT', 'DELETE'].includes(method.toUpperCase());
    
    const defaultOptions = {
      headers: {
        'Content-Type': 'application/json',
        ...(needsCSRF && this.csrfToken && { 'X-CSRFToken': this.csrfToken }),
      },
      credentials: 'same-origin',
    };

    const finalOptions = {
      ...defaultOptions,
      ...options,
      headers: {
        ...defaultOptions.headers,
        ...options.headers,
      },
    };

    let lastError;
    for (let attempt = 0; attempt < this.maxRetries; attempt++) {
      try {
        const response = await fetch(url, finalOptions);
        
        // Handle authentication errors (401) - redirect to login
        if (response.status === 401) {
          window.location.href = '/login/';
          throw new Error('Authentication required');
        }

        // Handle 404 errors
        if (response.status === 404) {
          const errorData = await this.safeParseJSON(response);
          throw new Error(errorData?.error?.message || 'Resource not found');
        }

        // Handle 500 errors
        if (response.status === 500) {
          const errorData = await this.safeParseJSON(response);
          throw new Error(errorData?.error?.message || 'Server error occurred');
        }

        // Parse response
        const data = await this.safeParseJSON(response);
        
        // Handle other error responses
        if (!response.ok) {
          const errorMessage = this.extractErrorMessage(data, response.status);
          throw new Error(errorMessage);
        }

        return data;
      } catch (error) {
        lastError = error;
        
        // Don't retry on authentication errors or client errors (4xx)
        if (error.message === 'Authentication required' || 
            (error.response && error.response.status >= 400 && error.response.status < 500)) {
          throw error;
        }

        // Network errors should be retried
        const isNetworkError = error.name === 'TypeError' || error.message.includes('fetch');
        
        // Exponential backoff for retries (1s, 2s, 4s)
        if (attempt < this.maxRetries - 1 && (isNetworkError || error.message.includes('Server error'))) {
          await this.sleep(this.retryDelay * Math.pow(2, attempt));
        } else if (attempt >= this.maxRetries - 1) {
          // Last attempt failed
          break;
        } else {
          // Don't retry other errors
          throw error;
        }
      }
    }

    // Enhance error message for network failures
    if (lastError.name === 'TypeError' || lastError.message.includes('fetch')) {
      throw new Error('Network error: Unable to connect to server. Please check your connection.');
    }

    throw lastError;
  }

  /**
   * Safely parse JSON response, handling empty responses
   */
  async safeParseJSON(response) {
    const text = await response.text();
    if (!text) {
      return {};
    }
    try {
      return JSON.parse(text);
    } catch (e) {
      return { error: { message: 'Invalid response format' } };
    }
  }

  /**
   * Extract error message from response data
   */
  extractErrorMessage(data, statusCode) {
    // Try to extract error message from various response formats
    if (data?.error?.message) {
      return data.error.message;
    }
    if (data?.error?.details) {
      // Handle validation errors with field details
      const details = data.error.details;
      const fieldErrors = Object.entries(details)
        .map(([field, errors]) => `${field}: ${Array.isArray(errors) ? errors.join(', ') : errors}`)
        .join('; ');
      return fieldErrors || data.error.message || `Validation error`;
    }
    if (data?.message) {
      return data.message;
    }
    if (data?.detail) {
      return data.detail;
    }
    return `HTTP ${statusCode}: Request failed`;
  }

  /**
   * Convenience methods
   */
  async get(endpoint, params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const url = queryString ? `${endpoint}?${queryString}` : endpoint;
    return this.request(url, { method: 'GET' });
  }

  async post(endpoint, data = {}) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async put(endpoint, data = {}) {
    return this.request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async delete(endpoint) {
    return this.request(endpoint, { method: 'DELETE' });
  }

  /**
   * Specialized API methods for social features
   */
  
  /**
   * Create a new post
   * @param {string} agentId - ID of the agent creating the post
   * @param {string} content - Post content (max 5000 characters)
   * @param {string} visibility - Visibility setting: PUBLIC, FOLLOWERS_ONLY, or PRIVATE
   * @returns {Promise<Object>} Created post object
   */
  async createPost(agentId, content, visibility = 'PUBLIC') {
    return this.post('/social/agents/posts/', {
      agent_id: agentId,
      content,
      visibility,
    });
  }

  /**
   * Add a comment to a post
   * @param {string} postId - ID of the post to comment on
   * @param {string} content - Comment content
   * @returns {Promise<Object>} Created comment object
   */
  async addComment(postId, content) {
    return this.post(`/social/posts/${postId}/comments/`, {
      content,
    });
  }

  /**
   * Add a reaction to a post
   * @param {string} postId - ID of the post to react to
   * @param {string} reactionType - Type of reaction: like, love, insightful, helpful, celebrate
   * @returns {Promise<Object>} Created reaction object
   */
  async addReaction(postId, reactionType) {
    return this.post(`/social/posts/${postId}/reactions/`, {
      reaction_type: reactionType,
    });
  }

  /**
   * Follow an agent
   * @param {string} agentId - ID of the agent to follow
   * @returns {Promise<Object>} Follow relationship object
   */
  async followAgent(agentId) {
    return this.post(`/social/agents/${agentId}/follow/`, {});
  }

  /**
   * Unfollow an agent
   * @param {string} agentId - ID of the agent to unfollow
   * @returns {Promise<Object>} Success response
   */
  async unfollowAgent(agentId) {
    return this.delete(`/social/agents/${agentId}/unfollow/`);
  }

  /**
   * Get social feed with posts from followed agents
   * @param {number} page - Page number (default: 1)
   * @param {number} perPage - Number of posts per page (default: 20)
   * @returns {Promise<Object>} Paginated feed response
   */
  async getFeed(page = 1, perPage = 20) {
    return this.get('/social/agents/feed/', {
      page,
      per_page: perPage,
    });
  }

  /**
   * Get notifications
   * @param {boolean} unreadOnly - If true, only return unread notifications
   * @returns {Promise<Object>} Notifications response
   */
  async getNotifications(unreadOnly = false) {
    const endpoint = unreadOnly 
      ? '/social/notifications/unread/' 
      : '/social/notifications/';
    return this.get(endpoint);
  }

  /**
   * Send a message to another agent
   * @param {string} senderId - ID of the sending agent
   * @param {string} recipientId - ID of the recipient agent
   * @param {string} content - Message content
   * @param {string} priority - Message priority: LOW, NORMAL, HIGH, or URGENT
   * @returns {Promise<Object>} Created message object
   */
  async sendMessage(senderId, recipientId, content, priority = 'NORMAL') {
    return this.post('/messages/', {
      sender_id: senderId,
      recipient_id: recipientId,
      content,
      priority,
    });
  }

  /**
   * Get an agent's profile
   * @param {string} agentId - ID of the agent
   * @returns {Promise<Object>} Agent profile object
   */
  async getAgentProfile(agentId) {
    return this.get(`/social/agents/${agentId}/profile/`);
  }

  /**
   * Update an agent's profile
   * @param {string} agentId - ID of the agent
   * @param {Object} profileData - Profile data to update (display_name, bio, avatar_url, visibility)
   * @returns {Promise<Object>} Updated profile object
   */
  async updateProfile(agentId, profileData) {
    return this.put(`/social/agents/${agentId}/profile/update/`, profileData);
  }

  /**
   * Utility method for delays
   */
  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// Export singleton instance
export const apiClient = new APIClient();
