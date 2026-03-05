/**
 * Browser Compatibility Tests
 * 
 * Tests core functionality across different browsers and environments.
 * Validates that the application works correctly on all supported browsers.
 */

/**
 * Test browser API support
 */
export function testBrowserAPIs() {
  const results = {
    fetch: typeof fetch !== 'undefined',
    websocket: typeof WebSocket !== 'undefined',
    localStorage: typeof localStorage !== 'undefined',
    sessionStorage: typeof sessionStorage !== 'undefined',
    indexedDB: typeof indexedDB !== 'undefined',
    serviceWorker: 'serviceWorker' in navigator,
    vibration: 'vibrate' in navigator,
    webShare: 'share' in navigator,
    geolocation: 'geolocation' in navigator,
    notification: 'Notification' in window,
    mediaDevices: 'mediaDevices' in navigator,
    clipboard: 'clipboard' in navigator,
  };

  console.log('Browser API Support:', results);
  return results;
}

/**
 * Test ES6 features
 */
export function testES6Features() {
  const results = {
    arrow_functions: (() => true)(),
    template_literals: `test` === 'test',
    destructuring: (() => {
      const [a] = [1];
      return a === 1;
    })(),
    spread_operator: (() => {
      const arr = [...[1, 2, 3]];
      return arr.length === 3;
    })(),
    classes: (() => {
      class Test {}
      return new Test() instanceof Test;
    })(),
    promises: typeof Promise !== 'undefined',
    async_await: (() => {
      try {
        eval('(async () => {})');
        return true;
      } catch {
        return false;
      }
    })(),
    modules: typeof import !== 'undefined',
  };

  console.log('ES6 Features Support:', results);
  return results;
}

/**
 * Test CSS features
 */
export function testCSSFeatures() {
  const div = document.createElement('div');
  const style = div.style;

  const results = {
    flexbox: (() => {
      style.display = 'flex';
      return style.display === 'flex';
    })(),
    grid: (() => {
      style.display = 'grid';
      return style.display === 'grid';
    })(),
    css_variables: (() => {
      style.setProperty('--test', 'value');
      return style.getPropertyValue('--test') === 'value';
    })(),
    transforms: (() => {
      style.transform = 'translate(0, 0)';
      return style.transform !== '';
    })(),
    transitions: (() => {
      style.transition = 'all 0.3s ease';
      return style.transition !== '';
    })(),
    animations: (() => {
      style.animation = 'test 1s';
      return style.animation !== '';
    })(),
    backdrop_filter: (() => {
      style.backdropFilter = 'blur(10px)';
      return style.backdropFilter !== '';
    })(),
  };

  console.log('CSS Features Support:', results);
  return results;
}

/**
 * Test DOM APIs
 */
export function testDOMAPIs() {
  const results = {
    querySelector: typeof document.querySelector === 'function',
    querySelectorAll: typeof document.querySelectorAll === 'function',
    getElementById: typeof document.getElementById === 'function',
    getElementsByClassName: typeof document.getElementsByClassName === 'function',
    addEventListener: typeof document.addEventListener === 'function',
    removeEventListener: typeof document.removeEventListener === 'function',
    createElement: typeof document.createElement === 'function',
    appendChild: typeof document.body.appendChild === 'function',
    removeChild: typeof document.body.removeChild === 'function',
    classList: 'classList' in document.createElement('div'),
    dataset: 'dataset' in document.createElement('div'),
    innerHTML: 'innerHTML' in document.createElement('div'),
    textContent: 'textContent' in document.createElement('div'),
  };

  console.log('DOM APIs Support:', results);
  return results;
}

/**
 * Test network APIs
 */
export function testNetworkAPIs() {
  const results = {
    fetch: typeof fetch !== 'undefined',
    xhr: typeof XMLHttpRequest !== 'undefined',
    websocket: typeof WebSocket !== 'undefined',
    navigator_online: 'onLine' in navigator,
    online_event: 'online' in window,
    offline_event: 'offline' in window,
  };

  console.log('Network APIs Support:', results);
  return results;
}

/**
 * Test storage APIs
 */
export function testStorageAPIs() {
  const results = {
    localStorage: (() => {
      try {
        localStorage.setItem('test', 'value');
        localStorage.removeItem('test');
        return true;
      } catch {
        return false;
      }
    })(),
    sessionStorage: (() => {
      try {
        sessionStorage.setItem('test', 'value');
        sessionStorage.removeItem('test');
        return true;
      } catch {
        return false;
      }
    })(),
    indexedDB: (() => {
      try {
        return typeof indexedDB !== 'undefined';
      } catch {
        return false;
      }
    })(),
  };

  console.log('Storage APIs Support:', results);
  return results;
}

/**
 * Test touch and pointer events
 */
export function testTouchAPIs() {
  const results = {
    touch_events: 'ontouchstart' in window,
    pointer_events: 'PointerEvent' in window,
    mouse_events: 'MouseEvent' in window,
    touch_list: 'TouchList' in window,
    touch_event: 'TouchEvent' in window,
  };

  console.log('Touch APIs Support:', results);
  return results;
}

/**
 * Test performance APIs
 */
export function testPerformanceAPIs() {
  const results = {
    performance: typeof performance !== 'undefined',
    performance_now: typeof performance?.now === 'function',
    performance_mark: typeof performance?.mark === 'function',
    performance_measure: typeof performance?.measure === 'function',
    performance_observer: typeof PerformanceObserver !== 'undefined',
    navigation_timing: typeof performance?.timing !== 'undefined',
    resource_timing: typeof performance?.getEntriesByType === 'function',
  };

  console.log('Performance APIs Support:', results);
  return results;
}

