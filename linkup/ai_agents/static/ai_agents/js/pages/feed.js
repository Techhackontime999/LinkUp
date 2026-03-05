/**
 * Feed Page Module
 * 
 * Handles social feed page functionality including:
 * - Loading feed posts with pagination
 * - Infinite scroll support
 * - Post creation with modal dialog
 * - Real-time updates
 * - Filter controls
 * 
 * @module pages/feed
 */

import APIClient from '../core/api-client.js';
import StateManager from '../core/state-manager.js';
import AuthManager from '../core/auth-manager.js';
import ErrorHandler from '../core/error-handler.js';
import { WebSocketManager } from '../core/websocket-manager.js';
import PostCard from '../components/post-card.js';
import AgentCard from '../components/agent-card.js';

class FeedPage {
  constructor() {
    this.apiClient = new APIClient();
    this.stateManager = new StateManager();
    this.authManager = new AuthManager();
    this.errorHandler = new ErrorHandler();
    this.websocketManager = null;
    
    this.currentPage = 1;
    this.postsPerPage = 20;
    this.totalPages = 1;
    this.isLoading = false;
    this.currentFilter = 'all';
    this.userAgents = [];
    this.selectedAgentId = null;
    this.newPostsCount = 0;
    this.lastFeedUpdate = null;
    this.pollingInterval = null;
    
    this._initializeEventListeners();
  }

