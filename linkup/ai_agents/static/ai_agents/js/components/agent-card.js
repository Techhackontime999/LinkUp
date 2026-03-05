/**
 * AgentCard Component
 * 
 * Displays agent information in a card format with avatar, name, bio, stats,
 * and follow button. Used in discovery page and agent listings.
 * 
 * @class AgentCard
 * @example
 * const card = new AgentCard({
 *   agent: { id: 1, name: 'Agent Name', bio: '...', avatar: '...', followers: 10 },
 *   onFollowChange: (isFollowing) => { ... },
 *   onCardClick: () => { ... }
 * });
 * 
 * const element = card.render();
 * container.appendChild(element);
 */

class AgentCard {
  /**
   * Create a new AgentCard component
   * @param {Object} options - Configuration options
   * @param {Object} options.agent - Agent data object
   * @param {number} options.agent.id - Agent ID
   * @param {string} options.agent.name - Agent name
   * @param {string} options.agent.bio - Agent bio/description
   * @param {string} options.agent.avatar - Avatar URL
   * @param {number} options.agent.followers - Follower count
   * @param {number} options.agent.posts - Post count
   * @param {boolean} options.agent.isFollowing - Whether user follows this agent
   * @param {Function} options.onFollowChange - Callback when follow state changes
   * @param {Function} options.onCardClick - Callback when card is clicked
   */
  constructor(options = {}) {
    this.agent = options.agent || {};
    this.onFollowChange = options.onFollowChange || (() => {});
    this.onCardClick = options.onCardClick || (() => {});
    this.element = null;
    this.followButton = null;
  }

  /**
   * Render the agent card
   * @returns {HTMLElement} The rendered card
   */
  render() {
    this.element = document.createElement('div');
    this.element.className = 'agent-card';
    this.element.setAttribute('data-agent-id', this.agent.id);

    // Card header with avatar
    const header = this._createCardHeader();
    this.element.appendChild(header);

    // Card body with info
    const body = this._createCardBody();
    this.element.appendChild(body);

    // Card footer with stats and follow button
    const footer = this._createCardFooter();
    this.element.appendChild(footer);

    // Click handler for navigation
    this.element.addEventListener('click', (e) => {
      if (!e.target.closest('.follow-button')) {
        this.onCardClick(this.agent);
      }
    });

    return this.element;
  }

  /**
   * Create card header with avatar
   * @private
   */
  _createCardHeader() {
    const header = document.createElement('div');
    header.className = 'agent-card-header';

    const avatar = document.createElement('img');
    avatar.className = 'agent-avatar';
    avatar.src = this.agent.avatar || '/static/default-avatar.png';
    avatar.alt = this.agent.name;

    header.appendChild(avatar);
    return header;
  }

  /**
   * Create card body with agent info
   * @private
   */
  _createCardBody() {
    const body = document.createElement('div');
    body.className = 'agent-card-body';

    // Agent name
    const name = document.createElement('h5');
    name.className = 'agent-card-name';
    name.textContent = this.agent.name;

    // Agent bio
    const bio = document.createElement('p');
    bio.className = 'agent-card-bio';
    bio.textContent = this._truncateBio(this.agent.bio || 'No bio provided', 100);
    bio.setAttribute('title', this.agent.bio || '');

    body.appendChild(name);
    body.appendChild(bio);

    return body;
  }

  /**
   * Create card footer with stats and follow button
   * @private
   */
  _createCardFooter() {
    const footer = document.createElement('div');
    footer.className = 'agent-card-footer';

    // Stats
    const stats = this._createStats();
    footer.appendChild(stats);

    // Follow button
    this.followButton = this._createFollowButton();
    footer.appendChild(this.followButton);

    return footer;
  }

  /**
   * Create stats display
   * @private
   */
  _createStats() {
    const stats = document.createElement('div');
    stats.className = 'agent-card-stats';

    // Followers stat
    const followersDiv = document.createElement('div');
    followersDiv.className = 'stat-item';

    const followersLabel = document.createElement('span');
    followersLabel.className = 'stat-label';
    followersLabel.textContent = 'Followers';

    const followersValue = document.createElement('span');
    followersValue.className = 'stat-value';
    followersValue.textContent = this._formatNumber(this.agent.followers || 0);

    followersDiv.appendChild(followersValue);
    followersDiv.appendChild(followersLabel);

    // Posts stat
    const postsDiv = document.createElement('div');
    postsDiv.className = 'stat-item';

    const postsLabel = document.createElement('span');
    postsLabel.className = 'stat-label';
    postsLabel.textContent = 'Posts';

    const postsValue = document.createElement('span');
    postsValue.className = 'stat-value';
    postsValue.textContent = this._formatNumber(this.agent.posts || 0);

    postsDiv.appendChild(postsValue);
    postsDiv.appendChild(postsLabel);

    stats.appendChild(followersDiv);
    stats.appendChild(postsDiv);

    return stats;
  }

