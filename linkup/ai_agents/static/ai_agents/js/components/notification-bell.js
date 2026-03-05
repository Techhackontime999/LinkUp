/**
 * NotificationBell Component
 * 
 * Dropdown notification bell with badge count, notification list,
 * and real-time update support via WebSocket or polling.
 * 
 * @class NotificationBell
 * @example
 * const bell = new NotificationBell({
 *   notifications: [...],
 *   onNotificationClick: (notification) => { ... },
 *   onMarkAsRead: (notificationId) => { ... }
 * });
 * 
 * const element = bell.render();
 * container.appendChild(element);
 */

class NotificationBell {
  /**
   * Create a new NotificationBell component
   * @param {Object} options - Configuration options
   * @param {Array} options.notifications - Array of notification objects
   * @param {Function} options.onNotificationClick - Callback when notification is clicked
   * @param {Function} options.onMarkAsRead - Callback to mark notification as read
   * @param {Function} options.onMarkAllAsRead - Callback to mark all as read
   * @param {number} options.maxNotifications - Max notifications to display (default: 10)
   */
  constructor(options = {}) {
    this.notifications = options.notifications || [];
    this.onNotificationClick = options.onNotificationClick || (() => {});
    this.onMarkAsRead = options.onMarkAsRead || (() => {});
    this.onMarkAllAsRead = options.onMarkAllAsRead || (() => {});
    this.maxNotifications = options.maxNotifications || 10;
    this.element = null;
    this.bellButton = null;
    this.dropdown = null;
    this.badge = null;
    this.notificationList = null;
    this.isOpen = false;
  }

  /**
   * Render the notification bell component
   * @returns {HTMLElement} The rendered component
   */
  render() {
    this.element = document.createElement('div');
    this.element.className = 'notification-bell-container';

    // Create bell button
    this.bellButton = document.createElement('button');
    this.bellButton.className = 'notification-bell-btn';
    this.bellButton.setAttribute('aria-label', 'Notifications');
    this.bellButton.setAttribute('aria-haspopup', 'true');
    this.bellButton.setAttribute('aria-expanded', 'false');

    const bellIcon = document.createElement('i');
    bellIcon.className = 'fas fa-bell';

    this.badge = document.createElement('span');
    this.badge.className = 'notification-badge';
    this.badge.textContent = this._getUnreadCount();
    if (this._getUnreadCount() === 0) {
      this.badge.style.display = 'none';
    }

    this.bellButton.appendChild(bellIcon);
    this.bellButton.appendChild(this.badge);
    this.bellButton.addEventListener('click', () => this.toggle());

    // Create dropdown
    this.dropdown = document.createElement('div');
    this.dropdown.className = 'notification-dropdown';
    this.dropdown.setAttribute('role', 'menu');

    // Create dropdown header
    const header = this._createDropdownHeader();
    this.dropdown.appendChild(header);

    // Create notification list
    this.notificationList = document.createElement('div');
    this.notificationList.className = 'notification-list';
    this.notificationList.setAttribute('role', 'region');
    this.notificationList.setAttribute('aria-label', 'Notifications');

    if (this.notifications.length === 0) {
      const emptyState = document.createElement('div');
      emptyState.className = 'empty-notifications';
      emptyState.innerHTML = '<p>No notifications yet</p>';
      this.notificationList.appendChild(emptyState);
    } else {
      this.notifications.slice(0, this.maxNotifications).forEach(notification => {
        const notifElement = this._createNotificationItem(notification);
        this.notificationList.appendChild(notifElement);
      });
    }

    this.dropdown.appendChild(this.notificationList);

    // Create dropdown footer
    const footer = this._createDropdownFooter();
    this.dropdown.appendChild(footer);

    this.element.appendChild(this.bellButton);
    this.element.appendChild(this.dropdown);

    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => this._handleOutsideClick(e));

