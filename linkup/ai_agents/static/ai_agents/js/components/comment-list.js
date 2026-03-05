/**
 * CommentList Component
 * 
 * Displays and manages comments with nested reply support (3-level depth limit).
 * Includes comment input, threading, and real-time updates.
 * 
 * @class CommentList
 * @example
 * const comments = new CommentList({
 *   postId: 123,
 *   comments: [...],
 *   onCommentAdd: (content) => { ... },
 *   onReplyAdd: (parentId, content) => { ... }
 * });
 * 
 * const element = comments.render();
 * container.appendChild(element);
 */

class CommentList {
  /**
   * Create a new CommentList component
   * @param {Object} options - Configuration options
   * @param {number} options.postId - ID of the post
   * @param {Array} options.comments - Array of comment objects
   * @param {Function} options.onCommentAdd - Callback when comment is added
   * @param {Function} options.onReplyAdd - Callback when reply is added
   * @param {number} options.maxDepth - Maximum nesting depth (default: 3)
   */
  constructor(options = {}) {
    this.postId = options.postId;
    this.comments = options.comments || [];
    this.onCommentAdd = options.onCommentAdd || (() => {});
    this.onReplyAdd = options.onReplyAdd || (() => {});
    this.maxDepth = options.maxDepth || 3;
    this.element = null;
    this.commentInput = null;
    this.commentList = null;
    this.loading = false;
    this.expandedReplies = new Set();
  }

  /**
   * Render the comment list component
   * @returns {HTMLElement} The rendered component
   */
  render() {
    this.element = document.createElement('div');
    this.element.className = 'comment-list-container';
    this.element.setAttribute('data-post-id', this.postId);

    // Create comment input section
    const inputSection = this._createCommentInput();
    this.element.appendChild(inputSection);

    // Create comments list
    this.commentList = document.createElement('div');
    this.commentList.className = 'comments-list';

    if (this.comments.length === 0) {
      const emptyState = document.createElement('div');
      emptyState.className = 'empty-comments-state';
      emptyState.innerHTML = '<p>No comments yet. Be the first to comment!</p>';
      this.commentList.appendChild(emptyState);
    } else {
      this.comments.forEach(comment => {
        const commentElement = this._createCommentElement(comment, 0);
        this.commentList.appendChild(commentElement);
      });
    }

    this.element.appendChild(this.commentList);
    return this.element;
  }

  /**
   * Create comment input section
   * @private
   */
  _createCommentInput() {
    const section = document.createElement('div');
    section.className = 'comment-input-section';

    const form = document.createElement('form');
    form.className = 'comment-form';

    const inputGroup = document.createElement('div');
    inputGroup.className = 'input-group';

    this.commentInput = document.createElement('textarea');
    this.commentInput.className = 'form-control comment-textarea';
    this.commentInput.placeholder = 'Write a comment...';
    this.commentInput.rows = 2;
    this.commentInput.setAttribute('aria-label', 'Comment input');

    const submitBtn = document.createElement('button');
    submitBtn.type = 'submit';
    submitBtn.className = 'btn btn-primary btn-sm';
    submitBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Comment';
    submitBtn.setAttribute('aria-label', 'Submit comment');

    inputGroup.appendChild(this.commentInput);
    inputGroup.appendChild(submitBtn);

    form.appendChild(inputGroup);
    form.addEventListener('submit', (e) => this._handleCommentSubmit(e));

    section.appendChild(form);
    return section;
  }

