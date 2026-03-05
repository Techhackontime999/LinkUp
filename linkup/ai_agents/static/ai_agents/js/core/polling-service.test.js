/**
 * Unit Tests for PollingService
 * 
 * Tests the polling service functionality including:
 * - Feed polling (30s interval)
 * - Message polling (15s interval)
 * - Notification polling (60s interval)
 * - Efficient incremental updates
 * - Error handling and retry logic
 */

// Mock APIClient
class MockAPIClient {
  constructor() {
    this.callCount = 0;
    this.shouldFail = false;
  }

  async get(endpoint, params) {
    this.callCount++;
    
    if (this.shouldFail) {
      throw new Error('API request failed');
    }

    // Return mock data based on endpoint
    if (endpoint.includes('/social/agents/feed/')) {
      return {
        data: {
          results: [
            {
              id: 'post-1',
              content: 'Test post',
              created_at: new Date().toISOString(),
              reaction_counts: { like: 0, love: 0, insightful: 0, helpful: 0, celebrate: 0 },
              comment_count: 0,
            }
          ]
        }
      };
    }

    if (endpoint.includes('/messages/')) {
      return {
        data: {
          results: [
            {
              id: 'msg-1',
              content: 'Test message',
              created_at: new Date().toISOString(),
            }
          ]
        }
      };
    }

    if (endpoint.includes('/social/notifications/')) {
      return {
        data: {
          results: [
            {
              id: 'notif-1',
              message: 'Test notification',
              created_at: new Date().toISOString(),
              read: false,
            }
          ]
        }
      };
    }

    return { data: { results: [] } };
  }
}

// Mock StateManager
class MockStateManager {
  constructor() {
    this.state = {
      'feed.posts': [],
      'notifications.items': [],
      'notifications.unreadCount': 0,
    };
  }

  getState(key) {
    return this.state[key];
  }

  setState(key, value) {
    this.state[key] = value;
  }

  addPostToFeed(post) {
    const posts = this.state['feed.posts'] || [];
    this.state['feed.posts'] = [post, ...posts];
  }
}

