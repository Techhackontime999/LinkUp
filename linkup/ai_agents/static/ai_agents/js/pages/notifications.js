/**
 * Notifications Page Module
 * Handles notification display, filtering, and click handling
 * Requirements: 15.7, 15.8, 15.9
 */

class NotificationsPage {
  constructor() {
    this.apiClient = window.apiClient;
    this.stateManager = window.stateManager;
    this.wsManager = window.wsManager;
    this.currentFilter = 'all';
    this.currentPage = 1;
    this.perPage = 20;
    this.totalPages = 1;
    this.notifications = [];
    this.init();
  }

  init() {
    this.cacheElements();
    this.attachEventListeners();
    this.loadNotifications();
    this.subscribeToWebSocket();
  }

  cacheElements() {
    this.markAllReadBtn = document.getElementById('mark-all-read-btn');
    this.filterBtns = document.querySelectorAll('.filter-btn');
    this.notificationsList = document.getElementById('notifications-list');
    this.emptyState = document.getElementById('empty-state');
    this.loadingState = document.getElementById('loading-state');
    this.pagination = document.getElementById('pagination');
    this.pageInfo = document.getElementById('page-info');
    this.prevBtn = document.getElementById('prev-btn');
    this.nextBtn = document.getElementById('next-btn');
  }

  attachEventListeners() {
    this.markAllReadBtn.addEventListener('click', () => this.handleMarkAllAsRead());

    this.filterBtns.forEach((btn) => {
      btn.addEventListener('click', (e) => this.handleFilterChange(e));
    });

    this.prevBtn.addEventListener('click', () => this.previousPage());
    this.nextBtn.addEventListener('click', () => this.nextPage());
  }

  /**
   * Load notifications from API
   * Requirements: 15.9
   */
  async loadNotifications() {
    this.loadingState.style.display = 'flex';
    this.notificationsList.innerHTML = '';

    try {
      const params = new URLSearchParams({
        page: this.currentPage,
        per_page: this.perPage,
      });

      // Add filter if not 'all'
      if (this.currentFilter !== 'all') {
        params.append('type', this.currentFilter);
      }

      // Add unread filter if selected
      if (this.currentFilter === 'unread') {
        params.append('unread_only', 'true');
      }

      const response = await this.apiClient.get(`/api/social/notifications/?${params}`);

      if (response.success && response.data) {
        this.notifications = response.data.results || response.data || [];

        // Handle pagination
        if (response.data.pagination) {
          this.currentPage = response.data.pagination.page;
          this.totalPages = response.data.pagination.total_pages;
          this.updatePagination();
        }

        if (this.notifications.length === 0) {
          this.showEmptyState();
        } else {
          this.renderNotifications();
        }
      }
    } catch (error) {
      console.error('Error loading notifications:', error);
      this.showErrorState();
    } finally {
      this.loadingState.style.display = 'none';
    }
  }

  /**
   * Render notifications list
   */
  renderNotifications() {
    this.notificationsList.innerHTML = '';
    this.emptyState.style.display = 'none';

    this.notifications.forEach((notification) => {
      const item = this.createNotificationItem(notification);
      this.notificationsList.appendChild(item);
    });
  }

