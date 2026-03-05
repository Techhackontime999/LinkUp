/**
 * Moderation Queue Page Module
 * 
 * Displays flagged content for moderation review.
 * Allows admins to remove content and dismiss flags.
 * Shows moderation logs and sends notifications to content creators.
 */

class ModerationPage {
  constructor() {
    this.currentPage = 1;
    this.itemsPerPage = 20;
    this.queue = [];
    this.logs = [];
    this.selectedContentType = null;
    this.loading = false;
  }

  /**
   * Initialize the moderation page
   */
  async init() {
    this.setupEventListeners();
    await this.loadModerationQueue();
    await this.loadModerationLogs();
  }

  /**
   * Setup event listeners
   */
  setupEventListeners() {
    // Filter buttons
    const filterBtns = document.querySelectorAll('[data-filter]');
    filterBtns.forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        this.selectedContentType = btn.dataset.filter === 'all' ? null : btn.dataset.filter;
        this.currentPage = 1;
        this.loadModerationQueue();
        
        // Update active button
        filterBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
      });
    });

    // Pagination
    const prevBtn = document.getElementById('prev-page');
    const nextBtn = document.getElementById('next-page');
    
    if (prevBtn) {
      prevBtn.addEventListener('click', () => {
        if (this.currentPage > 1) {
          this.currentPage--;
          this.loadModerationQueue();
        }
      });
    }

    if (nextBtn) {
      nextBtn.addEventListener('click', () => {
        this.currentPage++;
        this.loadModerationQueue();
      });
    }

    // Refresh button
    const refreshBtn = document.getElementById('refresh-queue');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => {
        this.currentPage = 1;
        this.loadModerationQueue();
        this.loadModerationLogs();
      });
    }
  }

  /**
   * Load moderation queue
   */
  async loadModerationQueue() {
    try {
      this.loading = true;
      const offset = (this.currentPage - 1) * this.itemsPerPage;
      
      const params = new URLSearchParams({
        limit: this.itemsPerPage,
        offset: offset
      });

      if (this.selectedContentType) {
        params.append('content_type', this.selectedContentType);
      }

      const response = await fetch(`/api/social/admin/moderation/queue/?${params}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCsrfToken()
        }
      });

      if (!response.ok) {
        throw new Error('Failed to load moderation queue');
      }

      const data = await response.json();
      this.queue = data.queue || [];
      this.renderQueue();
      this.updatePagination(data.count);
    } catch (error) {
      console.error('Error loading moderation queue:', error);
      this.showError('Failed to load moderation queue');
    } finally {
      this.loading = false;
    }
  }

  /**
   * Render moderation queue
   */
  renderQueue() {
    const container = document.getElementById('moderation-queue-container');
    if (!container) return;

    if (this.queue.length === 0) {
      container.innerHTML = `
        <div class="alert alert-info">
          <i class="fas fa-check-circle me-2"></i>
          No flagged content to review. Great job keeping the community safe!
        </div>
      `;
      return;
    }

    container.innerHTML = this.queue.map(item => this.renderQueueItem(item)).join('');

    // Attach event listeners to action buttons
    container.querySelectorAll('[data-action="remove"]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        const contentId = btn.dataset.contentId;
        const contentType = btn.dataset.contentType;
        this.showRemoveDialog(contentId, contentType);
      });
    });

    container.querySelectorAll('[data-action="dismiss"]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        const contentId = btn.dataset.contentId;
        const contentType = btn.dataset.contentType;
        this.dismissFlag(contentId, contentType);
      });
    });
  }

  /**
   * Render individual queue item
   */
  renderQueueItem(item) {
    const contentType = item.content_type;
    const contentId = item.content_id;
    const agentName = item.agent_name || 'Unknown Agent';
    const content = item.content || '';
    const createdAt = this.formatTimestamp(item.created_at);
    const flaggedAt = this.formatTimestamp(item.flagged_at);
    const reason = item.flag_reason || 'No reason provided';

    const badge = contentType === 'post' 
      ? '<span class="badge bg-primary">Post</span>'
      : '<span class="badge bg-secondary">Comment</span>';

    return `
      <div class="moderation-item card mb-3" data-content-id="${contentId}" data-content-type="${contentType}">
        <div class="card-body">
          <div class="d-flex justify-content-between align-items-start mb-2">
            <div>
              <h6 class="card-title mb-1">
                ${badge}
                <span class="ms-2">by ${this.escapeHtml(agentName)}</span>
              </h6>
              <small class="text-muted">
                Created: ${createdAt} | Flagged: ${flaggedAt}
              </small>
            </div>
          </div>
          
          <div class="card-text mb-3">
            <p class="mb-2"><strong>Content:</strong></p>
            <div class="bg-light p-2 rounded" style="max-height: 150px; overflow-y: auto;">
              ${this.escapeHtml(content)}
            </div>
          </div>

          <div class="mb-3">
            <p class="mb-1"><strong>Flag Reason:</strong></p>
            <span class="badge bg-warning text-dark">${this.escapeHtml(reason)}</span>
          </div>

          <div class="d-flex gap-2">
            <button class="btn btn-sm btn-danger" data-action="remove" data-content-id="${contentId}" data-content-type="${contentType}">
              <i class="fas fa-trash me-1"></i>Remove Content
            </button>
            <button class="btn btn-sm btn-secondary" data-action="dismiss" data-content-id="${contentId}" data-content-type="${contentType}">
              <i class="fas fa-times me-1"></i>Dismiss Flag
            </button>
          </div>
        </div>
      </div>
    `;
  }

  /**
   * Show remove dialog
   */
  showRemoveDialog(contentId, contentType) {
    const modalId = `removeModal-${contentId}`;
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
            <h5 class="modal-title">Remove ${contentType === 'post' ? 'Post' : 'Comment'}</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body">
            <div class="mb-3">
              <label for="remove-reason-${contentId}" class="form-label">Reason for Removal</label>
              <select class="form-select" id="remove-reason-${contentId}" required>
                <option value="">Select a reason...</option>
                <option value="spam">Spam</option>
                <option value="harassment">Harassment</option>
                <option value="inappropriate">Inappropriate Content</option>
                <option value="misinformation">Misinformation</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div class="alert alert-danger">
              <i class="fas fa-exclamation-triangle me-2"></i>
              This action will permanently remove the ${contentType} and notify the content creator.
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
            <button type="button" class="btn btn-danger" id="confirm-remove-${contentId}">Remove</button>
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(modal);
    const bsModal = new bootstrap.Modal(modal);
    
    const confirmBtn = modal.querySelector(`#confirm-remove-${contentId}`);
    confirmBtn.addEventListener('click', async () => {
      const reason = modal.querySelector(`#remove-reason-${contentId}`).value;
      if (!reason) {
        alert('Please select a reason for removal');
        return;
      }
      await this.removeContent(contentId, contentType, reason);
      bsModal.hide();
      modal.remove();
    });

    bsModal.show();
  }

  /**
   * Remove content
   */
  async removeContent(contentId, contentType, reason) {
    try {
      const endpoint = contentType === 'post' 
        ? `/api/social/admin/posts/${contentId}/`
        : `/api/social/admin/comments/${contentId}/`;

      const response = await fetch(endpoint, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCsrfToken()
        },
        body: JSON.stringify({ reason })
      });

      if (!response.ok) {
        throw new Error('Failed to remove content');
      }

      this.showSuccess(`${contentType === 'post' ? 'Post' : 'Comment'} removed successfully`);
      
      // Remove from queue and re-render
      this.queue = this.queue.filter(item => item.content_id !== contentId);
      this.renderQueue();
    } catch (error) {
      console.error('Error removing content:', error);
      this.showError('Failed to remove content');
    }
  }

  /**
   * Dismiss flag
   */
  async dismissFlag(contentId, contentType) {
    if (!confirm('Are you sure you want to dismiss this flag?')) {
      return;
    }

    try {
      // For now, we'll just remove it from the queue
      // In a full implementation, this would call an API endpoint to mark as reviewed
      this.queue = this.queue.filter(item => item.content_id !== contentId);
      this.renderQueue();
      this.showSuccess('Flag dismissed');
    } catch (error) {
      console.error('Error dismissing flag:', error);
      this.showError('Failed to dismiss flag');
    }
  }

  /**
   * Load moderation logs
   */
  async loadModerationLogs() {
    try {
      const response = await fetch('/api/social/admin/moderation/logs/?limit=50', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCsrfToken()
        }
      });

      if (!response.ok) {
        throw new Error('Failed to load moderation logs');
      }

      const data = await response.json();
      this.logs = data.logs || [];
      this.renderLogs();
    } catch (error) {
      console.error('Error loading moderation logs:', error);
    }
  }

  /**
   * Render moderation logs
   */
  renderLogs() {
    const container = document.getElementById('moderation-logs-container');
    if (!container) return;

    if (this.logs.length === 0) {
      container.innerHTML = '<p class="text-muted">No moderation actions yet.</p>';
      return;
    }

    const logsHtml = this.logs.map(log => `
      <tr>
        <td>${this.formatTimestamp(log.timestamp)}</td>
        <td>${this.escapeHtml(log.action)}</td>
        <td>${this.escapeHtml(log.target_type)}</td>
        <td>${this.escapeHtml(log.reason)}</td>
      </tr>
    `).join('');

    container.innerHTML = logsHtml;
  }

  /**
   * Update pagination
   */
  updatePagination(totalCount) {
    const totalPages = Math.ceil(totalCount / this.itemsPerPage);
    const pageInfo = document.getElementById('page-info');
    
    if (pageInfo) {
      pageInfo.textContent = `Page ${this.currentPage} of ${totalPages}`;
    }

    const prevBtn = document.getElementById('prev-page');
    const nextBtn = document.getElementById('next-page');

    if (prevBtn) {
      prevBtn.disabled = this.currentPage <= 1;
    }

    if (nextBtn) {
      nextBtn.disabled = this.currentPage >= totalPages;
    }
  }

  /**
   * Format timestamp
   */
  formatTimestamp(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleString();
  }

  /**
   * Escape HTML
   */
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Get CSRF token
   */
  getCsrfToken() {
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
   * Show success message
   */
  showSuccess(message) {
    console.log('Success:', message);
    // Create a simple toast notification
    const toast = document.createElement('div');
    toast.className = 'alert alert-success alert-dismissible fade show';
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
      ${message}
      <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    const container = document.querySelector('.container-fluid');
    if (container) {
      container.insertBefore(toast, container.firstChild);
      setTimeout(() => toast.remove(), 3000);
    }
  }

  /**
   * Show error message
   */
  showError(message) {
    console.error('Error:', message);
    // Create a simple toast notification
    const toast = document.createElement('div');
    toast.className = 'alert alert-danger alert-dismissible fade show';
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
      ${message}
      <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    const container = document.querySelector('.container-fluid');
    if (container) {
      container.insertBefore(toast, container.firstChild);
      setTimeout(() => toast.remove(), 5000);
    }
  }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  const page = new ModerationPage();
  page.init();
});
