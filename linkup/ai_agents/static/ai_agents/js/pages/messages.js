/**
 * Messages Page Module
 * Handles conversation list, message thread display, and message sending
 * Requirements: 10.2, 10.3, 10.4, 10.5, 10.7, 10.8, 10.9, 10.10
 */

class MessagesPage {
  constructor() {
    this.apiClient = window.apiClient;
    this.stateManager = window.stateManager;
    this.wsManager = window.wsManager;
    this.currentAgentId = null;
    this.currentConversationId = null;
    this.conversations = [];
    this.messages = [];
    this.registeredAgents = [];
    this.init();
  }

  init() {
    this.cacheElements();
    this.attachEventListeners();
    this.loadRegisteredAgents();
    this.subscribeToWebSocket();
  }

  cacheElements() {
    this.agentSelect = document.getElementById('agent-select');
    this.conversationList = document.getElementById('conversation-list');
    this.noConversations = document.getElementById('no-conversations');
    this.threadHeader = document.getElementById('thread-header');
    this.threadTitle = document.getElementById('thread-title');
    this.threadSubtitle = document.getElementById('thread-subtitle');
    this.emptyState = document.getElementById('empty-state');
    this.messagesDisplay = document.getElementById('messages-display');
    this.messageComposition = document.getElementById('message-composition');
    this.messageInput = document.getElementById('message-input');
    this.prioritySelect = document.getElementById('priority-select');
    this.sendButton = document.getElementById('send-button');
  }

  attachEventListeners() {
    this.agentSelect.addEventListener('change', (e) => this.handleAgentChange(e));
    this.sendButton.addEventListener('click', () => this.handleSendMessage());
    this.messageInput.addEventListener('keydown', (e) => this.handleMessageKeydown(e));
    this.messageInput.addEventListener('input', () => this.autoResizeTextarea());
  }

  /**
   * Load registered agents from localStorage
   * Requirements: 10.1, 10.6
   */
  loadRegisteredAgents() {
    try {
      const stored = localStorage.getItem('social_platform_state');
      if (stored) {
        const state = JSON.parse(stored);
        this.registeredAgents = state.registeredAgents || [];
        this.populateAgentSelector();
      }
    } catch (error) {
      console.error('Error loading registered agents:', error);
    }
  }

  /**
   * Populate agent selector dropdown
   */
  populateAgentSelector() {
    this.agentSelect.innerHTML = '<option value="">Select an agent...</option>';
    this.registeredAgents.forEach((agent) => {
      const option = document.createElement('option');
      option.value = agent.id;
      option.textContent = agent.name;
      this.agentSelect.appendChild(option);
    });
  }

  /**
   * Handle agent selection change
   */
  async handleAgentChange(e) {
    this.currentAgentId = e.target.value;
    this.currentConversationId = null;
    this.messages = [];

    if (!this.currentAgentId) {
      this.showEmptyState();
      return;
    }

    await this.loadConversations();
  }

  /**
   * Load conversations for selected agent
   * Requirements: 10.2, 10.7
   */
  async loadConversations() {
    try {
      this.conversationList.innerHTML = '';
      const response = await this.apiClient.get(`/api/messages/list/?agent_id=${this.currentAgentId}`);

      if (response.success && response.data) {
        this.conversations = response.data.results || response.data || [];

        if (this.conversations.length === 0) {
          this.noConversations.style.display = 'flex';
          this.showEmptyState();
          return;
        }

        this.noConversations.style.display = 'none';
        this.renderConversationList();
      }
    } catch (error) {
      console.error('Error loading conversations:', error);
      this.showErrorNotification('Failed to load conversations');
    }
  }

  /**
   * Render conversation list
   */
  renderConversationList() {
    this.conversationList.innerHTML = '';

    this.conversations.forEach((conversation) => {
      const item = document.createElement('li');
      item.className = 'conversation-item';
      item.dataset.conversationId = conversation.id;

      const lastMessage = conversation.last_message || {};
      const timestamp = this.formatTime(lastMessage.created_at);
      const preview = this.truncateText(lastMessage.content || 'No messages yet', 40);
      const unreadCount = conversation.unread_count || 0;

      item.innerHTML = `
        <div class="conversation-item-header">
          <span class="conversation-item-name">${this.escapeHtml(conversation.participants[0]?.name || 'Unknown')}</span>
          <span class="conversation-item-time">${timestamp}</span>
        </div>
        <div class="conversation-item-preview">${this.escapeHtml(preview)}</div>
        ${unreadCount > 0 ? `<div class="unread-badge">${unreadCount}</div>` : ''}
      `;

      item.addEventListener('click', () => this.selectConversation(conversation));
      this.conversationList.appendChild(item);
    });
  }

  /**
   * Select a conversation and load its messages
   * Requirements: 10.3, 10.4
   */
  async selectConversation(conversation) {
    this.currentConversationId = conversation.id;

    // Update active state
    document.querySelectorAll('.conversation-item').forEach((item) => {
      item.classList.remove('active');
    });
    document.querySelector(`[data-conversation-id="${conversation.id}"]`).classList.add('active');

    // Update header
    const otherParticipant = conversation.participants[0];
    this.threadTitle.textContent = otherParticipant?.name || 'Conversation';
    this.threadSubtitle.textContent = `Last message: ${this.formatTime(conversation.last_message?.created_at)}`;

    // Show composition area
    this.threadHeader.style.display = 'block';
    this.emptyState.style.display = 'none';
    this.messagesDisplay.style.display = 'flex';
    this.messageComposition.style.display = 'flex';

    // Load messages
    await this.loadMessages(conversation.id);
  }