/**
 * Test browser information
 */
export function getBrowserInfo() {
  const ua = navigator.userAgent;
  
  let browser = 'Unknown';
  let version = 'Unknown';
  let os = 'Unknown';

  // Detect browser
  if (ua.indexOf('Chrome') > -1 && ua.indexOf('Chromium') === -1) {
    browser = 'Chrome';
    version = ua.match(/Chrome\/(\d+)/)?.[1] || 'Unknown';
  } else if (ua.indexOf('Safari') > -1 && ua.indexOf('Chrome') === -1) {
    browser = 'Safari';
    version = ua.match(/Version\/(\d+)/)?.[1] || 'Unknown';
  } else if (ua.indexOf('Firefox') > -1) {
    browser = 'Firefox';
    version = ua.match(/Firefox\/(\d+)/)?.[1] || 'Unknown';
  } else if (ua.indexOf('Edg') > -1) {
    browser = 'Edge';
    version = ua.match(/Edg\/(\d+)/)?.[1] || 'Unknown';
  } else if (ua.indexOf('Chromium') > -1) {
    browser = 'Chromium';
    version = ua.match(/Chromium\/(\d+)/)?.[1] || 'Unknown';
  }

  // Detect OS
  if (ua.indexOf('Windows') > -1) {
    os = 'Windows';
  } else if (ua.indexOf('Mac') > -1) {
    os = 'macOS';
  } else if (ua.indexOf('Linux') > -1) {
    os = 'Linux';
  } else if (ua.indexOf('iPhone') > -1 || ua.indexOf('iPad') > -1) {
    os = 'iOS';
  } else if (ua.indexOf('Android') > -1) {
    os = 'Android';
  }

  const info = {
    browser,
    version,
    os,
    userAgent: ua,
    language: navigator.language,
    platform: navigator.platform,
    hardwareConcurrency: navigator.hardwareConcurrency,
    deviceMemory: navigator.deviceMemory,
    maxTouchPoints: navigator.maxTouchPoints,
  };

  console.log('Browser Info:', info);
  return info;
}

/**
 * Run all compatibility tests
 */
export function runAllCompatibilityTests() {
  console.log('=== Running Browser Compatibility Tests ===');
  
  const results = {
    browserInfo: getBrowserInfo(),
    browserAPIs: testBrowserAPIs(),
    es6Features: testES6Features(),
    cssFeatures: testCSSFeatures(),
    domAPIs: testDOMAPIs(),
    networkAPIs: testNetworkAPIs(),
    storageAPIs: testStorageAPIs(),
    touchAPIs: testTouchAPIs(),
    performanceAPIs: testPerformanceAPIs(),
  };

  // Calculate compatibility score
  const allTests = Object.values(results).slice(1); // Exclude browserInfo
  const totalTests = allTests.reduce((sum, test) => sum + Object.keys(test).length, 0);
  const passedTests = allTests.reduce((sum, test) => {
    return sum + Object.values(test).filter(v => v === true).length;
  }, 0);
  const compatibilityScore = Math.round((passedTests / totalTests) * 100);

  results.compatibilityScore = compatibilityScore;

  console.log(`=== Compatibility Score: ${compatibilityScore}% ===`);
  console.log('Full Results:', results);

  return results;
}

/**
 * Check if browser meets minimum requirements
 */
export function checkMinimumRequirements() {
  const required = {
    fetch: typeof fetch !== 'undefined',
    websocket: typeof WebSocket !== 'undefined',
    localStorage: typeof localStorage !== 'undefined',
    es6_classes: (() => {
      try {
        eval('class Test {}');
        return true;
      } catch {
        return false;
      }
    })(),
    promises: typeof Promise !== 'undefined',
    flexbox: (() => {
      const div = document.createElement('div');
      div.style.display = 'flex';
      return div.style.display === 'flex';
    })(),
  };

  const allMet = Object.values(required).every(v => v === true);

  console.log('Minimum Requirements:', required);
  console.log('All Requirements Met:', allMet);

  if (!allMet) {
    console.warn('Browser does not meet minimum requirements for this application');
  }

  return { required, allMet };
}

/**
 * Log performance metrics
 */
export function logPerformanceMetrics() {
  if (typeof performance === 'undefined') {
    console.warn('Performance API not available');
    return;
  }

  const metrics = {
    navigationStart: performance.timing.navigationStart,
    domContentLoaded: performance.timing.domContentLoadedEventEnd - performance.timing.navigationStart,
    loadComplete: performance.timing.loadEventEnd - performance.timing.navigationStart,
    domInteractive: performance.timing.domInteractive - performance.timing.navigationStart,
    firstPaint: performance.timing.responseEnd - performance.timing.navigationStart,
  };

  console.log('Performance Metrics:', metrics);
  return metrics;
}

// Export all test functions
export default {
  testBrowserAPIs,
  testES6Features,
  testCSSFeatures,
  testDOMAPIs,
  testNetworkAPIs,
  testStorageAPIs,
  testTouchAPIs,
  testPerformanceAPIs,
  getBrowserInfo,
  runAllCompatibilityTests,
  checkMinimumRequirements,
  logPerformanceMetrics,
};
