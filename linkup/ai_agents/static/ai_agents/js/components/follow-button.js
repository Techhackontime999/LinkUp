/**
 * FollowButton Component
 * 
 * Standalone button component for following/unfollowing agents.
 * Manages three states: following, not-following, and loading.
 * Includes optimistic UI updates and visual feedback.
 * 
 * @class FollowButton
 * @example
 * const followBtn = new FollowButton({
 *   agentId: 123,
 *   isFollowing: false,
 *   onFollowChange: (isFollowing) => { ... }
 * });
 * 
 * const element = followBtn.render();
 * container.appendChild(element);
 */

class FollowButton {
  /**
   * Create a new FollowButton component
   * @param {Object} options - Configuration options
   * @param {number} options.agentId - ID of the agent to follow
   * @param {boolean} options.isFollowing - Initial following state
   * @param {Function} options.onFollowChange - Callback when follow state changes
   * @param {string} options.size - Button size (sm, md, lg) - default: md
   * @param {boolean} options.compact - Compact mode (icon only)
   */
  constructor(options = {}) {
    this.agentId = options.agentId;
    this.isFollowing = options.isFollowing || false;
    this.onFollowChange = options.onFollowChange || (() => {});
    this.size = options.size || 'md';
    this.compact = options.compact || false;
    this.loading = false;
    this.element = null;
  }

  /**
   * Render the follow button
   * @returns {HTMLElement} The rendered button
   */
  render() {
    this.element = document.createElement('button');
    this.element.type = 'button';
    this.element.className = this._getButtonClass();
    this.element.setAttribute('data-agent-id', this.agentId);
    this.element.setAttribute('aria-label', this._getAriaLabel());

    this._updateButtonContent();
    this.element.addEventListener('click', (e) => this.handleClick(e));

    return this.element;
  }

  /**
   * Get button CSS classes
   * @private
   */
  _getButtonClass() {
    const classes = ['follow-button', `follow-button-${this.size}`];

    if (this.isFollowing) {
      classes.push('following');
    } else {
      classes.push('not-following');
    }

    if (this.compact) {
      classes.push('compact');
    }

    if (this.loading) {
      classes.push('loading');
    }

    return classes.join(' ');
  }

  /**
   * Get aria-label based on state
   * @private
   */
  _getAriaLabel() {
    if (this.loading) {
      return 'Updating follow status';
    }
    return this.isFollowing ? 'Unfollow agent' : 'Follow agent';
  }

  /**
   * Update button content based on state
   * @private
   */
  _updateButtonContent() {
    if (!this.element) return;

    if (this.loading) {
      this.element.innerHTML = this.compact
        ? '<i class="fas fa-spinner fa-spin"></i>'
        : '<i class="fas fa-spinner fa-spin"></i> <span>Updating...</span>';
      this.element.disabled = true;
    } else if (this.isFollowing) {
      this.element.innerHTML = this.compact
        ? '<i class="fas fa-check"></i>'
        : '<i class="fas fa-check"></i> <span>Following</span>';
      this.element.disabled = false;
    } else {
      this.element.innerHTML = this.compact
        ? '<i class="fas fa-plus"></i>'
        : '<i class="fas fa-plus"></i> <span>Follow</span>';
      this.element.disabled = false;
    }

    this.element.className = this._getButtonClass();
    this.element.setAttribute('aria-label', this._getAriaLabel());
  }

  /**
   * Handle button click
   * @param {Event} event - Click event
   */
  async handleClick(event) {
    event.preventDefault();
    event.stopPropagation();

    if (this.loading) return;

    const previousState = this.isFollowing;

    // Optimistic UI update
    this.setLoading(true);

    try {
      // Call the follow change callback
      const newState = !this.isFollowing;
      await this.onFollowChange(newState);

      // Update state based on callback result
      this.setFollowing(newState);
    } catch (error) {
      // Revert optimistic update on error
      this.setFollowing(previousState);
      console.error(`Error updating follow status: ${error.message}`);
    } finally {
      this.setLoading(false);
    }
  }

  /**
   * Set following state
   * @param {boolean} isFollowing - New following state
   */
  setFollowing(isFollowing) {
    this.isFollowing = isFollowing;
    this._updateButtonContent();

    // Dispatch custom event for external listeners
    const event = new CustomEvent('followStateChanged', {
      detail: { agentId: this.agentId, isFollowing }
    });
    this.element.dispatchEvent(event);
  }

  /**
   * Set loading state
   * @param {boolean} loading - Loading state
   */
  setLoading(loading) {
    this.loading = loading;
    this._updateButtonContent();
  }

  /**
   * Get current following state
   * @returns {boolean} Current following state
   */
  getFollowing() {
    return this.isFollowing;
  }

  /**
   * Toggle following state
   */
  async toggle() {
    await this.handleClick(new Event('click'));
  }

  /**
   * Destroy the component
   */
  destroy() {
    if (this.element) {
      this.element.remove();
      this.element = null;
    }
  }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = FollowButton;
}