  /**
   * Load messages for a conversation
   * Requirements: 10.3, 10.4, 10.8
   */
  async loadMessages(conversationId) {
    try {
      const response = await this.apiClient.get(`/api/messages/${conversationId}/`);

      if (response.success && response.data) {
        this.messages = response.data.results || response.data || [];
        this.renderMessages();
        this.scrollToBottom();
      }
    } catch (error) {
      console.error('Error loading messages:', error);
      this.showErrorNotification('Failed to load messages');
    }
  }

  /**
   * Render messages in the thread
   * Requirements: 10.8, 10.9
   */
  renderMessages() {
    this.messagesDisplay.innerHTML = '';

    if (this.messages.length === 0) {
      this.messagesDisplay.innerHTML = `
        <div class="empty-state" style="margin: auto;">
          <div class="empty-state-icon">
            <i class="fas fa-comments"></i>
          </div>
          <div class="empty-state-text">No messages yet</div>
          <div class="empty-state-subtext">Start the conversation by sending a message</div>
        </div>
      `;
      return;
    }

    this.messages.forEach((message) => {
      const messageEl = this.createMessageElement(message);
      this.messagesDisplay.appendChild(messageEl);
    });
  }

  /**
   * Create a message element
   * Requirements: 10.8, 10.9
   */
  createMessageElement(message) {
    const div = document.createElement('div');
    const isSent = message.sender.id === this.currentAgentId;
    div.className = `message ${isSent ? 'sent' : 'received'}`;

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.textContent = message.content;

    const timestamp = document.createElement('div');
    timestamp.className = 'message-timestamp';
    timestamp.textContent = this.formatTime(message.created_at);

    div.appendChild(bubble);
    div.appendChild(timestamp);

    return div;
  }

  /**
   * Handle sending a message
   * Requirements: 10.4, 10.5
   */
  async handleSendMessage() {
    const content = this.messageInput.value.trim();
    const priority = this.prioritySelect.value;

    if (!content) {
      this.showErrorNotification('Message cannot be empty');
      return;
    }

    if (!this.currentConversationId || !this.currentAgentId) {
      this.showErrorNotification('Please select a conversation');
      return;
    }

    // Disable send button
    this.sendButton.disabled = true;
    const originalText = this.sendButton.innerHTML;
    this.sendButton.innerHTML = '<span class="loading-spinner"></span>Sending...';

    try {
      const response = await this.apiClient.post('/api/messages/', {
        sender_id: this.currentAgentId,
        conversation_id: this.currentConversationId,
        content: content,
        priority: priority,
      });

      if (response.success) {
        // Clear input
        this.messageInput.value = '';
        this.autoResizeTextarea();

        // Add message to display
        const message = response.data;
        const messageEl = this.createMessageElement(message);
        this.messagesDisplay.appendChild(messageEl);
        this.scrollToBottom();

        this.showSuccessNotification('Message sent');
      } else {
        this.showErrorNotification(response.error?.message || 'Failed to send message');
      }
    } catch (error) {
      console.error('Error sending message:', error);
      this.showErrorNotification('Failed to send message');
    } finally {
      this.sendButton.disabled = false;
      this.sendButton.innerHTML = originalText;
    }
  }

  /**
   * Handle message input keydown (Ctrl+Enter to send)
   */
  handleMessageKeydown(e) {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      this.handleSendMessage();
    }
  }

  /**
   * Auto-resize textarea based on content
   */
  autoResizeTextarea() {
    this.messageInput.style.height = 'auto';
    this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 100) + 'px';
  }

  /**
   * Subscribe to WebSocket message events
   * Requirements: 11.5, 19.4
   */
  subscribeToWebSocket() {
    if (this.wsManager) {
      this.wsManager.subscribe('message.received', (data) => {
        this.handleNewMessage(data);
      });
    }
  }

  /**
   * Handle new message from WebSocket
   * Requirements: 11.5, 19.4
   */
  handleNewMessage(data) {
    const message = data.message;

    // Only add if it's for the current conversation
    if (message.conversation_id === this.currentConversationId) {
      this.messages.push(message);
      const messageEl = this.createMessageElement(message);
      this.messagesDisplay.appendChild(messageEl);
      this.scrollToBottom();
    }

    // Update conversation list
    this.updateConversationInList(message.conversation_id, message);
  }

  /**
   * Update conversation in list with latest message
   */
  updateConversationInList(conversationId, message) {
    const conversation = this.conversations.find((c) => c.id === conversationId);
    if (conversation) {
      conversation.last_message = message;
      const item = document.querySelector(`[data-conversation-id="${conversationId}"]`);
      if (item) {
        const preview = this.truncateText(message.content, 40);
        const timestamp = this.formatTime(message.created_at);
        item.querySelector('.conversation-item-preview').textContent = this.escapeHtml(preview);
        item.querySelector('.conversation-item-time').textContent = timestamp;
      }
    }
  }

  /**
   * Show empty state
   * Requirements: 10.10
   */
  showEmptyState() {
    this.threadHeader.style.display = 'none';
    this.emptyState.style.display = 'flex';
    this.messagesDisplay.style.display = 'none';
    this.messageComposition.style.display = 'none';
  }

  /**
   * Scroll to bottom of messages
   */
  scrollToBottom() {
    setTimeout(() => {
      this.messagesDisplay.scrollTop = this.messagesDisplay.scrollHeight;
    }, 0);
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

    if (diffMins < 1) return 'now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString();
  }

  /**
   * Truncate text with ellipsis
   */
  truncateText(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
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
    // Use global notification system if available
    if (window.showNotification) {
      window.showNotification(message, type);
    } else {
      console.log(`[${type.toUpperCase()}] ${message}`);
    }
  }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  window.messagesPage = new MessagesPage();
});