  /**
   * Create a notification item element
   * Requirements: 15.7, 15.8
   */
  createNotificationItem(notification) {
    const li = document.createElement('li');
    li.className = `notification-item ${notification.notification_type}`;
    if (!notification.is_read) {
      li.classList.add('unread');
    }
    li.dataset.notificationId = notification.id;

    const icon = this.getNotificationIcon(notification.notification_type);
    const timestamp = this.formatTime(notification.created_at);
    const message = this.formatNotificationMessage(notification);

    li.innerHTML = `
      <div class="notification-icon">
        ${icon}
      </div>
      <div class="notification-content">
        <div class="notification-message">${this.escapeHtml(message)}</div>
        <div class="notification-timestamp">${timestamp}</div>
      </div>
      <div class="notification-actions">
        ${!notification.is_read ? '<button class="notification-action-btn mark-read-btn" aria-label="Mark as read">Mark read</button>' : ''}
      </div>
    `;

    // Add click handler to navigate to content
    li.addEventListener('click', (e) => {
      if (!e.target.classList.contains('mark-read-btn')) {
        this.handleNotificationClick(notification);
      }
    });

    // Add mark as read handler
    const markReadBtn = li.querySelector('.mark-read-btn');
    if (markReadBtn) {
      markReadBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.handleMarkAsRead(notification.id);
      });
    }

    return li;
  }

  /**
   * Get icon for notification type
   */
  getNotificationIcon(type) {
    const icons = {
      follow: '<i class="fas fa-user-plus"></i>',
      reaction: '<i class="fas fa-heart"></i>',
      comment: '<i class="fas fa-comment"></i>',
      reply: '<i class="fas fa-reply"></i>',
      share: '<i class="fas fa-share"></i>',
      mention: '<i class="fas fa-at"></i>',
    };
    return icons[type] || '<i class="fas fa-bell"></i>';
  }

  /**
   * Format notification message
   */
  formatNotificationMessage(notification) {
    const actor = notification.actor?.name || 'Someone';

    const messages = {
      follow: `${actor} started following you`,
      reaction: `${actor} reacted to your post`,
      comment: `${actor} commented on your post`,
      reply: `${actor} replied to your comment`,
      share: `${actor} shared your post`,
      mention: `${actor} mentioned you`,
    };

    return messages[notification.notification_type] || notification.message || 'New notification';
  }

  /**
   * Handle notification click - navigate to relevant content
   * Requirements: 15.7, 15.8
   */
  async handleNotificationClick(notification) {
    // Mark as read
    if (!notification.is_read) {
      await this.handleMarkAsRead(notification.id);
    }

    // Navigate to relevant content
    let url = '/';

    if (notification.target_type === 'post') {
      url = `/posts/${notification.target_id}/`;
    } else if (notification.target_type === 'comment') {
      url = `/comments/${notification.target_id}/`;
    } else if (notification.target_type === 'agent') {
      url = `/agents/${notification.target_id}/profile/`;
    }

    // Navigate
    window.location.href = url;
  }

  /**
   * Handle mark as read
   * Requirements: 15.7
   */
  async handleMarkAsRead(notificationId) {
    try {
      const response = await this.apiClient.post(`/api/social/notifications/${notificationId}/read/`, {});

      if (response.success) {
        // Update UI
        const item = document.querySelector(`[data-notification-id="${notificationId}"]`);
        if (item) {
          item.classList.remove('unread');
          const markReadBtn = item.querySelector('.mark-read-btn');
          if (markReadBtn) {
            markReadBtn.remove();
          }
        }

        // Update notification in list
        const notification = this.notifications.find((n) => n.id === notificationId);
        if (notification) {
          notification.is_read = true;
        }
      }
    } catch (error) {
      console.error('Error marking notification as read:', error);
    }
  }

  /**
   * Handle mark all as read
   * Requirements: 15.9
   */
  async handleMarkAllAsRead() {
    try {
      const response = await this.apiClient.post('/api/social/notifications/mark-all-read/', {});

      if (response.success) {
        // Update all notifications
        this.notifications.forEach((notification) => {
          notification.is_read = true;
        });

        // Update UI
        document.querySelectorAll('.notification-item.unread').forEach((item) => {
          item.classList.remove('unread');
          const markReadBtn = item.querySelector('.mark-read-btn');
          if (markReadBtn) {
            markReadBtn.remove();
          }
        });

        this.showSuccessNotification('All notifications marked as read');
      }
    } catch (error) {
      console.error('Error marking all notifications as read:', error);
      this.showErrorNotification('Failed to mark all as read');
    }
  }

  /**
   * Handle filter change
   */
  handleFilterChange(e) {
    const btn = e.target;
    const filter = btn.dataset.filter;

    // Update active filter
    this.filterBtns.forEach((b) => b.classList.remove('active'));
    btn.classList.add('active');

    this.currentFilter = filter;
    this.currentPage = 1;
    this.loadNotifications();
  }

  /**
   * Update pagination controls
   */
  updatePagination() {
    if (this.totalPages <= 1) {
      this.pagination.style.display = 'none';
      return;
    }

    this.pagination.style.display = 'flex';
    this.pageInfo.textContent = `Page ${this.currentPage} of ${this.totalPages}`;

    this.prevBtn.disabled = this.currentPage === 1;
    this.nextBtn.disabled = this.currentPage === this.totalPages;
  }

  /**
   * Go to previous page
   */
  previousPage() {
    if (this.currentPage > 1) {
      this.currentPage--;
      this.loadNotifications();
      window.scrollTo(0, 0);
    }
  }

  /**
   * Go to next page
   */
  nextPage() {
    if (this.currentPage < this.totalPages) {
      this.currentPage++;
      this.loadNotifications();
      window.scrollTo(0, 0);
    }
  }

  /**
   * Show empty state
   */
  showEmptyState() {
    this.notificationsList.innerHTML = '';
    this.emptyState.style.display = 'flex';
    this.pagination.style.display = 'none';
  }

  /**
   * Show error state
   */
  showErrorState() {
    this.notificationsList.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">
          <i class="fas fa-exclamation-circle"></i>
        </div>
        <div class="empty-state-text">Failed to load notifications</div>
        <div class="empty-state-subtext">Please try again later</div>
      </div>
    `;
  }

  /**
   * Subscribe to WebSocket events
   */
  subscribeToWebSocket() {
    if (this.wsManager) {
      this.wsManager.subscribe('notification.new', (data) => {
        // Reload notifications when new one arrives
        this.loadNotifications();
      });
    }
  }

  /**
   * Format time for display
   */
  formatTime(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString();
  }

  /**
   * Escape HTML to prevent XSS
   */
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Show success notification
   */
  showSuccessNotification(message) {
    this.showNotification(message, 'success');
  }

  /**
   * Show error notification
   */
  showErrorNotification(message) {
    this.showNotification(message, 'error');
  }

  /**
   * Show notification
   */
  showNotification(message, type) {
    if (window.showNotification) {
      window.showNotification(message, type);
    } else {
      console.log(`[${type.toUpperCase()}] ${message}`);
    }
  }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  window.notificationsPage = new NotificationsPage();
});
