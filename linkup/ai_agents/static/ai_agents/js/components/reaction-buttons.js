/**
 * ReactionButtons Component
 * 
 * Standalone component for displaying and managing reactions on posts/comments.
 * Supports 5 reaction types: like, love, insightful, helpful, celebrate
 * 
 * @class ReactionButtons
 * @example
 * const reactions = new ReactionButtons({
 *   postId: 123,
 *   reactions: {
 *     like: { count: 5, userReacted: true },
 *     love: { count: 2, userReacted: false },
 *     insightful: { count: 1, userReacted: false },
 *     helpful: { count: 3, userReacted: false },
 *     celebrate: { count: 0, userReacted: false }
 *   },
 *   onReactionChange: (reactionType, isActive) => { ... }
 * });
 * 
 * const element = reactions.render();
 * container.appendChild(element);
 */

class ReactionButtons {
  // Reaction types with their Font Awesome icons and colors
  static REACTION_TYPES = {
    like: {
      icon: 'fa-thumbs-up',
      label: 'Like',
      color: '#0d6efd',
      hoverColor: '#0b5ed7'
    },
    love: {
      icon: 'fa-heart',
      label: 'Love',
      color: '#dc3545',
      hoverColor: '#bb2d3b'
    },
    insightful: {
      icon: 'fa-lightbulb',
      label: 'Insightful',
      color: '#ffc107',
      hoverColor: '#e0a800'
    },
    helpful: {
      icon: 'fa-hand-thumbs-up',
      label: 'Helpful',
      color: '#198754',
      hoverColor: '#157347'
    },
    celebrate: {
      icon: 'fa-face-grin-stars',
      label: 'Celebrate',
      color: '#fd7e14',
      hoverColor: '#e86c00'
    }
  };

  /**
   * Create a new ReactionButtons component
   * @param {Object} options - Configuration options
   * @param {number} options.postId - ID of the post/comment
   * @param {Object} options.reactions - Reaction data { reactionType: { count, userReacted } }
   * @param {Function} options.onReactionChange - Callback when reaction changes
   * @param {boolean} options.compact - Compact mode (smaller buttons)
   */
  constructor(options = {}) {
    this.postId = options.postId;
    this.reactions = options.reactions || this._initializeReactions();
    this.onReactionChange = options.onReactionChange || (() => {});
    this.compact = options.compact || false;
    this.loading = false;
    this.element = null;
    this.buttons = {};
  }

  /**
   * Initialize empty reactions object
   * @private
   */
  _initializeReactions() {
    const reactions = {};
    Object.keys(ReactionButtons.REACTION_TYPES).forEach(type => {
      reactions[type] = { count: 0, userReacted: false };
    });
    return reactions;
  }

  /**
   * Render the reaction buttons component
   * @returns {HTMLElement} The rendered component
   */
  render() {
    this.element = document.createElement('div');
    this.element.className = `reaction-buttons ${this.compact ? 'compact' : ''}`;
    this.element.setAttribute('data-post-id', this.postId);

    // Create button container
    const buttonContainer = document.createElement('div');
    buttonContainer.className = 'reaction-button-container';

    // Create a button for each reaction type
    Object.entries(ReactionButtons.REACTION_TYPES).forEach(([type, config]) => {
      const button = this._createReactionButton(type, config);
      buttonContainer.appendChild(button);
      this.buttons[type] = button;
    });

    this.element.appendChild(buttonContainer);
    this._attachEventListeners();
    return this.element;
  }

  /**
   * Create individual reaction button
   * @private
   */
  _createReactionButton(type, config) {
    const button = document.createElement('button');
    button.className = `reaction-btn ${type}-btn`;
    button.setAttribute('data-reaction', type);
    button.setAttribute('title', config.label);
    button.setAttribute('aria-label', `${config.label} reaction`);

    const reactionData = this.reactions[type] || { count: 0, userReacted: false };

    // Button content
    button.innerHTML = `
      <span class="reaction-icon">
        <i class="fas ${config.icon}"></i>
      </span>
      <span class="reaction-count">${reactionData.count}</span>
    `;

    // Add active state if user has reacted
    if (reactionData.userReacted) {
      button.classList.add('active');
      button.setAttribute('aria-pressed', 'true');
    } else {
      button.setAttribute('aria-pressed', 'false');
    }

    return button;
  }

  /**
   * Attach event listeners to buttons
   * @private
   */
  _attachEventListeners() {
    Object.keys(this.buttons).forEach(type => {
      const button = this.buttons[type];
      button.addEventListener('click', (e) => this.handleReactionClick(e, type));
      button.addEventListener('mouseenter', () => this._showReactionTooltip(button, type));
      button.addEventListener('mouseleave', () => this._hideReactionTooltip(button));
    });
  }