  /**
   * Create individual comment element
   * @private
   */
  _createCommentElement(comment, depth = 0) {
    const commentDiv = document.createElement('div');
    commentDiv.className = `comment-item depth-${depth}`;
    commentDiv.setAttribute('data-comment-id', comment.id);
    commentDiv.style.marginLeft = `${depth * 20}px`;

    // Comment header
    const header = document.createElement('div');
    header.className = 'comment-header';

    const avatar = document.createElement('img');
    avatar.className = 'comment-avatar';
    avatar.src = comment.author.avatar || '/static/default-avatar.png';
    avatar.alt = comment.author.name;

    const authorInfo = document.createElement('div');
    authorInfo.className = 'comment-author-info';

    const authorName = document.createElement('strong');
    authorName.className = 'comment-author-name';
    authorName.textContent = comment.author.name;

    const timestamp = document.createElement('span');
    timestamp.className = 'comment-timestamp';
    timestamp.textContent = this._formatTimestamp(comment.created_at);
    timestamp.setAttribute('title', new Date(comment.created_at).toLocaleString());

    authorInfo.appendChild(authorName);
    authorInfo.appendChild(timestamp);

    header.appendChild(avatar);
    header.appendChild(authorInfo);

    // Comment content
    const content = document.createElement('div');
    content.className = 'comment-content';
    content.innerHTML = this._escapeHtml(comment.content);

    // Comment actions
    const actions = document.createElement('div');
    actions.className = 'comment-actions';

    const replyBtn = document.createElement('button');
    replyBtn.className = 'btn-link comment-action-btn';
    replyBtn.innerHTML = '<i class="fas fa-reply"></i> Reply';
    replyBtn.setAttribute('aria-label', 'Reply to comment');
    replyBtn.addEventListener('click', () => this._toggleReplyForm(comment.id, depth));

    actions.appendChild(replyBtn);

    // Add flag button for admins
    if (this._isCurrentUserAdmin()) {
      const flagBtn = document.createElement('button');
      flagBtn.className = 'btn-link comment-action-btn text-danger';
      flagBtn.innerHTML = '<i class="fas fa-flag"></i> Flag';
      flagBtn.setAttribute('aria-label', 'Flag comment for moderation');
      flagBtn.addEventListener('click', () => this._showFlagDialog(comment.id));
      actions.appendChild(flagBtn);
    }

    // Assemble comment
    commentDiv.appendChild(header);
    commentDiv.appendChild(content);
    commentDiv.appendChild(actions);

    // Add replies if they exist and depth allows
    if (comment.replies && comment.replies.length > 0 && depth < this.maxDepth - 1) {
      const repliesContainer = document.createElement('div');
      repliesContainer.className = 'comment-replies';
      repliesContainer.setAttribute('data-parent-id', comment.id);

      comment.replies.forEach(reply => {
        const replyElement = this._createCommentElement(reply, depth + 1);
        repliesContainer.appendChild(replyElement);
      });

      commentDiv.appendChild(repliesContainer);
    } else if (comment.replies && comment.replies.length > 0 && depth >= this.maxDepth - 1) {
      // Show "view more replies" button if max depth reached
      const viewMoreBtn = document.createElement('button');
      viewMoreBtn.className = 'btn-link view-more-replies';
      viewMoreBtn.innerHTML = `<i class="fas fa-ellipsis-h"></i> View ${comment.replies.length} more replies`;
      viewMoreBtn.setAttribute('aria-label', 'View more replies');
      viewMoreBtn.addEventListener('click', () => this._expandReplies(comment.id));
      commentDiv.appendChild(viewMoreBtn);
    }

    return commentDiv;
  }

  /**
   * Toggle reply form visibility
   * @private
   */
  _toggleReplyForm(parentCommentId, depth) {
    const commentDiv = this.element.querySelector(`[data-comment-id="${parentCommentId}"]`);
    if (!commentDiv) return;

    let replyForm = commentDiv.querySelector('.reply-form');

    if (replyForm) {
      replyForm.remove();
    } else {
      replyForm = this._createReplyForm(parentCommentId, depth);
      commentDiv.appendChild(replyForm);
      replyForm.querySelector('textarea').focus();
    }
  }

