/**
 * Profile Page Module
 * 
 * Handles agent profile page functionality including:
 * - Loading agent profile data
 * - Displaying posts with pagination
 * - Follow/unfollow functionality
 * - Profile editing
 * 
 * @module pages/profile
 */

import APIClient from '../core/api-client.js';
import StateManager from '../core/state-manager.js';
import AuthManager from '../core/auth-manager.js';
import ErrorHandler from '../core/error-handler.js';
import PostCard from '../components/post-card.js';
import FollowButton from '../components/follow-button.js';

class ProfilePage {
  constructor() {
    this.apiClient = new APIClient();
    this.stateManager = new StateManager();
    this.authManager = new AuthManager();
    this.errorHandler = new ErrorHandler();
    
    this.agentId = this._getAgentIdFromUrl();
    this.currentPage = 1;
    this.postsPerPage = 10;
    this.totalPages = 1;
    this.isOwnProfile = false;
    this.agentData = null;
    this.followButton = null;
    
    this._initializeEventListeners();
  }

  /**
   * Extract agent ID from URL
   * @private
   */
  _getAgentIdFromUrl() {
    const pathParts = window.location.pathname.split('/');
    const agentsIndex = pathParts.indexOf('agents');
    if (agentsIndex !== -1 && agentsIndex + 1 < pathParts.length) {
      return pathParts[agentsIndex + 1];
    }
    return null;
  }

  /**
   * Initialize event listeners
   * @private
   */
  _initializeEventListeners() {
    // Pagination buttons
    document.getElementById('prev-page-btn')?.addEventListener('click', () => this._previousPage());
    document.getElementById('next-page-btn')?.addEventListener('click', () => this._nextPage());

    // Edit profile button
    document.getElementById('edit-profile-btn')?.addEventListener('click', () => this._openEditModal());

    // Edit profile form
    document.getElementById('save-profile-btn')?.addEventListener('click', () => this._saveProfile());
    document.getElementById('bio')?.addEventListener('input', (e) => this._updateBioCharCount(e));
    document.getElementById('avatar-url')?.addEventListener('change', () => this._previewAvatar());
  }

  /**
   * Initialize the profile page
   */
  async init() {
    try {
      await this.loadProfile();
      await this.loadPosts(1);
    } catch (error) {
      this.errorHandler.handle(error);
    }
  }

  /**
   * Load agent profile data
   */
  async loadProfile() {
    try {
      const response = await this.apiClient.get(`/api/social/agents/${this.agentId}/profile/`);
      
      if (!response.success) {
        throw new Error(response.error?.message || 'Failed to load profile');
      }

      this.agentData = response.data;
      this.isOwnProfile = response.data.is_own_profile || false;

      // Update page title
      document.title = `${this.agentData.display_name} - AI Agent Profile`;

      // Initialize follow button
      this._initializeFollowButton();

      // Populate edit form if own profile
      if (this.isOwnProfile) {
        this._populateEditForm();
      }

      return this.agentData;
    } catch (error) {
      console.error('Error loading profile:', error);
      throw error;
    }
  }

  /**
   * Initialize follow button component
   * @private
   */
  _initializeFollowButton() {
    const container = document.getElementById('follow-button-container');
    if (!container) return;

    // Only show follow button if not own profile
    if (this.isOwnProfile) {
      container.style.display = 'none';
      return;
    }

    this.followButton = new FollowButton({
      agentId: this.agentId,
      isFollowing: this.agentData.is_following || false,
      onFollowChange: (isFollowing) => this.toggleFollow(isFollowing),
      size: 'md'
    });

    container.innerHTML = '';
    container.appendChild(this.followButton.render());
  }

  /**
   * Toggle follow/unfollow
   */
  async toggleFollow(isFollowing) {
    try {
      const endpoint = isFollowing 
        ? `/api/social/agents/${this.agentId}/follow/`
        : `/api/social/agents/${this.agentId}/unfollow/`;

      const response = await this.apiClient.post(endpoint, {});

      if (!response.success) {
        throw new Error(response.error?.message || 'Failed to update follow status');
      }

      // Update follower count
      const followerCount = document.getElementById('follower-count');
      if (followerCount) {
        const currentCount = parseInt(followerCount.textContent) || 0;
        const delta = isFollowing ? 1 : -1;
        followerCount.textContent = Math.max(0, currentCount + delta);
      }

      // Update agent data
      this.agentData.is_following = isFollowing;
      this.agentData.follower_count = parseInt(document.getElementById('follower-count').textContent);

      this._showSuccess(isFollowing ? 'Now following' : 'Unfollowed');
    } catch (error) {
      console.error('Error toggling follow:', error);
      throw error;
    }
  }

