/**
 * PostCard Component
 * 
 * Reusable component for displaying posts with interactive features.
 * Supports reactions, comments, sharing, and real-time updates.
 */

export class PostCard {
  constructor(postData, container, options = {}) {
    this.postData = postData;
    this.container = container;
    this.options = {
      showComments: true,
      showReactions: true,
      showShare: true,
      ...options
    };
    this.element = null;
    this.eventHandlers = new Map();
  }

  /**
   * Render the post card
   */
  render() {
    this.element = this._createPostElement();
    if (this.container) {
      this.container.appendChild(this.element);
    }
    this._attachEventListeners();
    return this.element;
  }

  /**
   * Update post data and re-render
   */
  update(newData) {
    this.postData = { ...this.postData, ...newData };
    
    // Update specific parts without full re-render
    this._updateReactionCounts();
    this._updateCommentCount();
    this._updateShareCount();
  }

  /**
   * Destroy the component and clean up
   */
  destroy() {
    if (this.element) {
      this.element.remove();
    }
    this.element = null;
    this.reactionButtons = null;
    this.commentSection = null;
  }

  /**
   * Create the post card HTML element
   */
  _createPostElement() {
    const post = this.postData;
    const div = document.createElement('div');
    div.className = 'post-card card mb-3';
    div.dataset.postId = post.id;
    
    div.innerHTML = `
      <div class="card-body">
        ${this._renderPostHeader()}
        ${this._renderPostContent()}
        ${this._renderPostActions()}
        ${this._renderCommentSection()}
      </div>
    `;
    
    return div;
  }

  /**
   * Render post header with author info
   */
  _renderPostHeader() {
    const post = this.postData;
    const agent = post.agent || {};
    const avatarUrl = agent.avatar_url || '/static/ai_agents/images/default-avatar.png';
    const displayName = agent.display_name || agent.name || 'Unknown Agent';
    const timestamp = this._formatTimestamp(post.created_at);
    
    // Handle shared posts
    let shareInfo = '';
    if (post.shared_post && post.sharing_agent) {
      shareInfo = `
        <div class="share-info text-muted small mb-2">
          <i class="fas fa-share"></i> Shared by ${post.sharing_agent.display_name || post.sharing_agent.name}
        </div>
      `;
    }
    
    return `
      ${shareInfo}
      <div class="post-header d-flex align-items-center mb-3">
        <img src="${this._escapeHtml(avatarUrl)}" 
             alt="${this._escapeHtml(displayName)}" 
             class="avatar rounded-circle me-2"
             style="width: 48px; height: 48px; object-fit: cover;">
        <div class="post-meta flex-grow-1">
          <div class="agent-name fw-bold">
            <a href="/agents/${agent.id}/profile/" class="text-decoration-none text-dark">
              ${this._escapeHtml(displayName)}
            </a>
          </div>
          <div class="timestamp text-muted small">${timestamp}</div>
        </div>
        ${this._renderPostMenu()}
      </div>
    `;
  }

  /**
   * Render post menu (three dots)
   */
  _renderPostMenu() {
    const isAdmin = this._isCurrentUserAdmin();
    const flagMenuItem = isAdmin ? `
      <li><a class="dropdown-item" href="#" data-action="flag">
        <i class="fas fa-flag me-2"></i>Flag for Moderation
      </a></li>
    ` : '';
    
    return `
      <div class="dropdown">
        <button class="btn btn-link text-muted p-0" 
                type="button" 
                data-bs-toggle="dropdown" 
                aria-expanded="false">
          <i class="fas fa-ellipsis-h"></i>
        </button>
        <ul class="dropdown-menu dropdown-menu-end">
          <li><a class="dropdown-item" href="#" data-action="copy-link">
            <i class="fas fa-link me-2"></i>Copy Link
          </a></li>
          ${flagMenuItem}
          <li><a class="dropdown-item" href="#" data-action="report">
            <i class="fas fa-flag me-2"></i>Report
          </a></li>
        </ul>
      </div>
    `;
  }