  /**
   * Create reply form
   * @private
   */
  _createReplyForm(parentCommentId, depth) {
    const form = document.createElement('form');
    form.className = 'reply-form';
    form.style.marginLeft = `${(depth + 1) * 20}px`;

    const inputGroup = document.createElement('div');
    inputGroup.className = 'input-group input-group-sm';

    const textarea = document.createElement('textarea');
    textarea.className = 'form-control reply-textarea';
    textarea.placeholder = 'Write a reply...';
    textarea.rows = 2;
    textarea.setAttribute('aria-label', 'Reply input');

    const submitBtn = document.createElement('button');
    submitBtn.type = 'submit';
    submitBtn.className = 'btn btn-primary btn-sm';
    submitBtn.innerHTML = '<i class="fas fa-paper-plane"></i>';
    submitBtn.setAttribute('aria-label', 'Submit reply');

    const cancelBtn = document.createElement('button');
    cancelBtn.type = 'button';
    cancelBtn.className = 'btn btn-secondary btn-sm';
    cancelBtn.innerHTML = '<i class="fas fa-times"></i>';
    cancelBtn.setAttribute('aria-label', 'Cancel reply');
    cancelBtn.addEventListener('click', () => form.remove());

    inputGroup.appendChild(textarea);
    inputGroup.appendChild(submitBtn);
    inputGroup.appendChild(cancelBtn);

    form.appendChild(inputGroup);
    form.addEventListener('submit', (e) => this._handleReplySubmit(e, parentCommentId));

    return form;
  }

  /**
   * Handle comment submission
   * @private
   */
  async _handleCommentSubmit(event) {
    event.preventDefault();

    const content = this.commentInput.value.trim();
    if (!content) return;

    if (this.loading) return;

    this.loading = true;
    const submitBtn = event.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Posting...';
    submitBtn.disabled = true;

    try {
      await this.onCommentAdd(content);
      this.commentInput.value = '';
      this.commentInput.focus();
    } catch (error) {
      console.error('Error adding comment:', error);
    } finally {
      this.loading = false;
      submitBtn.innerHTML = originalText;
      submitBtn.disabled = false;
    }
  }

  /**
   * Handle reply submission
   * @private
   */
  async _handleReplySubmit(event, parentCommentId) {
    event.preventDefault();

    const textarea = event.target.querySelector('textarea');
    const content = textarea.value.trim();
    if (!content) return;

    if (this.loading) return;

    this.loading = true;
    const submitBtn = event.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    submitBtn.disabled = true;

    try {
      await this.onReplyAdd(parentCommentId, content);
      event.target.remove();
    } catch (error) {
      console.error('Error adding reply:', error);
    } finally {
      this.loading = false;
      submitBtn.innerHTML = originalText;
      submitBtn.disabled = false;
    }
  }

  /**
   * Expand replies for a comment
   * @private
   */
  _expandReplies(commentId) {
    this.expandedReplies.add(commentId);
    // This would typically trigger a re-render or fetch more replies
    console.log(`Expanding replies for comment ${commentId}`);
  }

  /**
   * Add a new comment to the list
   * @param {Object} comment - Comment object to add
   */
  addComment(comment) {
    // Remove empty state if it exists
    const emptyState = this.commentList.querySelector('.empty-comments-state');
    if (emptyState) {
      emptyState.remove();
    }

    // Add new comment at the top
    const commentElement = this._createCommentElement(comment, 0);
    this.commentList.insertBefore(commentElement, this.commentList.firstChild);
  }

  /**
   * Add a reply to a comment
   * @param {number} parentCommentId - ID of parent comment
   * @param {Object} reply - Reply object to add
   */
  addReply(parentCommentId, reply) {
    const parentComment = this.element.querySelector(`[data-comment-id="${parentCommentId}"]`);
    if (!parentComment) return;

    let repliesContainer = parentComment.querySelector('.comment-replies');
    if (!repliesContainer) {
      repliesContainer = document.createElement('div');
      repliesContainer.className = 'comment-replies';
      repliesContainer.setAttribute('data-parent-id', parentCommentId);
      parentComment.appendChild(repliesContainer);
    }

    const replyElement = this._createCommentElement(reply, 1);
    repliesContainer.appendChild(replyElement);
  }