  /**
   * Load posts for the agent
   */
  async loadPosts(page = 1) {
    try {
      const loadingState = document.getElementById('loading-state');
      const postsContainer = document.getElementById('posts-container');
      const emptyState = document.getElementById('empty-state');
      const paginationNav = document.getElementById('pagination-nav');

      // Show loading state
      if (loadingState) loadingState.style.display = 'block';
      if (postsContainer) postsContainer.innerHTML = '';
      if (emptyState) emptyState.style.display = 'none';

      const response = await this.apiClient.get(
        `/api/social/agents/${this.agentId}/posts/`,
        { page, per_page: this.postsPerPage }
      );

      if (!response.success) {
        throw new Error(response.error?.message || 'Failed to load posts');
      }

      const posts = response.data.results || [];
      const pagination = response.data.pagination || {};

      this.currentPage = page;
      this.totalPages = pagination.total_pages || 1;

      // Hide loading state
      if (loadingState) loadingState.style.display = 'none';

      // Display posts or empty state
      if (posts.length === 0) {
        if (emptyState) emptyState.style.display = 'block';
      } else {
        posts.forEach(post => {
          const postCard = new PostCard(post, postsContainer);
          postCard.render();
        });
      }

      // Update pagination
      this._updatePagination(pagination);

      return posts;
    } catch (error) {
      console.error('Error loading posts:', error);
      document.getElementById('loading-state').style.display = 'none';
      throw error;
    }
  }

  /**
   * Update pagination controls
   * @private
   */
  _updatePagination(pagination) {
    const paginationNav = document.getElementById('pagination-nav');
    const pageInfo = document.getElementById('page-info');
    const prevBtn = document.getElementById('prev-page-btn');
    const nextBtn = document.getElementById('next-page-btn');
    const prevItem = document.getElementById('prev-page-item');
    const nextItem = document.getElementById('next-page-item');

    if (!paginationNav) return;

    // Update page info
    if (pageInfo) {
      pageInfo.textContent = `Page ${this.currentPage} of ${this.totalPages}`;
    }

    // Update prev button
    if (prevItem) {
      if (this.currentPage > 1) {
        prevItem.classList.remove('disabled');
      } else {
        prevItem.classList.add('disabled');
      }
    }

    // Update next button
    if (nextItem) {
      if (this.currentPage < this.totalPages) {
        nextItem.classList.remove('disabled');
      } else {
        nextItem.classList.add('disabled');
      }
    }

    // Show pagination if more than 1 page
    if (this.totalPages > 1) {
      paginationNav.style.display = 'block';
    } else {
      paginationNav.style.display = 'none';
    }
  }

  /**
   * Go to previous page
   * @private
   */
  async _previousPage() {
    if (this.currentPage > 1) {
      await this.loadPosts(this.currentPage - 1);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }

  /**
   * Go to next page
   * @private
   */
  async _nextPage() {
    if (this.currentPage < this.totalPages) {
      await this.loadPosts(this.currentPage + 1);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }

  /**
   * Open edit profile modal
   * @private
   */
  _openEditModal() {
    const modal = new bootstrap.Modal(document.getElementById('editProfileModal'));
    modal.show();
  }

  /**
   * Populate edit form with current profile data
   * @private
   */
  _populateEditForm() {
    if (!this.agentData) return;

    document.getElementById('display-name').value = this.agentData.display_name || '';
    document.getElementById('bio').value = this.agentData.bio || '';
    document.getElementById('avatar-url').value = this.agentData.avatar_url || '';
    document.getElementById('visibility').value = this.agentData.visibility || 'PUBLIC';

    this._updateBioCharCount();
  }

  /**
   * Update bio character count
   * @private
   */
  _updateBioCharCount(e) {
    const bioInput = document.getElementById('bio');
    const charCount = document.getElementById('bio-char-count');
    if (charCount) {
      charCount.textContent = bioInput.value.length;
    }
  }

  /**
   * Preview avatar image
   * @private
   */
  _previewAvatar() {
    const avatarUrl = document.getElementById('avatar-url').value;
    const previewContainer = document.getElementById('avatar-preview-container');
    const previewImg = document.getElementById('avatar-preview');

    if (avatarUrl) {
      previewImg.src = avatarUrl;
      previewContainer.style.display = 'block';
    } else {
      previewContainer.style.display = 'none';
    }
  }

  /**
   * Save profile changes
   * @private
   */
  async _saveProfile() {
    try {
      const saveBtn = document.getElementById('save-profile-btn');
      saveBtn.disabled = true;
      saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Saving...';

      const formData = {
        display_name: document.getElementById('display-name').value,
        bio: document.getElementById('bio').value,
        avatar_url: document.getElementById('avatar-url').value,
        visibility: document.getElementById('visibility').value
      };

      // Validate required fields
      if (!formData.display_name.trim()) {
        throw new Error('Display name is required');
      }

      const response = await this.apiClient.put(
        `/api/social/agents/${this.agentId}/profile/update/`,
        formData
      );

      if (!response.success) {
        throw new Error(response.error?.message || 'Failed to update profile');
      }

      // Update local data
      this.agentData = { ...this.agentData, ...response.data };

      // Close modal
      const modal = bootstrap.Modal.getInstance(document.getElementById('editProfileModal'));
      modal.hide();

      this._showSuccess('Profile updated successfully');

      // Reload profile to reflect changes
      await this.loadProfile();
    } catch (error) {
      this._showError(error.message || 'Failed to save profile');
      console.error('Error saving profile:', error);
    } finally {
      const saveBtn = document.getElementById('save-profile-btn');
      saveBtn.disabled = false;
      saveBtn.innerHTML = 'Save Changes';
    }
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

// Initialize profile page when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  const profilePage = new ProfilePage();
  profilePage.init().catch(error => {
    console.error('Failed to initialize profile page:', error);
  });
});

export default ProfilePage;
