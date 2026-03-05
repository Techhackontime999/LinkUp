/**
 * App Initialization Module
 * 
 * Initializes all core modules and sets up the application on page load.
 * Handles:
 * - APIClient initialization with CSRF token
 * - WebSocketManager initialization with authentication
 * - StateManager initialization with initial state
 * - Global error handlers setup
 * - Page-specific module initialization
 * - Navigation and routing
 */

import { APIClient, apiClient } from './core/api-client.js';
import { WebSocketManager, initWebSocketManager } from './core/websocket-manager.js';
import { StateManager, stateManager } from './core/state-manager.js';
import { AuthManager, authManager } from './core/auth-manager.js';
import { ErrorHandler, errorHandler } from './core/error-handler.js';
import { PollingService } from './core/polling-service.js';
import { initializeStateSubscriptions } from './core/state-subscriptions.js';
import { createRouter } from './core/router.js';

// Import page modules
import { FeedPage } from './pages/feed.js';
import { ProfilePage } from './pages/profile.js';
import { DiscoveryPage } from './pages/discovery.js';
import { MessagesPage } from './pages/messages.js';
import { CommunicationPage } from './pages/communication.js';
import { AnalyticsPage } from './pages/analytics.js';
import { NotificationsPage } from './pages/notifications.js';
import { ModerationPage } from './pages/moderation.js';

/**
 * Global app instance
 */
class SocialPlatformApp {
  constructor() {
    this.apiClient = apiClient;
    this.stateManager = stateManager;
    this.authManager = authManager;
    this.errorHandler = errorHandler;
    this.websocketManager = null;
    this.pollingService = null;
    this.router = null;
    this.pageModules = new Map();
  }

  /**
   * Initialize the application
   */
  async init() {
    try {
      console.log('Initializing Social Platform App...');

      // Step 1: Verify authentication
      if (!this.authManager.isAuthenticated()) {
        console.warn('User not authenticated, redirecting to login');
        this.authManager.redirectToLogin();
        return;
      }

      // Step 2: Initialize core modules
      await this._initializeCoreModules();

      // Step 3: Set up global error handlers
      this._setupGlobalErrorHandlers();

      // Step 4: Initialize page-specific modules
      await this._initializePageModules();

      // Step 5: Set up navigation
      this._setupNavigation();

      // Step 6: Load initial page
      await this._loadCurrentPage();

      console.log('Social Platform App initialized successfully');
    } catch (error) {
      console.error('Failed to initialize app:', error);
      this.errorHandler.handleAPIError(error, 'App initialization');
    }
  }

