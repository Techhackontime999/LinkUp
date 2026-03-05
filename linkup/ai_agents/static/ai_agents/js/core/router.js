/**
 * Router Module
 * 
 * Handles client-side navigation and routing between pages.
 * Manages URL history, page transitions, and cleanup.
 */

/**
 * Router class for managing client-side navigation
 */
export class Router {
  constructor(options = {}) {
    this.routes = new Map();
    this.currentRoute = null;
    this.currentPage = null;
    this.pageCleanupCallbacks = [];
    this.beforeNavigateCallbacks = [];
    this.afterNavigateCallbacks = [];
    this.baseUrl = options.baseUrl || '/';
    this.enableHistoryAPI = options.enableHistoryAPI !== false;
  }

  /**
   * Register a route
   * @param {string} path - Route path (e.g., '/feed', '/profile/:id')
   * @param {Function} handler - Handler function or page class
   */
  registerRoute(path, handler) {
    this.routes.set(path, handler);
    console.log(`Route registered: ${path}`);
  }

  /**
   * Register multiple routes
   * @param {Object} routeMap - Map of path -> handler
   */
  registerRoutes(routeMap) {
    Object.entries(routeMap).forEach(([path, handler]) => {
      this.registerRoute(path, handler);
    });
  }

  /**
   * Navigate to a route
   * @param {string} path - Route path
   * @param {Object} params - Route parameters
   * @param {Object} options - Navigation options
   */
  async navigate(path, params = {}, options = {}) {
    try {
      // Call before navigate callbacks
      for (const callback of this.beforeNavigateCallbacks) {
        const shouldContinue = await callback(path, params);
        if (shouldContinue === false) {
          console.log('Navigation cancelled by before callback');
          return false;
        }
      }

      // Clean up current page
      await this._cleanupCurrentPage();

      // Find matching route
      const route = this._findMatchingRoute(path);
      if (!route) {
        throw new Error(`No route found for path: ${path}`);
      }

      // Load page
      const { handler, params: routeParams } = route;
      const mergedParams = { ...routeParams, ...params };

      console.log(`Navigating to: ${path}`, mergedParams);

      // Create page instance
      const page = await this._createPageInstance(handler, mergedParams);
      this.currentPage = page;
      this.currentRoute = { path, params: mergedParams, handler };

      // Update URL if history API is enabled
      if (this.enableHistoryAPI && options.updateHistory !== false) {
        const url = this._buildUrl(path, mergedParams);
        window.history.pushState({ path, params: mergedParams }, '', url);
      }

      // Call after navigate callbacks
      for (const callback of this.afterNavigateCallbacks) {
        await callback(path, mergedParams, page);
      }

      return true;
    } catch (error) {
      console.error(`Navigation error for ${path}:`, error);
      throw error;
    }
  }

  /**
   * Go back in history
   */
  back() {
    window.history.back();
  }

  /**
   * Go forward in history
   */
  forward() {
    window.history.forward();
  }

  /**
   * Register before navigate callback
   * @param {Function} callback - Callback function
   */
  beforeNavigate(callback) {
    this.beforeNavigateCallbacks.push(callback);
  }

  /**
   * Register after navigate callback
   * @param {Function} callback - Callback function
   */
  afterNavigate(callback) {
    this.afterNavigateCallbacks.push(callback);
  }

  /**
   * Register page cleanup callback
   * @param {Function} callback - Cleanup function
   */
  onPageCleanup(callback) {
    this.pageCleanupCallbacks.push(callback);
  }

  /**
   * Get current route
   */
  getCurrentRoute() {
    return this.currentRoute;
  }

  /**
   * Get current page
   */
  getCurrentPage() {
    return this.currentPage;
  }

  /**
   * Find matching route for path
   * @private
   */
  _findMatchingRoute(path) {
    // Exact match
    if (this.routes.has(path)) {
      return { handler: this.routes.get(path), params: {} };
    }

    // Pattern match (e.g., /profile/:id)
    for (const [routePath, handler] of this.routes) {
      const params = this._matchPath(routePath, path);
      if (params !== null) {
        return { handler, params };
      }
    }

    return null;
  }

  /**
   * Match path pattern against actual path
   * @private
   */
  _matchPath(pattern, path) {
    const patternParts = pattern.split('/').filter(p => p);
    const pathParts = path.split('/').filter(p => p);

    if (patternParts.length !== pathParts.length) {
      return null;
    }

    const params = {};
    for (let i = 0; i < patternParts.length; i++) {
      const patternPart = patternParts[i];
      const pathPart = pathParts[i];

      if (patternPart.startsWith(':')) {
        // Parameter
        const paramName = patternPart.slice(1);
        params[paramName] = pathPart;
      } else if (patternPart !== pathPart) {
        // Mismatch
        return null;
      }
    }

    return params;
  }

  /**
   * Create page instance
   * @private
   */
  async _createPageInstance(handler, params) {
    if (typeof handler === 'function') {
      // Check if it's a class (constructor function)
      if (handler.prototype && handler.prototype.constructor === handler) {
        // It's a class, instantiate it
        const instance = new handler();
        
        // Initialize if init method exists
        if (typeof instance.init === 'function') {
          await instance.init(params);
        }
        
        return instance;
      } else {
        // It's a regular function, call it
        return await handler(params);
      }
    }

    throw new Error('Handler must be a function or class');
  }

  /**
   * Clean up current page
   * @private
   */
  async _cleanupCurrentPage() {
    if (this.currentPage) {
      // Call cleanup method if exists
      if (typeof this.currentPage.cleanup === 'function') {
        try {
          await this.currentPage.cleanup();
        } catch (error) {
          console.error('Error cleaning up page:', error);
        }
      }

      // Call registered cleanup callbacks
      for (const callback of this.pageCleanupCallbacks) {
        try {
          await callback(this.currentPage);
        } catch (error) {
          console.error('Error in cleanup callback:', error);
        }
      }
    }
  }

  /**
   * Build URL from path and params
   * @private
   */
  _buildUrl(path, params) {
    let url = path;
    
    // Replace path parameters
    Object.entries(params).forEach(([key, value]) => {
      url = url.replace(`:${key}`, value);
    });

    // Add query parameters
    const queryParams = Object.entries(params)
      .filter(([key]) => !path.includes(`:${key}`))
      .map(([key, value]) => `${key}=${encodeURIComponent(value)}`)
      .join('&');

    if (queryParams) {
      url += `?${queryParams}`;
    }

    return url;
  }

  /**
   * Handle browser back/forward buttons
   */
  setupHistoryListener() {
    window.addEventListener('popstate', (event) => {
      if (event.state && event.state.path) {
        this.navigate(event.state.path, event.state.params || {}, { updateHistory: false });
      }
    });
  }

  /**
   * Handle navigation links
   */
  setupLinkListener(selector = 'a[data-navigate]') {
    document.addEventListener('click', (event) => {
      const link = event.target.closest(selector);
      if (link) {
        event.preventDefault();
        const path = link.dataset.navigate;
        this.navigate(path);
      }
    });
  }

  /**
   * Initialize router
   */
  init() {
    this.setupHistoryListener();
    this.setupLinkListener();
    console.log('Router initialized');
  }
}

/**
 * Create router instance
 */
export function createRouter(options = {}) {
  return new Router(options);
}