  /**
   * Update a comment
   * @param {number} commentId - ID of comment to update
   * @param {Object} updatedData - Updated comment data
   */
  updateComment(commentId, updatedData) {
    const commentElement = this.element.querySelector(`[data-comment-id="${commentId}"]`);
    if (!commentElement) return;

    const contentDiv = commentElement.querySelector('.comment-content');
    if (contentDiv && updatedData.content) {
      contentDiv.innerHTML = this._escapeHtml(updatedData.content);
    }
  }

  /**
   * Remove a comment
   * @param {number} commentId - ID of comment to remove
   */
  removeComment(commentId) {
    const commentElement = this.element.querySelector(`[data-comment-id="${commentId}"]`);
    if (commentElement) {
      commentElement.remove();
    }

    // Show empty state if no comments left
    if (this.commentList.children.length === 0) {
      const emptyState = document.createElement('div');
      emptyState.className = 'empty-comments-state';
      emptyState.innerHTML = '<p>No comments yet. Be the first to comment!</p>';
      this.commentList.appendChild(emptyState);
    }
  }

  /**
   * Format timestamp to relative time
   * @private
   */
  _formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);

    if (seconds < 60) return 'just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;

    return date.toLocaleDateString();
  }

  /**
   * Escape HTML to prevent XSS
   * @private
   */
  _escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Destroy the component
   */
  destroy() {
    if (this.element) {
      this.element.remove();
      this.element = null;
      this.commentList = null;
      this.commentInput = null;
    }
  }

  /**
   * Check if current user is an administrator
   * @private
   */
  _isCurrentUserAdmin() {
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
  _showFlagDialog(commentId) {
    const modalId = `flagCommentModal-${commentId}`;
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
            <h5 class="modal-title">Flag Comment for Moderation</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body">
            <div class="mb-3">
              <label for="flag-reason-${commentId}" class="form-label">Reason for Flagging</label>
              <select class="form-select" id="flag-reason-${commentId}" required>
                <option value="">Select a reason...</option>
                <option value="spam">Spam</option>
                <option value="harassment">Harassment</option>
                <option value="inappropriate">Inappropriate Content</option>
                <option value="misinformation">Misinformation</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div class="mb-3">
              <label for="flag-details-${commentId}" class="form-label">Additional Details (optional)</label>
              <textarea class="form-control" id="flag-details-${commentId}" 
                        placeholder="Provide any additional context..." rows="3"></textarea>
            </div>
            <div class="alert alert-info">
              <strong>Comment Content:</strong>
              <p class="mb-0 mt-2" id="comment-preview-${commentId}"></p>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
            <button type="button" class="btn btn-danger" id="confirm-flag-${commentId}">Flag Comment</button>
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(modal);
    
    // Get comment content for preview
    const commentElement = this.element.querySelector(`[data-comment-id="${commentId}"]`);
    const commentContent = commentElement?.querySelector('.comment-content')?.textContent || 'Comment content';
    const preview = document.getElementById(`comment-preview-${commentId}`);
    if (preview) {
      preview.textContent = commentContent.substring(0, 150) + (commentContent.length > 150 ? '...' : '');
    }
    
    const bsModal = new bootstrap.Modal(modal);
    
    // Handle flag confirmation
    const confirmBtn = modal.querySelector(`#confirm-flag-${commentId}`);
    confirmBtn.addEventListener('click', async () => {
      const reason = modal.querySelector(`#flag-reason-${commentId}`).value;
      const details = modal.querySelector(`#flag-details-${commentId}`).value;
      
      if (!reason) {
        console.error('Please select a reason for flagging.');
        return;
      }
      
      await this._submitCommentFlag(commentId, reason, details);
      bsModal.hide();
      modal.remove();
    });

    bsModal.show();
  }

  /**
   * Submit comment flag to backend
   * @private
   */
  async _submitCommentFlag(commentId, reason, details = '') {
    try {
      const response = await fetch(`/api/social/admin/comments/${commentId}/flag/`, {
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
        throw new Error(errorData.error || 'Failed to flag comment');
      }

      console.log('Comment flagged successfully');
    } catch (error) {
      console.error('Error flagging comment:', error);
    }
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
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = CommentList;
}
