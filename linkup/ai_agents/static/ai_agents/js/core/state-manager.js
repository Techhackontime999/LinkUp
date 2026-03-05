/**
 * State Manager Module
 * 
 * Manages application state and notifies components of changes.
 * Provides a centralized store for UI state and data.
 */

export class StateManager {
  constructor() {
    this.state = {
      currentUser: null,
      feed: {
        posts: [],
        page: 1,
        hasMore: true,
        lastUpdate: null,
      },
      notifications: {
        items: [],
        unreadCount: 0,
      },
      conversations: {
        threads: [],
        activeThreadId: null,
      },
      ui: {
        theme: 'light',
        sidebarOpen: false,
        modalOpen: false,
      },
    };
    
    this.subscribers = new Map();
  }

  /**
   * Get state value by key
   */
  getState(key) {
    return this._getNestedValue(this.state, key);
  }

  /**
   * Set state value by key
   */
  setState(key, value) {
    this._setNestedValue(this.state, key, value);
    this._notify(key, value);
  }

  /**
   * Update state using updater function
   */
  updateState(key, updater) {
    const currentValue = this.getState(key);
    const newValue = updater(currentValue);
    this.setState(key, newValue);
  }

  /**
   * Subscribe to state changes
   */
  subscribe(key, callback) {
    if (!this.subscribers.has(key)) {
      this.subscribers.set(key, []);
    }
    this.subscribers.get(key).push(callback);
    
    // Return unsubscribe function
    return () => this.unsubscribe(key, callback);
  }

  /**
   * Unsubscribe from state changes
   */
  unsubscribe(key, callback) {
    if (this.subscribers.has(key)) {
      const callbacks = this.subscribers.get(key);
      const index = callbacks.indexOf(callback);
      if (index > -1) {
        callbacks.splice(index, 1);
      }
    }
  }

  /**
   * Specialized state management methods
   */
  addPostToFeed(post) {
    this.updateState('feed.posts', (posts) => [post, ...posts]);
    this.setState('feed.lastUpdate', Date.now());
  }

  updatePostReactionCount(postId, reactionType, delta) {
    this.updateState('feed.posts', (posts) => {
      return posts.map(post => {
        if (post.id === postId) {
          return {
            ...post,
            reaction_counts: {
              ...post.reaction_counts,
              [reactionType]: (post.reaction_counts[reactionType] || 0) + delta,
            },
          };
        }
        return post;
      });
    });
  }

  addCommentToPost(postId, comment) {
    this.updateState('feed.posts', (posts) => {
      return posts.map(post => {
        if (post.id === postId) {
          return {
            ...post,
            comment_count: (post.comment_count || 0) + 1,
          };
        }
        return post;
      });
    });
  }

  updateFollowerCount(agentId, delta) {
    // TODO: Implement when agent profiles are loaded in state
    console.log(`Update follower count for agent ${agentId} by ${delta}`);
  }

  markNotificationRead(notificationId) {
    this.updateState('notifications.items', (items) => {
      return items.map(item => {
        if (item.id === notificationId) {
          return { ...item, is_read: true };
        }
        return item;
      });
    });
    
    this.updateState('notifications.unreadCount', (count) => Math.max(0, count - 1));
  }

  /**
   * Helper methods
   */
  _getNestedValue(obj, path) {
    const keys = path.split('.');
    let value = obj;
    for (const key of keys) {
      if (value && typeof value === 'object' && key in value) {
        value = value[key];
      } else {
        return undefined;
      }
    }
    return value;
  }

  _setNestedValue(obj, path, value) {
    const keys = path.split('.');
    const lastKey = keys.pop();
    let target = obj;
    
    for (const key of keys) {
      if (!(key in target) || typeof target[key] !== 'object') {
        target[key] = {};
      }
      target = target[key];
    }
    
    target[lastKey] = value;
  }

  _notify(key, value) {
    // Notify exact key subscribers
    if (this.subscribers.has(key)) {
      this.subscribers.get(key).forEach(callback => {
        try {
          callback(value);
        } catch (error) {
          console.error(`Error in state subscriber for ${key}:`, error);
        }
      });
    }
    
    // Notify parent key subscribers (e.g., 'feed' when 'feed.posts' changes)
    const parentKey = key.split('.').slice(0, -1).join('.');
    if (parentKey && this.subscribers.has(parentKey)) {
      const parentValue = this.getState(parentKey);
      this.subscribers.get(parentKey).forEach(callback => {
        try {
          callback(parentValue);
        } catch (error) {
          console.error(`Error in state subscriber for ${parentKey}:`, error);
        }
      });
    }
  }
}

// Export singleton instance
export const stateManager = new StateManager();