    return this.element;
  }

  /**
   * Create dropdown header with title and mark all as read button
   * @private
   */
  _createDropdownHeader() {
    const header = document.createElement('div');
    header.className = 'notification-dropdown-header';

    const title = document.createElement('h6');
    title.className = 'notification-title';
    title.textContent = 'Notifications';

    const markAllBtn = document.createElement('button');
    markAllBtn.className = 'btn-link mark-all-read-btn';
    markAllBtn.innerHTML = '<i class="fas fa-check-double"></i> Mark all as read';
    markAllBtn.setAttribute('aria-label', 'Mark all notifications as read');
    markAllBtn.addEventListener('click', () => this._handleMarkAllAsRead());

    header.appendChild(title);
    header.appendChild(markAllBtn);

    return header;
  }

  /**
   * Create individual notification item
   * @private
   */
  _createNotificationItem(notification) {
    const item = document.createElement('div');
    item.className = `notification-item ${notification.read ? 'read' : 'unread'}`;
    item.setAttribute('data-notification-id', notification.id);
    item.setAttribute('role', 'menuitem');

    // Notification icon
    const icon = document.createElement('div');
    icon.className = 'notification-icon';
    icon.innerHTML = this._getNotificationIcon(notification.type);

    // Notification content
    const content = document.createElement('div');
    content.className = 'notification-content';

    const title = document.createElement('div');
    title.className = 'notification-item-title';
    title.textContent = notification.title;

    const message = document.createElement('div');
    message.className = 'notification-item-message';
    message.textContent = notification.message;

    const timestamp = document.createElement('div');
    timestamp.className = 'notification-item-timestamp';
    timestamp.textContent = this._formatTimestamp(notification.created_at);
    timestamp.setAttribute('title', new Date(notification.created_at).toLocaleString());

    content.appendChild(title);
    content.appendChild(message);
    content.appendChild(timestamp);

    // Notification actions
    const actions = document.createElement('div');
    actions.className = 'notification-actions';

    if (!notification.read) {
      const markReadBtn = document.createElement('button');
      markReadBtn.className = 'btn-link mark-read-btn';
      markReadBtn.innerHTML = '<i class="fas fa-check"></i>';
      markReadBtn.setAttribute('aria-label', 'Mark as read');
      markReadBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        this._handleMarkAsRead(notification.id);
      });
      actions.appendChild(markReadBtn);
    }

    item.appendChild(icon);
    item.appendChild(content);
    item.appendChild(actions);

    // Click handler
    item.addEventListener('click', () => this._handleNotificationClick(notification));

    return item;
  }

  /**
   * Get icon for notification type
   * @private
   */
  _getNotificationIcon(type) {
    const icons = {
      post: '<i class="fas fa-file-alt"></i>',
      comment: '<i class="fas fa-comment"></i>',
      reaction: '<i class="fas fa-heart"></i>',
      follow: '<i class="fas fa-user-plus"></i>',
      message: '<i class="fas fa-envelope"></i>',
      mention: '<i class="fas fa-at"></i>',
      default: '<i class="fas fa-bell"></i>'
    };
    return icons[type] || icons.default;
  }

  /**
   * Create dropdown footer with view all link
   * @private
   */
  _createDropdownFooter() {
    const footer = document.createElement('div');
    footer.className = 'notification-dropdown-footer';

    const viewAllBtn = document.createElement('a');
    viewAllBtn.href = '#/notifications';
    viewAllBtn.className = 'view-all-notifications-btn';
    viewAllBtn.innerHTML = 'View all notifications <i class="fas fa-arrow-right"></i>';
    viewAllBtn.setAttribute('role', 'menuitem');

    footer.appendChild(viewAllBtn);

    return footer;
  }

  /**
   * Handle notification click
   * @private
   */
  async _handleNotificationClick(notification) {
    // Mark as read if not already
    if (!notification.read) {
      await this._handleMarkAsRead(notification.id);
    }

    // Call the callback
    await this.onNotificationClick(notification);

    // Close dropdown
    this.close();
  }

  /**
   * Handle mark as read
   * @private
   */
  async _handleMarkAsRead(notificationId) {
    try {
      await this.onMarkAsRead(notificationId);

      // Update UI
      const notification = this.notifications.find(n => n.id === notificationId);
      if (notification) {
        notification.read = true;
        const item = this.notificationList.querySelector(`[data-notification-id="${notificationId}"]`);
        if (item) {
          item.classList.remove('unread');
          item.classList.add('read');
          const markReadBtn = item.querySelector('.mark-read-btn');
          if (markReadBtn) {
            markReadBtn.remove();
          }
        }
      }

      this._updateBadge();
    } catch (error) {
      console.error('Error marking notification as read:', error);
    }
  }

  /**
   * Handle mark all as read
   * @private
   */
  async _handleMarkAllAsRead() {
    try {
      await this.onMarkAllAsRead();

      // Update all notifications
      this.notifications.forEach(notification => {
        notification.read = true;
      });

      // Update UI
      this.notificationList.querySelectorAll('.notification-item.unread').forEach(item => {
        item.classList.remove('unread');
        item.classList.add('read');
        const markReadBtn = item.querySelector('.mark-read-btn');
        if (markReadBtn) {
          markReadBtn.remove();
        }
      });

      this._updateBadge();
    } catch (error) {
      console.error('Error marking all notifications as read:', error);
    }
  }

  /**
   * Handle outside click to close dropdown
   * @private
   */
  _handleOutsideClick(event) {
    if (!this.element.contains(event.target) && this.isOpen) {
      this.close();
    }
  }

  /**
   * Toggle dropdown visibility
   */
  toggle() {
    if (this.isOpen) {
      this.close();
    } else {
      this.open();
    }
  }

  /**
   * Open dropdown
   */
  open() {
    this.isOpen = true;
    this.dropdown.classList.add('open');
    this.bellButton.setAttribute('aria-expanded', 'true');
  }

  /**
   * Close dropdown
   */
  close() {
    this.isOpen = false;
    this.dropdown.classList.remove('open');
    this.bellButton.setAttribute('aria-expanded', 'false');
  }

  /**
   * Update badge count
   * @private
   */
  _updateBadge() {
    const unreadCount = this._getUnreadCount();
    if (unreadCount === 0) {
      this.badge.style.display = 'none';
    } else {
      this.badge.style.display = 'inline-block';
      this.badge.textContent = unreadCount > 99 ? '99+' : unreadCount;
    }
  }

  /**
   * Get unread notification count
   * @private
   */
  _getUnreadCount() {
    return this.notifications.filter(n => !n.read).length;
  }

  /**
   * Add a new notification
   * @param {Object} notification - Notification object to add
   */
  addNotification(notification) {
    // Remove empty state if it exists
    const emptyState = this.notificationList.querySelector('.empty-notifications');
    if (emptyState) {
      emptyState.remove();
    }

    // Add notification at the top
    const notifElement = this._createNotificationItem(notification);
    this.notificationList.insertBefore(notifElement, this.notificationList.firstChild);

    // Keep only maxNotifications
    while (this.notificationList.children.length > this.maxNotifications) {
      this.notificationList.lastChild.remove();
    }

    // Add to notifications array
    this.notifications.unshift(notification);
    if (this.notifications.length > this.maxNotifications) {
      this.notifications.pop();
    }

    this._updateBadge();
  }

  /**
   * Update notification count
   * @param {number} count - New unread count
   */
  updateCount(count) {
    if (count === 0) {
      this.badge.style.display = 'none';
    } else {
      this.badge.style.display = 'inline-block';
      this.badge.textContent = count > 99 ? '99+' : count;
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
   * Destroy the component
   */
  destroy() {
    if (this.element) {
      this.element.remove();
      this.element = null;
      this.bellButton = null;
      this.dropdown = null;
      this.badge = null;
      this.notificationList = null;
    }
  }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = NotificationBell;
}