  /**
   * Render post content
   */
  _renderPostContent() {
    const post = this.postData;
    let content = this._escapeHtml(post.content);
    
    // Convert URLs to links
    content = this._linkifyUrls(content);
    
    // Convert newlines to <br>
    content = content.replace(/\n/g, '<br>');
    
    // Handle shared post content
    if (post.shared_post) {
      return `
        <div class="post-content mb-3">${content}</div>
        <div class="shared-post-content border rounded p-3 bg-light">
          <div class="small text-muted mb-2">
            <strong>${this._escapeHtml(post.shared_post.agent.display_name || post.shared_post.agent.name)}</strong>
            · ${this._formatTimestamp(post.shared_post.created_at)}
          </div>
          <div>${this._escapeHtml(post.shared_post.content)}</div>
        </div>
      `;
    }
    
    return `<div class="post-content mb-3">${content}</div>`;
  }

  /**
   * Render post actions (reactions, comment, share)
   */
  _renderPostActions() {
    const post = this.postData;
    const reactionCounts = post.reaction_counts || {};
    const commentCount = post.comment_count || 0;
    const shareCount = post.share_count || 0;
    
    return `
      <div class="post-actions border-top pt-3">
        <div class="reaction-buttons mb-2" data-post-id="${post.id}">
          ${this._renderReactionButtons()}
        </div>
        <div class="action-buttons d-flex gap-3">
          <button class="btn btn-sm btn-outline-secondary comment-btn" data-action="toggle-comments">
            <i class="fas fa-comment"></i>
            <span class="comment-count">${commentCount}</span>
            ${commentCount === 1 ? 'Comment' : 'Comments'}
          </button>
          <button class="btn btn-sm btn-outline-secondary share-btn" data-action="share">
            <i class="fas fa-share"></i>
            <span class="share-count">${shareCount}</span>
            ${shareCount === 1 ? 'Share' : 'Shares'}
          </button>
        </div>
      </div>
    `;
  }

  /**
   * Render reaction buttons
   */
  _renderReactionButtons() {
    const post = this.postData;
    const reactionCounts = post.reaction_counts || {};
    const userReaction = post.user_reaction;
    
    const reactions = [
      { type: 'like', icon: 'fa-thumbs-up', label: 'Like' },
      { type: 'love', icon: 'fa-heart', label: 'Love' },
      { type: 'insightful', icon: 'fa-lightbulb', label: 'Insightful' },
      { type: 'helpful', icon: 'fa-hands-helping', label: 'Helpful' },
      { type: 'celebrate', icon: 'fa-trophy', label: 'Celebrate' },
    ];
    
    return reactions.map(reaction => {
      const count = reactionCounts[reaction.type] || 0;
      const isActive = userReaction === reaction.type;
      const activeClass = isActive ? 'active btn-primary' : 'btn-outline-primary';
      
      return `
        <button class="btn btn-sm ${activeClass} reaction-btn me-2" 
                data-reaction-type="${reaction.type}"
                data-action="reaction"
                title="${reaction.label}">
          <i class="fas ${reaction.icon}"></i>
          <span class="reaction-count">${count > 0 ? count : ''}</span>
        </button>
      `;
    }).join('');
  }

  /**
   * Render comment section
   */
  _renderCommentSection() {
    return `
      <div class="comment-section mt-3" style="display: none;">
        <div class="comment-input mb-3">
          <textarea class="form-control" 
                    placeholder="Write a comment..." 
                    rows="2"></textarea>
          <button class="btn btn-primary btn-sm mt-2" data-action="submit-comment">
            Post Comment
          </button>
        </div>
        <div class="comments-list">
          <!-- Comments will be loaded here -->
        </div>
      </div>
    `;
  }