  /**
   * Initialize core modules
   * @private
   */
  async _initializeCoreModules() {
    console.log('Initializing core modules...');

    // APIClient is already initialized with CSRF token
    console.log('APIClient initialized');

    // Initialize WebSocketManager
    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/social/`;
      
      this.websocketManager = initWebSocketManager(wsUrl, this.authManager.sessionToken);
      
      // Set up polling fallback
      this.pollingService = new PollingService(this.apiClient);
      this.websocketManager.setPollingFallback(() => {
        console.log('Switching to polling fallback');
        this.pollingService.start();
      });

      // Attempt to connect WebSocket
      await this.websocketManager.connect();
      console.log('WebSocketManager initialized and connected');
    } catch (error) {
      console.warn('WebSocket connection failed, will use polling:', error);
      // Polling will be started as fallback
    }

    // StateManager is already initialized
    console.log('StateManager initialized');

    // Load initial state from server
    await this._loadInitialState();

    // Initialize state subscriptions
    this._initializeStateSubscriptions();
  }

  /**
   * Load initial state from server
   * @private
   */
  async _loadInitialState() {
    try {
      // Load current user info
      const userResponse = await this.apiClient.get('/api/auth/user/');
      if (userResponse.success && userResponse.data) {
        this.stateManager.setState('currentUser', userResponse.data);
      }

      // Load initial notifications
      const notificationsResponse = await this.apiClient.getNotifications(true);
      if (notificationsResponse.success && notificationsResponse.data) {
        const items = Array.isArray(notificationsResponse.data) 
          ? notificationsResponse.data 
          : notificationsResponse.data.results || [];
        this.stateManager.setState('notifications.items', items);
        this.stateManager.setState('notifications.unreadCount', items.length);
      }
    } catch (error) {
      console.warn('Error loading initial state:', error);
      // Continue anyway, state will be loaded on demand
    }
  }

  /**
   * Initialize state subscriptions
   * @private
   */
  _initializeStateSubscriptions() {
    console.log('Initializing state subscriptions...');

    // Get or create notification bell
    let notificationBell = null;
    const bellContainer = document.getElementById('notification-bell-container');
    if (bellContainer) {
      // Import and initialize NotificationBell
      import('./components/notification-bell.js').then(({ NotificationBell }) => {
        notificationBell = new NotificationBell({ container: bellContainer });
        notificationBell.render();
        
        // Initialize state subscriptions with notification bell
        initializeStateSubscriptions(this.websocketManager, notificationBell);
      }).catch(error => {
        console.error('Error initializing NotificationBell:', error);
        // Initialize without notification bell
        initializeStateSubscriptions(this.websocketManager, null);
      });
    } else {
      // Initialize without notification bell
      initializeStateSubscriptions(this.websocketManager, null);
    }
  }

  /**
   * Set up global error handlers
   * @private
   */
  _setupGlobalErrorHandlers() {
    console.log('Setting up global error handlers...');

    // Handle unhandled promise rejections
    window.addEventListener('unhandledrejection', (event) => {
      console.error('Unhandled promise rejection:', event.reason);
      this.errorHandler.logError(event.reason, 'Unhandled Promise Rejection');
    });

    // Handle global errors
    window.addEventListener('error', (event) => {
      console.error('Global error:', event.error);
      this.errorHandler.logError(event.error, 'Global Error');
    });

    // Handle fetch errors globally
    const originalFetch = window.fetch;
    window.fetch = async function(...args) {
      try {
        const response = await originalFetch.apply(this, args);
        if (!response.ok && response.status >= 500) {
          console.error(`Server error: ${response.status} ${response.statusText}`);
        }
        return response;
      } catch (error) {
        console.error('Fetch error:', error);
        throw error;
      }
    };
  }

  /**
   * Initialize page-specific modules
   * @private
   */
  async _initializePageModules() {
    console.log('Initializing page modules...');

    // Create router
    this.router = createRouter({
      baseUrl: '/',
      enableHistoryAPI: true,
    });

    // Register page modules as routes
    this.router.registerRoutes({
      '/': FeedPage,
      '/feed': FeedPage,
      '/profile/:id': ProfilePage,
      '/discover': DiscoveryPage,
      '/messages': MessagesPage,
      '/communicate': CommunicationPage,
      '/analytics/:id': AnalyticsPage,
      '/notifications': NotificationsPage,
      '/moderation': ModerationPage,
    });

    // Set up page initialization with shared services
    this.router.beforeNavigate(async (path, params) => {
      console.log(`Before navigate to ${path}`);
      return true;
    });

    this.router.afterNavigate(async (path, params, page) => {
      console.log(`After navigate to ${path}`);
      
      // Inject shared services into page
      if (page) {
        page.apiClient = this.apiClient;
        page.stateManager = this.stateManager;
        page.authManager = this.authManager;
        page.errorHandler = this.errorHandler;
        page.websocketManager = this.websocketManager;
        page.router = this.router;
      }

      // Update active navigation link
      this._updateActiveNavLink(path);
    });

    // Set up page cleanup
    this.router.onPageCleanup(async (page) => {
      console.log('Cleaning up page');
      // Page cleanup is handled by router
    });

    // Initialize router
    this.router.init();

    console.log('Router initialized with page modules');
  }

  /**
   * Set up navigation and routing
   * @private
   */
  _setupNavigation() {
    console.log('Setting up navigation...');

    // Handle navigation links with data-navigate attribute
    document.addEventListener('click', (event) => {
      const link = event.target.closest('a[data-navigate]');
      if (link) {
        event.preventDefault();
        const path = link.dataset.navigate;
        this.router.navigate(path);
      }
    });

    // Handle navigation links with data-page attribute (legacy)
    document.addEventListener('click', (event) => {
      const link = event.target.closest('a[data-page]');
      if (link) {
        event.preventDefault();
        const page = link.dataset.page;
        const path = this._pageToPath(page);
        this.router.navigate(path);
      }
    });
  }

  /**
   * Convert page name to path
   * @private
   */
  _pageToPath(page) {
    const pathMap = {
      'feed': '/feed',
      'profile': '/profile',
      'discovery': '/discover',
      'messages': '/messages',
      'communication': '/communicate',
      'analytics': '/analytics',
      'notifications': '/notifications',
      'moderation': '/moderation',
    };
    return pathMap[page] || `/${page}`;
  }

  /**
   * Load the current page based on URL
   * @private
   */
  async _loadCurrentPage() {
    // Determine current page from URL or default to feed
    const path = window.location.pathname;
    let targetPath = '/feed';

    if (path.includes('/profile/')) {
      targetPath = path;
    } else if (path.includes('/discover')) {
      targetPath = '/discover';
    } else if (path.includes('/messages')) {
      targetPath = '/messages';
    } else if (path.includes('/communicate')) {
      targetPath = '/communicate';
    } else if (path.includes('/analytics/')) {
      targetPath = path;
    } else if (path.includes('/notifications')) {
      targetPath = '/notifications';
    } else if (path.includes('/moderation')) {
      targetPath = '/moderation';
    }

    try {
      await this.router.navigate(targetPath, {}, { updateHistory: false });
    } catch (error) {
      console.error('Error loading current page:', error);
      // Fall back to feed
      await this.router.navigate('/feed', {}, { updateHistory: false });
    }
  }

  /**
   * Update active navigation link
   * @private
   */
  _updateActiveNavLink(page) {
    // Remove active class from all nav links
    document.querySelectorAll('[data-page]').forEach(link => {
      link.classList.remove('active');
    });

    // Add active class to current page link
    const activeLink = document.querySelector(`[data-page="${page}"]`);
    if (activeLink) {
      activeLink.classList.add('active');
    }
  }

  /**
   * Subscribe to state changes
   */
  subscribeToState(key, callback) {
    return this.stateManager.subscribe(key, callback);
  }

  /**
   * Get current state
   */
  getState(key) {
    return this.stateManager.getState(key);
  }

  /**
   * Cleanup and shutdown
   */
  async shutdown() {
    console.log('Shutting down app...');

    // Clean up current page via router
    if (this.router && this.router.currentPage) {
      if (typeof this.router.currentPage.cleanup === 'function') {
        try {
          await this.router.currentPage.cleanup();
        } catch (error) {
          console.error('Error cleaning up page:', error);
        }
      }
    }

    // Disconnect WebSocket
    if (this.websocketManager) {
      this.websocketManager.disconnect();
    }

    // Stop polling
    if (this.pollingService) {
      this.pollingService.stop();
    }

    console.log('App shutdown complete');
  }
}

/**
 * Global app instance
 */
let app = null;

/**
 * Initialize app when DOM is ready
 */
function initializeApp() {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      app = new SocialPlatformApp();
      app.init().catch(error => {
        console.error('Fatal error during app initialization:', error);
      });
    });
  } else {
    app = new SocialPlatformApp();
    app.init().catch(error => {
      console.error('Fatal error during app initialization:', error);
    });
  }
}

/**
 * Handle page unload
 */
window.addEventListener('beforeunload', () => {
  if (app) {
    app.shutdown();
  }
});

// Export for use in other modules
export { SocialPlatformApp, app, initializeApp };

// Initialize app on script load
initializeApp();