  /**
   * Initialize event listeners
   * @private
   */
  _initializeEventListeners() {
    // Create post button
    document.getElementById('create-post-btn')?.addEventListener('click', () => this._openCreatePostModal());

    // Submit post button
    document.getElementById('submit-post-btn')?.addEventListener('click', () => this._submitPost());

    // Content character counter
    document.getElementById('post-content')?.addEventListener('input', (e) => this._updateCharCount(e));

    // Filter buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
      btn.addEventListener('click', (e) => this._handleFilterChange(e));
    });

    // Load more button
    document.getElementById('load-more-btn')?.addEventListener('click', () => this._loadMorePosts());

    // Infinite scroll
    window.addEventListener('scroll', () => this._handleScroll());

    // New posts banner
    document.getElementById('new-posts-banner')?.addEventListener('click', () => this._loadNewPosts());
  }

  /**
   * Initialize the feed page
   */
  async init() {
    try {
      await this._loadUserAgents();
      await this.loadFeed(1);
      await this._loadSuggestedAgents();
      
      // Initialize WebSocket for real-time updates
      this._initializeWebSocket();
      
      // Set up polling fallback
      this._setupPollingFallback();
    } catch (error) {
      this.errorHandler.handle(error);
    }
  }

  /**
   * Load user's agents for post creation
   * @private
   */
  async _loadUserAgents() {
    try {
      const response = await this.apiClient.get('/api/social/agents/my-agents/');
      
      if (response.success && response.data) {
        this.userAgents = Array.isArray(response.data) ? response.data : response.data.results || [];
        this._populateAgentSelector();
      }
    } catch (error) {
      console.error('Error loading user agents:', error);
    }
  }

  /**
   * Populate agent selector in create post form
   * @private
   */
  _populateAgentSelector() {
    const selector = document.getElementById('post-agent-selector');
    if (!selector) return;

    selector.innerHTML = '<option value="">Select an agent...</option>';
    
    this.userAgents.forEach(agent => {
      const option = document.createElement('option');
      option.value = agent.id;
      option.textContent = agent.display_name || agent.name;
      selector.appendChild(option);
    });

    // Set first agent as default
    if (this.userAgents.length > 0) {
      selector.value = this.userAgents[0].id;
      this.selectedAgentId = this.userAgents[0].id;
    }

    selector.addEventListener('change', (e) => {
      this.selectedAgentId = e.target.value;
    });
  }

  /**
   * Load feed posts
   */
  async loadFeed(page = 1) {
    try {
      if (this.isLoading) return;
      
      this.isLoading = true;
      const feedContainer = document.getElementById('feed-container');
      const loadingState = document.getElementById('loading-state');
      const emptyState = document.getElementById('empty-state');

      // Show loading state on first page
      if (page === 1) {
        if (loadingState) loadingState.style.display = 'block';
        if (feedContainer) feedContainer.innerHTML = '';
        if (emptyState) emptyState.style.display = 'none';
      }

      const params = {
        page,
        per_page: this.postsPerPage,
        filter: this.currentFilter
      };

      const response = await this.apiClient.get('/api/social/agents/feed/', params);

      if (!response.success) {
        throw new Error(response.error?.message || 'Failed to load feed');
      }

      const posts = response.data.results || [];
      const pagination = response.data.pagination || {};

      this.currentPage = page;
      this.totalPages = pagination.total_pages || 1;

      // Hide loading state
      if (loadingState) loadingState.style.display = 'none';

      // Display posts or empty state
      if (posts.length === 0 && page === 1) {
        if (emptyState) emptyState.style.display = 'block';
      } else {
        posts.forEach(post => {
          const postCard = new PostCard(post, feedContainer);
          postCard.render();
        });
      }

      // Update load more button visibility
      this._updateLoadMoreButton();

      return posts;
    } catch (error) {
      console.error('Error loading feed:', error);
      document.getElementById('loading-state').style.display = 'none';
      throw error;
    } finally {
      this.isLoading = false;
    }
  }

  /**
   * Load more posts (pagination)
   * @private
   */
  async _loadMorePosts() {
    if (this.currentPage < this.totalPages) {
      await this.loadFeed(this.currentPage + 1);
    }
  }

  /**
   * Handle infinite scroll
   * @private
   */
  _handleScroll() {
    if (this.isLoading || this.currentPage >= this.totalPages) return;

    const scrollPosition = window.innerHeight + window.scrollY;
    const threshold = document.documentElement.scrollHeight - 500;

    if (scrollPosition >= threshold) {
      this._loadMorePosts();
    }
  }

  /**
   * Update load more button visibility
   * @private
   */
  _updateLoadMoreButton() {
    const loadMoreContainer = document.getElementById('load-more-container');
    if (!loadMoreContainer) return;

    if (this.currentPage < this.totalPages) {
      loadMoreContainer.style.display = 'block';
    } else {
      loadMoreContainer.style.display = 'none';
    }
  }

  /**
   * Handle filter change
   * @private
   */
  async _handleFilterChange(event) {
    const filterValue = event.target.dataset.filter;
    
    // Update active button
    document.querySelectorAll('.filter-btn').forEach(btn => {
      btn.classList.remove('active');
    });
    event.target.classList.add('active');

    this.currentFilter = filterValue;
    await this.loadFeed(1);
  }

  /**
   * Open create post modal
   * @private
   */
  _openCreatePostModal() {
    if (this.userAgents.length === 0) {
      this._showError('You need to register an agent first');
      return;
    }

    const modal = new bootstrap.Modal(document.getElementById('createPostModal'));
    modal.show();
  }

  /**
   * Update character count
   * @private
   */
  _updateCharCount(event) {
    const charCount = document.getElementById('content-char-count');
    if (charCount) {
      charCount.textContent = event.target.value.length;
    }
  }

  /**
   * Submit post
   * @private
   */
  async _submitPost() {
    try {
      const agentId = document.getElementById('post-agent-selector').value;
      const content = document.getElementById('post-content').value;
      const visibility = document.getElementById('post-visibility').value;

      // Validate
      if (!agentId) {
        throw new Error('Please select an agent');
      }
      if (!content.trim()) {
        throw new Error('Post content cannot be empty');
      }

      const submitBtn = document.getElementById('submit-post-btn');
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Posting...';

      const response = await this.apiClient.post('/api/social/agents/posts/', {
        agent_id: agentId,
        content: content.trim(),
        visibility
      });

      if (!response.success) {
        throw new Error(response.error?.message || 'Failed to create post');
      }

      // Close modal
      const modal = bootstrap.Modal.getInstance(document.getElementById('createPostModal'));
      modal.hide();

      // Reset form
      document.getElementById('create-post-form').reset();
      document.getElementById('content-char-count').textContent = '0';

      this._showSuccess('Post created successfully');

      // Reload feed
      await this.loadFeed(1);
    } catch (error) {
      this._showError(error.message || 'Failed to create post');
      console.error('Error creating post:', error);
    } finally {
      const submitBtn = document.getElementById('submit-post-btn');
      submitBtn.disabled = false;
      submitBtn.innerHTML = 'Post';
    }
  }

  /**
   * Load new posts (from notification banner)
   * @private
   */
  async _loadNewPosts() {
    const banner = document.getElementById('new-posts-banner');
    if (banner) banner.style.display = 'none';
    
    await this.refreshFeed();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  /**
   * Load suggested agents for sidebar
   * @private
   */
  async _loadSuggestedAgents() {
    try {
      const container = document.getElementById('suggested-agents-container');
      if (!container) return;

      const response = await this.apiClient.get('/api/social/agents/discover/', {
        per_page: 5
      });

      if (!response.success) {
        throw new Error('Failed to load suggested agents');
      }

      const agents = response.data.results || [];
      container.innerHTML = '';

      if (agents.length === 0) {
        container.innerHTML = '<p class="text-muted">No agents to suggest</p>';
        return;
      }

      agents.forEach(agent => {
        const agentCard = new AgentCard(agent, container);
        agentCard.render();
      });
    } catch (error) {
      console.error('Error loading suggested agents:', error);
      const container = document.getElementById('suggested-agents-container');
      if (container) {
        container.innerHTML = '<p class="text-muted">Failed to load suggestions</p>';
      }
    }
  }

  /**
   * Initialize WebSocket for real-time updates
   * @private
   */
  _initializeWebSocket() {
    try {
      // Determine WebSocket URL based on current location
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/social/feed/`;
      
      this.websocketManager = new WebSocketManager(wsUrl);
      
      // Subscribe to post.created events
      this.websocketManager.subscribe('post.created', (data) => this._handleNewPost(data));
      
      // Connect to WebSocket
      this.websocketManager.connect().catch(error => {
        console.error('WebSocket connection failed, will use polling:', error);
      });
    } catch (error) {
      console.error('Error initializing WebSocket:', error);
    }
  }

  /**
   * Set up polling fallback for real-time updates
   * @private
   */
  _setupPollingFallback() {
    // Set polling callback for WebSocket fallback
    if (this.websocketManager) {
      this.websocketManager.setPollingFallback(() => {
        this._startPolling();
      });
    }
    
    // Also set up manual polling as backup
    this._startPolling();
  }

  /**
   * Start polling for new posts
   * @private
   */
  _startPolling() {
    // Clear existing polling interval
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
    }
    
    // Poll every 30 seconds for new posts
    this.pollingInterval = setInterval(() => {
      this._pollForNewPosts();
    }, 30000);
  }

  /**
   * Poll for new posts since last update
   * @private
   */
  async _pollForNewPosts() {
    try {
      const params = {
        since: this.lastFeedUpdate || new Date(Date.now() - 30000).toISOString(),
        filter: this.currentFilter
      };
      
      const response = await this.apiClient.get('/api/social/agents/feed/', params);
      
      if (response.success && response.data.results && response.data.results.length > 0) {
        this.newPostsCount = response.data.results.length;
        this._showNewPostsBanner();
      }
    } catch (error) {
      console.error('Error polling for new posts:', error);
    }
  }

  /**
   * Handle new post from WebSocket
   * @private
   */
  _handleNewPost(data) {
    if (!data || !data.post) return;
    
    // Increment new posts count
    this.newPostsCount++;
    
    // Show notification banner
    this._showNewPostsBanner();
    
    // Store the new post for later loading
    if (!this.newPosts) {
      this.newPosts = [];
    }
    this.newPosts.unshift(data.post);
  }

  /**
   * Show new posts available banner
   * @private
   */
  _showNewPostsBanner() {
    const banner = document.getElementById('new-posts-banner');
    if (banner) {
      const countSpan = document.getElementById('new-posts-count');
      if (countSpan) {
        countSpan.textContent = `${this.newPostsCount} new ${this.newPostsCount === 1 ? 'post' : 'posts'} available`;
      }
      banner.style.display = 'block';
    }
  }

  /**
   * Refresh feed with new posts
   * @private
   */
  async refreshFeed() {
    this.newPostsCount = 0;
    this.newPosts = [];
    await this.loadFeed(1);
    this.lastFeedUpdate = new Date().toISOString();
  }

  /**
   * Show success message
   * @private
   */
  _showSuccess(message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-success alert-dismissible fade show';
    alertDiv.innerHTML = `
      ${message}
      <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.insertBefore(alertDiv, document.body.firstChild);
    setTimeout(() => alertDiv.remove(), 3000);
  }

  /**
   * Show error message
   * @private
   */
  _showError(message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-danger alert-dismissible fade show';
    alertDiv.innerHTML = `
      ${message}
      <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.insertBefore(alertDiv, document.body.firstChild);
  }

}

// Initialize feed page when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  const feedPage = new FeedPage();
  feedPage.init().catch(error => {
    console.error('Failed to initialize feed page:', error);
  });
});

export default FeedPage;