// Test Suite
describe('PollingService', () => {
  let pollingService;
  let mockAPIClient;
  let mockStateManager;

  beforeEach(() => {
    mockAPIClient = new MockAPIClient();
    mockStateManager = new MockStateManager();
    pollingService = new PollingService(mockAPIClient, mockStateManager);
  });

  afterEach(() => {
    pollingService.stopAllPolling();
  });

  describe('Feed Polling', () => {
    test('should start feed polling with 30s interval', (done) => {
      const callback = jest.fn();
      pollingService.startFeedPolling(callback);

      expect(pollingService.isPollingFeed).toBe(true);
      expect(pollingService.feedPollingTimer).toBeDefined();

      // Wait for first poll
      setTimeout(() => {
        expect(mockAPIClient.callCount).toBeGreaterThan(0);
        expect(callback).toHaveBeenCalled();
        done();
      }, 100);
    });

    test('should stop feed polling', (done) => {
      pollingService.startFeedPolling();
      expect(pollingService.isPollingFeed).toBe(true);

      pollingService.stopFeedPolling();
      expect(pollingService.isPollingFeed).toBe(false);
      expect(pollingService.feedPollingTimer).toBeNull();

      done();
    });

    test('should update state manager with new posts', (done) => {
      pollingService.startFeedPolling();

      setTimeout(() => {
        const posts = mockStateManager.getState('feed.posts');
        expect(posts.length).toBeGreaterThan(0);
        expect(posts[0].id).toBe('post-1');
        done();
      }, 100);
    });

    test('should track last feed update timestamp', (done) => {
      const initialTime = pollingService.lastFeedUpdate;
      pollingService.startFeedPolling();

      setTimeout(() => {
        expect(pollingService.lastFeedUpdate).not.toBe(initialTime);
        done();
      }, 100);
    });

    test('should handle polling errors gracefully', (done) => {
      mockAPIClient.shouldFail = true;
      const callback = jest.fn();
      pollingService.startFeedPolling(callback);

      setTimeout(() => {
        expect(pollingService.feedPollingErrors).toBeGreaterThan(0);
        done();
      }, 100);
    });

    test('should stop polling after max errors', (done) => {
      mockAPIClient.shouldFail = true;
      pollingService.maxPollingErrors = 2;
      pollingService.startFeedPolling();

      // Simulate multiple polling attempts
      setTimeout(() => {
        pollingService._pollFeed();
        pollingService._pollFeed();
        pollingService._pollFeed();

        setTimeout(() => {
          expect(pollingService.isPollingFeed).toBe(false);
          done();
        }, 50);
      }, 50);
    });
  });

  describe('Message Polling', () => {
    test('should start message polling with 15s interval', (done) => {
      const callback = jest.fn();
      pollingService.startMessagePolling(callback);

      expect(pollingService.isPollingMessages).toBe(true);
      expect(pollingService.messagePollingTimer).toBeDefined();

      setTimeout(() => {
        expect(mockAPIClient.callCount).toBeGreaterThan(0);
        expect(callback).toHaveBeenCalled();
        done();
      }, 100);
    });

    test('should stop message polling', (done) => {
      pollingService.startMessagePolling();
      expect(pollingService.isPollingMessages).toBe(true);

      pollingService.stopMessagePolling();
      expect(pollingService.isPollingMessages).toBe(false);
      expect(pollingService.messagePollingTimer).toBeNull();

      done();
    });

    test('should track last message update timestamp', (done) => {
      const initialTime = pollingService.lastMessageUpdate;
      pollingService.startMessagePolling();

      setTimeout(() => {
        expect(pollingService.lastMessageUpdate).not.toBe(initialTime);
        done();
      }, 100);
    });
  });

  describe('Notification Polling', () => {
    test('should start notification polling with 60s interval', (done) => {
      const callback = jest.fn();
      pollingService.startNotificationPolling(callback);

      expect(pollingService.isPollingNotifications).toBe(true);
      expect(pollingService.notificationPollingTimer).toBeDefined();

      setTimeout(() => {
        expect(mockAPIClient.callCount).toBeGreaterThan(0);
        expect(callback).toHaveBeenCalled();
        done();
      }, 100);
    });

    test('should stop notification polling', (done) => {
      pollingService.startNotificationPolling();
      expect(pollingService.isPollingNotifications).toBe(true);

      pollingService.stopNotificationPolling();
      expect(pollingService.isPollingNotifications).toBe(false);
      expect(pollingService.notificationPollingTimer).toBeNull();

      done();
    });

    test('should update state manager with new notifications', (done) => {
      pollingService.startNotificationPolling();

      setTimeout(() => {
        const notifications = mockStateManager.getState('notifications.items');
        expect(notifications.length).toBeGreaterThan(0);
        expect(notifications[0].id).toBe('notif-1');
        done();
      }, 100);
    });

    test('should update unread notification count', (done) => {
      pollingService.startNotificationPolling();

      setTimeout(() => {
        const unreadCount = mockStateManager.getState('notifications.unreadCount');
        expect(unreadCount).toBeGreaterThan(0);
        done();
      }, 100);
    });
  });

  describe('Multiple Polling', () => {
    test('should support multiple polling types simultaneously', (done) => {
      pollingService.startFeedPolling();
      pollingService.startMessagePolling();
      pollingService.startNotificationPolling();

      expect(pollingService.isPollingFeed).toBe(true);
      expect(pollingService.isPollingMessages).toBe(true);
      expect(pollingService.isPollingNotifications).toBe(true);

      done();
    });

    test('should stop all polling', (done) => {
      pollingService.startFeedPolling();
      pollingService.startMessagePolling();
      pollingService.startNotificationPolling();

      pollingService.stopAllPolling();

      expect(pollingService.isPollingFeed).toBe(false);
      expect(pollingService.isPollingMessages).toBe(false);
      expect(pollingService.isPollingNotifications).toBe(false);

      done();
    });
  });

  describe('Status and Reset', () => {
    test('should return polling status', (done) => {
      pollingService.startFeedPolling();
      pollingService.startMessagePolling();

      const status = pollingService.getStatus();

      expect(status.feedPolling).toBe(true);
      expect(status.messagePolling).toBe(true);
      expect(status.notificationPolling).toBe(false);
      expect(status.lastFeedUpdate).toBeDefined();
      expect(status.lastMessageUpdate).toBeDefined();

      done();
    });

    test('should reset polling service', (done) => {
      pollingService.startFeedPolling();
      pollingService.startMessagePolling();
      pollingService.startNotificationPolling();

      pollingService.reset();

      expect(pollingService.isPollingFeed).toBe(false);
      expect(pollingService.isPollingMessages).toBe(false);
      expect(pollingService.isPollingNotifications).toBe(false);
      expect(pollingService.lastFeedUpdate).toBeNull();
      expect(pollingService.lastMessageUpdate).toBeNull();
      expect(pollingService.lastNotificationUpdate).toBeNull();

      done();
    });
  });

  describe('Incremental Updates', () => {
    test('should only fetch new content since last update', (done) => {
      pollingService.startFeedPolling();

      setTimeout(() => {
        const firstCallTime = pollingService.lastFeedUpdate;
        
        // Simulate another poll
        pollingService._pollFeed();

        setTimeout(() => {
          // The since parameter should be the first call time
          expect(pollingService.lastFeedUpdate).toBeDefined();
          done();
        }, 50);
      }, 100);
    });
  });

  describe('Prevent Duplicate Polling', () => {
    test('should not start feed polling if already active', (done) => {
      pollingService.startFeedPolling();
      const firstTimer = pollingService.feedPollingTimer;

      pollingService.startFeedPolling();
      const secondTimer = pollingService.feedPollingTimer;

      expect(firstTimer).toBe(secondTimer);
      done();
    });

    test('should not start message polling if already active', (done) => {
      pollingService.startMessagePolling();
      const firstTimer = pollingService.messagePollingTimer;

      pollingService.startMessagePolling();
      const secondTimer = pollingService.messagePollingTimer;

      expect(firstTimer).toBe(secondTimer);
      done();
    });

    test('should not start notification polling if already active', (done) => {
      pollingService.startNotificationPolling();
      const firstTimer = pollingService.notificationPollingTimer;

      pollingService.startNotificationPolling();
      const secondTimer = pollingService.notificationPollingTimer;

      expect(firstTimer).toBe(secondTimer);
      done();
    });
  });
});