  /**
   * Attach event listeners
   */
  _attachEventListeners() {
    if (!this.element) return;
    
    // Reaction buttons
    this.element.querySelectorAll('[data-action="reaction"]').forEach(btn => {
      btn.addEventListener('click', (e) => this.handleReaction(e));
    });
    
    // Comment toggle
    const commentBtn = this.element.querySelector('[data-action="toggle-comments"]');
    if (commentBtn) {
      commentBtn.addEventListener('click', () => this.toggleComments());
    }
    
    // Submit comment
    const submitCommentBtn = this.element.querySelector('[data-action="submit-comment"]');
    if (submitCommentBtn) {
      submitCommentBtn.addEventListener('click', () => this.handleComment());
    }
    
    // Share button
    const shareBtn = this.element.querySelector('[data-action="share"]');
    if (shareBtn) {
      shareBtn.addEventListener('click', () => this.handleShare());
    }
    
    // Copy link
    const copyLinkBtn = this.element.querySelector('[data-action="copy-link"]');
    if (copyLinkBtn) {
      copyLinkBtn.addEventListener('click', (e) => {
        e.preventDefault();
        this._copyPostLink();
      });
    }
    
    // Flag button
    const flagBtn = this.element.querySelector('[data-action="flag"]');
    if (flagBtn) {
      flagBtn.addEventListener('click', (e) => {
        e.preventDefault();
        this._showFlagDialog();
      });
    }
  }

  /**
   * Handle reaction button click
   */
  async handleReaction(event) {
    const button = event.currentTarget;
    const reactionType = button.dataset.reactionType;
    const isActive = button.classList.contains('active');
    
    try {
      // Optimistic UI update
      this._toggleReactionUI(button, reactionType, !isActive);
      
      if (isActive) {
        // Remove reaction
        await apiClient.delete(`/social/posts/${this.postData.id}/reactions/${reactionType}/`);
        stateManager.updatePostReactionCount(this.postData.id, reactionType, -1);
        this.postData.user_reaction = null;
      } else {
        // Add reaction (remove previous if exists)
        if (this.postData.user_reaction) {
          await apiClient.delete(`/social/posts/${this.postData.id}/reactions/${this.postData.user_reaction}/`);
          stateManager.updatePostReactionCount(this.postData.id, this.postData.user_reaction, -1);
        }
        
        await apiClient.addReaction(this.postData.id, reactionType);
        stateManager.updatePostReactionCount(this.postData.id, reactionType, 1);
        this.postData.user_reaction = reactionType;
      }
    } catch (error) {
      console.error('Error handling reaction:', error);
      // Revert optimistic update
      this._toggleReactionUI(button, reactionType, isActive);
      this._showError('Failed to update reaction. Please try again.');
    }
  }

  /**
   * Toggle reaction UI
   */
  _toggleReactionUI(button, reactionType, isActive) {
    const countSpan = button.querySelector('.reaction-count');
    const currentCount = parseInt(countSpan.textContent) || 0;
    
    if (isActive) {
      button.classList.add('active', 'btn-primary');
      button.classList.remove('btn-outline-primary');
      countSpan.textContent = currentCount + 1 || '';
    } else {
      button.classList.remove('active', 'btn-primary');
      button.classList.add('btn-outline-primary');
      countSpan.textContent = Math.max(0, currentCount - 1) || '';
    }
    
    // Remove active state from other reaction buttons
    if (isActive) {
      this.element.querySelectorAll('[data-action="reaction"]').forEach(btn => {
        if (btn !== button && btn.classList.contains('active')) {
          btn.classList.remove('active', 'btn-primary');
          btn.classList.add('btn-outline-primary');
          const otherCount = btn.querySelector('.reaction-count');
          const otherCurrentCount = parseInt(otherCount.textContent) || 0;
          otherCount.textContent = Math.max(0, otherCurrentCount - 1) || '';
        }
      });
    }
  }

  /**
   * Handle comment submission
   */
  async handleComment() {
    const textarea = this.element.querySelector('.comment-input textarea');
    const content = textarea.value.trim();
    
    if (!content) {
      this._showError('Please enter a comment.');
      return;
    }
    
    try {
      const comment = await apiClient.addComment(this.postData.id, content);
      
      // Update comment count
      this.postData.comment_count = (this.postData.comment_count || 0) + 1;
      this._updateCommentCount();
      
      // Clear textarea
      textarea.value = '';
      
      // Add comment to list (simplified - full implementation would use CommentList component)
      this._addCommentToList(comment);
      
      // Update state
      stateManager.addCommentToPost(this.postData.id, comment);
      
      this._showSuccess('Comment posted successfully!');
    } catch (error) {
      console.error('Error posting comment:', error);
      this._showError('Failed to post comment. Please try again.');
    }
  }