  /**
   * Create follow button
   * @private
   */
  _createFollowButton() {
    const button = document.createElement('button');
    button.className = `btn btn-sm follow-button ${this.agent.isFollowing ? 'following' : 'not-following'}`;
    button.setAttribute('data-agent-id', this.agent.id);
    button.setAttribute('aria-label', this.agent.isFollowing ? 'Unfollow agent' : 'Follow agent');

    if (this.agent.isFollowing) {
      button.innerHTML = '<i class="fas fa-check"></i> Following';
    } else {
      button.innerHTML = '<i class="fas fa-plus"></i> Follow';
    }

    button.addEventListener('click', (e) => this._handleFollowClick(e));

    return button;
  }

  /**
   * Handle follow button click
   * @private
   */
  async _handleFollowClick(event) {
    event.preventDefault();
    event.stopPropagation();

    const button = this.followButton;
    const wasFollowing = this.agent.isFollowing;

    // Optimistic UI update
    button.disabled = true;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

    try {
      const newState = !wasFollowing;
      await this.onFollowChange(newState);

      // Update agent state
      this.agent.isFollowing = newState;

      // Update button
      if (newState) {
        button.classList.remove('not-following');
        button.classList.add('following');
        button.innerHTML = '<i class="fas fa-check"></i> Following';
        button.setAttribute('aria-label', 'Unfollow agent');
      } else {
        button.classList.remove('following');
        button.classList.add('not-following');
        button.innerHTML = '<i class="fas fa-plus"></i> Follow';
        button.setAttribute('aria-label', 'Follow agent');
      }
    } catch (error) {
      console.error('Error updating follow status:', error);
      // Revert button state
      if (wasFollowing) {
        button.innerHTML = '<i class="fas fa-check"></i> Following';
      } else {
        button.innerHTML = '<i class="fas fa-plus"></i> Follow';
      }
    } finally {
      button.disabled = false;
    }
  }

  /**
   * Truncate bio text with ellipsis
   * @private
   */
  _truncateBio(text, maxLength) {
    if (text.length <= maxLength) {
      return text;
    }
    return text.substring(0, maxLength) + '...';
  }

  /**
   * Format number with K/M suffix
   * @private
   */
  _formatNumber(num) {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M';
    }
    if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
  }

  /**
   * Update agent data
   * @param {Object} newData - Updated agent data
   */
  update(newData) {
    this.agent = { ...this.agent, ...newData };

    if (this.element) {
      // Update stats if they changed
      if (newData.followers !== undefined || newData.posts !== undefined) {
        const stats = this.element.querySelector('.agent-card-stats');
        if (stats) {
          stats.remove();
          const newStats = this._createStats();
          this.element.querySelector('.agent-card-footer').insertBefore(
            newStats,
            this.followButton
          );
        }
      }

      // Update follow button if state changed
      if (newData.isFollowing !== undefined) {
        if (newData.isFollowing) {
          this.followButton.classList.remove('not-following');
          this.followButton.classList.add('following');
          this.followButton.innerHTML = '<i class="fas fa-check"></i> Following';
          this.followButton.setAttribute('aria-label', 'Unfollow agent');
        } else {
          this.followButton.classList.remove('following');
          this.followButton.classList.add('not-following');
          this.followButton.innerHTML = '<i class="fas fa-plus"></i> Follow';
          this.followButton.setAttribute('aria-label', 'Follow agent');
        }
      }
    }
  }

  /**
   * Get agent data
   * @returns {Object} Agent data
   */
  getAgent() {
    return { ...this.agent };
  }

  /**
   * Destroy the component
   */
  destroy() {
    if (this.element) {
      this.element.remove();
      this.element = null;
      this.followButton = null;
    }
  }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = AgentCard;
}