  /**
   * Handle reaction button click
   * @param {Event} event - Click event
   * @param {string} reactionType - Type of reaction
   */
  async handleReactionClick(event, reactionType) {
    event.preventDefault();
    event.stopPropagation();

    if (this.loading) return;

    const button = this.buttons[reactionType];
    const isCurrentlyActive = button.classList.contains('active');

    // Optimistic UI update
    this.loading = true;
    this._toggleReactionUI(button, reactionType, !isCurrentlyActive);

    try {
      // Call the reaction change callback
      await this.onReactionChange(reactionType, !isCurrentlyActive);
    } catch (error) {
      // Revert optimistic update on error
      this._toggleReactionUI(button, reactionType, isCurrentlyActive);
      console.error(`Error updating reaction: ${error.message}`);
    } finally {
      this.loading = false;
    }
  }

  /**
   * Toggle reaction UI state
   * @private
   */
  _toggleReactionUI(button, reactionType, isActive) {
    const reactionData = this.reactions[reactionType];

    if (isActive) {
      button.classList.add('active');
      button.setAttribute('aria-pressed', 'true');
      reactionData.count++;
      reactionData.userReacted = true;
    } else {
      button.classList.remove('active');
      button.setAttribute('aria-pressed', 'false');
      reactionData.count = Math.max(0, reactionData.count - 1);
      reactionData.userReacted = false;
    }

    this._updateCountDisplay(button, reactionData.count);
  }

  /**
   * Update the count display on a button
   * @private
   */
  _updateCountDisplay(button, count) {
    const countSpan = button.querySelector('.reaction-count');
    if (countSpan) {
      countSpan.textContent = count;
    }
  }

  /**
   * Show tooltip on hover
   * @private
   */
  _showReactionTooltip(button, reactionType) {
    const config = ReactionButtons.REACTION_TYPES[reactionType];
    const tooltip = document.createElement('div');
    tooltip.className = 'reaction-tooltip';
    tooltip.textContent = config.label;
    tooltip.style.position = 'absolute';
    tooltip.style.bottom = '100%';
    tooltip.style.left = '50%';
    tooltip.style.transform = 'translateX(-50%)';
    tooltip.style.marginBottom = '8px';
    tooltip.style.padding = '4px 8px';
    tooltip.style.backgroundColor = '#333';
    tooltip.style.color = '#fff';
    tooltip.style.borderRadius = '4px';
    tooltip.style.fontSize = '12px';
    tooltip.style.whiteSpace = 'nowrap';
    tooltip.style.zIndex = '1000';
    tooltip.style.pointerEvents = 'none';

    button.style.position = 'relative';
    button.appendChild(tooltip);
    button._tooltip = tooltip;
  }

  /**
   * Hide tooltip
   * @private
   */
  _hideReactionTooltip(button) {
    if (button._tooltip) {
      button._tooltip.remove();
      button._tooltip = null;
    }
  }

  /**
   * Update reaction counts from server data
   * @param {Object} newReactions - Updated reaction data
   */
  updateCounts(newReactions) {
    Object.entries(newReactions).forEach(([type, data]) => {
      if (this.buttons[type]) {
        this.reactions[type] = data;
        const button = this.buttons[type];

        // Update count display
        this._updateCountDisplay(button, data.count);

        // Update active state
        if (data.userReacted) {
          button.classList.add('active');
          button.setAttribute('aria-pressed', 'true');
        } else {
          button.classList.remove('active');
          button.setAttribute('aria-pressed', 'false');
        }
      }
    });
  }

  /**
   * Highlight user's reaction
   * @param {string} reactionType - Type of reaction to highlight
   */
  highlightUserReaction(reactionType) {
    Object.keys(this.buttons).forEach(type => {
      const button = this.buttons[type];
      if (type === reactionType) {
        button.classList.add('active');
        button.setAttribute('aria-pressed', 'true');
        this.reactions[type].userReacted = true;
      } else {
        button.classList.remove('active');
        button.setAttribute('aria-pressed', 'false');
        this.reactions[type].userReacted = false;
      }
    });
  }

  /**
   * Get current reaction state
   * @returns {Object} Current reactions object
   */
  getReactions() {
    return { ...this.reactions };
  }

  /**
   * Get user's current reaction (if any)
   * @returns {string|null} Reaction type or null
   */
  getUserReaction() {
    for (const [type, data] of Object.entries(this.reactions)) {
      if (data.userReacted) {
        return type;
      }
    }
    return null;
  }

  /**
   * Destroy the component
   */
  destroy() {
    if (this.element) {
      this.element.remove();
      this.element = null;
      this.buttons = {};
    }
  }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ReactionButtons;
}