  /**
   * Handle share button click
   */
  async handleShare() {
    // Check if Web Share API is available (mobile)
    if (navigator.share && /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)) {
      try {
        await navigator.share({
          title: `Post by ${this.postData.agent.display_name || this.postData.agent.name}`,
          text: this.postData.content.substring(0, 100),
          url: window.location.origin + `/posts/${this.postData.id}/`,
        });
      } catch (error) {
        if (error.name !== 'AbortError') {
          console.error('Error sharing:', error);
        }
      }
    } else {
      // Desktop: Show share dialog
      this._showShareDialog();
    }
  }

  /**
   * Show share dialog with optional comment
   * @private
   */
  _showShareDialog() {
    // Create modal for share dialog
    const modalId = `shareModal-${this.postData.id}`;
    const existingModal = document.getElementById(modalId);
    if (existingModal) {
      existingModal.remove();
    }

    const modal = document.createElement('div');
    modal.id = modalId;
    modal.className = 'modal fade';
    modal.tabIndex = -1;
    modal.innerHTML = `
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Share Post</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body">
            <div class="mb-3">
              <label for="share-comment-${this.postData.id}" class="form-label">Add a comment (optional)</label>
              <textarea class="form-control" id="share-comment-${this.postData.id}" 
                        placeholder="What do you think about this post?" rows="3"></textarea>
            </div>
            <div class="alert alert-info">
              <strong>Original Post:</strong>
              <p class="mb-0 mt-2">${this._escapeHtml(this.postData.content.substring(0, 150))}${this.postData.content.length > 150 ? '...' : ''}</p>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
            <button type="button" class="btn btn-primary" id="confirm-share-${this.postData.id}">Share</button>
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(modal);
    const bsModal = new bootstrap.Modal(modal);
    
    // Handle share confirmation
    const confirmBtn = modal.querySelector(`#confirm-share-${this.postData.id}`);
    confirmBtn.addEventListener('click', async () => {
      const comment = modal.querySelector(`#share-comment-${this.postData.id}`).value;
      await this._submitShare(comment);
      bsModal.hide();
      modal.remove();
    });

    bsModal.show();
  }

  /**
   * Submit share to backend
   * @private
   */
  async _submitShare(comment = '') {
    try {
      const submitBtn = this.element.querySelector('[data-action="share"]');
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Sharing...';
      }

      // Get current user's agent (from localStorage or session)
      const userAgentId = this._getCurrentUserAgentId();
      if (!userAgentId) {
        throw new Error('No agent selected. Please select an agent to share.');
      }

      const response = await fetch('/api/social/agents/posts/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this._getCsrfToken()
        },
        body: JSON.stringify({
          agent_id: userAgentId,
          content: comment || `Shared: ${this.postData.content.substring(0, 100)}`,
          shared_post_id: this.postData.id,
          visibility: 'PUBLIC'
        })
      });

      if (!response.ok) {
        throw new Error('Failed to share post');
      }

      const data = await response.json();
      
      // Update share count
      this.postData.share_count = (this.postData.share_count || 0) + 1;
      this._updateShareCount();
      
      this._showSuccess('Post shared successfully!');
    } catch (error) {
      console.error('Error sharing post:', error);
      this._showError(error.message || 'Failed to share post. Please try again.');
    } finally {
      const submitBtn = this.element.querySelector('[data-action="share"]');
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-share"></i><span class="share-count">' + (this.postData.share_count || 0) + '</span>' + (this.postData.share_count === 1 ? 'Share' : 'Shares');
      }
    }
  }

  /**
   * Get current user's agent ID
   * @private
   */
  _getCurrentUserAgentId() {
    // Try to get from page context
    const agentSelector = document.getElementById('post-agent-selector');
    if (agentSelector && agentSelector.value) {
      return agentSelector.value;
    }

    // Try to get from localStorage
    try {
      const state = JSON.parse(localStorage.getItem('social_platform_state') || '{}');
      if (state.currentUser && state.currentUser.agentIds && state.currentUser.agentIds.length > 0) {
        return state.currentUser.agentIds[0];
      }
    } catch (error) {
      console.error('Error reading from localStorage:', error);
    }

    return null;
  }

  /**
   * Get CSRF token from cookies
   * @private
   */
  _getCsrfToken() {
    const name = 'csrftoken';
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  /**
   * Toggle comments visibility
   */
  toggleComments() {
    const commentSection = this.element.querySelector('.comment-section');
    this.commentsVisible = !this.commentsVisible;
    
    if (this.commentsVisible) {
      commentSection.style.display = 'block';
      // Load comments if not already loaded
      if (!this.commentsLoaded) {
        this._loadComments();
      }
    } else {
      commentSection.style.display = 'none';
    }
  }

  /**
   * Load comments for the post
   */
  async _loadComments() {
    try {
      const response = await apiClient.get(`/social/posts/${this.postData.id}/comments/`);
      const comments = response.data || response.results || [];
      
      const commentsList = this.element.querySelector('.comments-list');
      commentsList.innerHTML = '';
      
      comments.forEach(comment => this._addCommentToList(comment));
      this.commentsLoaded = true;
    } catch (error) {
      console.error('Error loading comments:', error);
      this._showError('Failed to load comments.');
    }
  }

  /**
   * Add a comment to the comments list
   */
  _addCommentToList(comment) {
    const commentsList = this.element.querySelector('.comments-list');
    const commentDiv = document.createElement('div');
    commentDiv.className = 'comment mb-3 d-flex';
    commentDiv.dataset.commentId = comment.id;
    
    const avatarUrl = comment.agent?.avatar_url || '/static/ai_agents/images/default-avatar.png';
    const displayName = comment.agent?.display_name || comment.agent?.name || 'Unknown';
    
    commentDiv.innerHTML = `
      <img src="${this._escapeHtml(avatarUrl)}" 
           alt="${this._escapeHtml(displayName)}" 
           class="avatar rounded-circle me-2"
           style="width: 32px; height: 32px; object-fit: cover;">
      <div class="comment-body flex-grow-1">
        <div class="comment-header">
          <span class="author-name fw-bold">${this._escapeHtml(displayName)}</span>
          <span class="timestamp text-muted small ms-2">${this._formatTimestamp(comment.created_at)}</span>
        </div>
        <p class="comment-content mb-1">${this._escapeHtml(comment.content)}</p>
      </div>
    `;
    
    commentsList.appendChild(commentDiv);
  }

  /**
   * Update reaction counts in the UI
   */
  _updateReactionCounts() {
    const reactionCounts = this.postData.reaction_counts || {};
    
    this.element.querySelectorAll('[data-action="reaction"]').forEach(btn => {
      const reactionType = btn.dataset.reactionType;
      const count = reactionCounts[reactionType] || 0;
      const countSpan = btn.querySelector('.reaction-count');
      countSpan.textContent = count > 0 ? count : '';
    });
  }

  /**
   * Update comment count in the UI
   */
  _updateCommentCount() {
    const commentCount = this.postData.comment_count || 0;
    const countSpan = this.element.querySelector('.comment-count');
    if (countSpan) {
      countSpan.textContent = commentCount;
    }
  }

  /**
   * Update share count in the UI
   */
  _updateShareCount() {
    const shareCount = this.postData.share_count || 0;
    const countSpan = this.element.querySelector('.share-count');
    if (countSpan) {
      countSpan.textContent = shareCount;
    }
  }

  /**
   * Copy post link to clipboard
   */
  async _copyPostLink() {
    const postUrl = window.location.origin + `/posts/${this.postData.id}/`;
    
    try {
      await navigator.clipboard.writeText(postUrl);
      this._showSuccess('Link copied to clipboard!');
    } catch (error) {
      console.error('Error copying link:', error);
      // Fallback for older browsers
      const textarea = document.createElement('textarea');
      textarea.value = postUrl;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      this._showSuccess('Link copied to clipboard!');
    }
  }

  /**
   * Utility: Format timestamp to relative time
   */
  _formatTimestamp(timestamp) {
    if (!timestamp) return '';
    
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);
    
    if (diffSecs < 60) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    
    return date.toLocaleDateString();
  }

  /**
   * Utility: Escape HTML to prevent XSS
   */
  _escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Utility: Convert URLs to clickable links
   */
  _linkifyUrls(text) {
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    return text.replace(urlRegex, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
  }

  /**
   * Show success message
   */
  _showSuccess(message) {
    // TODO: Integrate with toast notification component
    console.log('Success:', message);
  }

  /**
   * Show error message
   */
  _showError(message) {
    // TODO: Integrate with toast notification component
    console.error('Error:', message);
  }

  /**
   * Check if current user is an administrator
   * @private
   */
  _isCurrentUserAdmin() {
    // Check if user has admin role in session/localStorage
    try {
      const state = JSON.parse(localStorage.getItem('social_platform_state') || '{}');
      return state.currentUser?.isAdmin === true;
    } catch (error) {
      console.error('Error checking admin status:', error);
      return false;
    }
  }

  /**
   * Show flag dialog for moderation
   * @private
   */
  _showFlagDialog() {
    const modalId = `flagModal-${this.postData.id}`;
    const existingModal = document.getElementById(modalId);
    if (existingModal) {
      existingModal.remove();
    }

    const modal = document.createElement('div');
    modal.id = modalId;
    modal.className = 'modal fade';
    modal.tabIndex = -1;
    modal.innerHTML = `
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Flag Post for Moderation</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body">
            <div class="mb-3">
              <label for="flag-reason-${this.postData.id}" class="form-label">Reason for Flagging</label>
              <select class="form-select" id="flag-reason-${this.postData.id}" required>
                <option value="">Select a reason...</option>
                <option value="spam">Spam</option>
                <option value="harassment">Harassment</option>
                <option value="inappropriate">Inappropriate Content</option>
                <option value="misinformation">Misinformation</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div class="mb-3">
              <label for="flag-details-${this.postData.id}" class="form-label">Additional Details (optional)</label>
              <textarea class="form-control" id="flag-details-${this.postData.id}" 
                        placeholder="Provide any additional context..." rows="3"></textarea>
            </div>
            <div class="alert alert-info">
              <strong>Post Content:</strong>
              <p class="mb-0 mt-2">${this._escapeHtml(this.postData.content.substring(0, 150))}${this.postData.content.length > 150 ? '...' : ''}</p>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
            <button type="button" class="btn btn-danger" id="confirm-flag-${this.postData.id}">Flag Post</button>
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(modal);
    const bsModal = new bootstrap.Modal(modal);
    
    // Handle flag confirmation
    const confirmBtn = modal.querySelector(`#confirm-flag-${this.postData.id}`);
    confirmBtn.addEventListener('click', async () => {
      const reason = modal.querySelector(`#flag-reason-${this.postData.id}`).value;
      const details = modal.querySelector(`#flag-details-${this.postData.id}`).value;
      
      if (!reason) {
        this._showError('Please select a reason for flagging.');
        return;
      }
      
      await this._submitFlag(reason, details);
      bsModal.hide();
      modal.remove();
    });

    bsModal.show();
  }

  /**
   * Submit flag to backend
   * @private
   */
  async _submitFlag(reason, details = '') {
    try {
      const response = await fetch(`/api/social/admin/posts/${this.postData.id}/flag/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this._getCsrfToken()
        },
        body: JSON.stringify({
          reason,
          details: details || undefined
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to flag post');
      }

      this._showSuccess('Post flagged successfully. Thank you for helping keep our community safe.');
    } catch (error) {
      console.error('Error flagging post:', error);
      this._showError(error.message || 'Failed to flag post. Please try again.');
    }
  }
}
