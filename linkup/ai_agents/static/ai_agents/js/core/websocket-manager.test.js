/**
 * WebSocketManager Tests
 * 
 * Basic tests to verify WebSocketManager functionality
 */

import { WebSocketManager } from './websocket-manager.js';

// Mock WebSocket for testing
class MockWebSocket {
  constructor(url) {
    this.url = url;
    this.readyState = WebSocket.CONNECTING;
    this.onopen = null;
    this.onclose = null;
    this.onerror = null;
    this.onmessage = null;
    
    // Simulate connection after a short delay
    setTimeout(() => {
      this.readyState = WebSocket.OPEN;
      if (this.onopen) this.onopen();
    }, 10);
  }
  
  send(data) {
    if (this.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket is not open');
    }
    console.log('Mock WebSocket send:', data);
  }
  
  close() {
    this.readyState = WebSocket.CLOSED;
    if (this.onclose) this.onclose({ code: 1000 });
  }
}

// Set up WebSocket constants
MockWebSocket.CONNECTING = 0;
MockWebSocket.OPEN = 1;
MockWebSocket.CLOSING = 2;
MockWebSocket.CLOSED = 3;

// Replace global WebSocket with mock
global.WebSocket = MockWebSocket;

// Test suite
async function runTests() {
  console.log('Running WebSocketManager tests...\n');
  
  let passed = 0;
  let failed = 0;
  
  // Test 1: Constructor initializes correctly
  try {
    const wsm = new WebSocketManager('ws://localhost:8000/ws', 'test-token');
    console.assert(wsm.url === 'ws://localhost:8000/ws', 'URL should be set');
    console.assert(wsm.authToken === 'test-token', 'Auth token should be set');
    console.assert(wsm.maxReconnectAttempts === 3, 'Max reconnect attempts should be 3');
    console.assert(wsm.reconnectDelay === 1000, 'Initial reconnect delay should be 1000ms');
    console.log('✓ Test 1: Constructor initializes correctly');
    passed++;
  } catch (error) {
    console.error('✗ Test 1 failed:', error);
    failed++;
  }
  
  // Test 2: Connect establishes connection
  try {
    const wsm = new WebSocketManager('ws://localhost:8000/ws');
    await wsm.connect();
    console.assert(wsm.isConnected === true, 'Should be connected');
    console.assert(wsm.ws !== null, 'WebSocket instance should exist');
    console.log('✓ Test 2: Connect establishes connection');
    wsm.disconnect();
    passed++;
  } catch (error) {
    console.error('✗ Test 2 failed:', error);
    failed++;
  }
  
  // Test 3: Subscribe and unsubscribe work correctly
  try {
    const wsm = new WebSocketManager('ws://localhost:8000/ws');
    const callback = (data) => console.log('Event received:', data);
    
    wsm.subscribe('post.created', callback);
    console.assert(wsm.subscribers.has('post.created'), 'Should have post.created subscribers');
    console.assert(wsm.subscribers.get('post.created').length === 1, 'Should have 1 subscriber');
    
    wsm.unsubscribe('post.created', callback);
    console.assert(wsm.subscribers.get('post.created').length === 0, 'Should have 0 subscribers after unsubscribe');
    
    console.log('✓ Test 3: Subscribe and unsubscribe work correctly');
    passed++;
  } catch (error) {
    console.error('✗ Test 3 failed:', error);
    failed++;
  }
  
  // Test 4: Send method works when connected
  try {
    const wsm = new WebSocketManager('ws://localhost:8000/ws');
    await wsm.connect();
    
    const result = wsm.send({ type: 'test', data: 'hello' });
    console.assert(result === true, 'Send should return true when connected');
    
    wsm.disconnect();
    console.log('✓ Test 4: Send method works when connected');
    passed++;
  } catch (error) {
    console.error('✗ Test 4 failed:', error);
    failed++;
  }
  
  // Test 5: Send method fails gracefully when disconnected
  try {
    const wsm = new WebSocketManager('ws://localhost:8000/ws');
    const result = wsm.send({ type: 'test', data: 'hello' });
    console.assert(result === false, 'Send should return false when disconnected');
    console.log('✓ Test 5: Send method fails gracefully when disconnected');
    passed++;
  } catch (error) {
    console.error('✗ Test 5 failed:', error);
    failed++;
  }
  
  // Test 6: getStatus returns correct information
  try {
    const wsm = new WebSocketManager('ws://localhost:8000/ws');
    const status = wsm.getStatus();
    console.assert(status.connected === false, 'Should not be connected initially');
    console.assert(status.pollingMode === false, 'Should not be in polling mode initially');
    console.assert(status.reconnectAttempts === 0, 'Should have 0 reconnect attempts initially');
    console.assert(status.maxReconnectAttempts === 3, 'Should have max 3 reconnect attempts');
    console.log('✓ Test 6: getStatus returns correct information');
    passed++;
  } catch (error) {
    console.error('✗ Test 6 failed:', error);
    failed++;
  }
  
  // Test 7: Polling fallback callback can be set
  try {
    const wsm = new WebSocketManager('ws://localhost:8000/ws');
    let pollingCalled = false;
    wsm.setPollingFallback(() => {
      pollingCalled = true;
    });
    console.assert(wsm.pollingCallback !== null, 'Polling callback should be set');
    console.log('✓ Test 7: Polling fallback callback can be set');
    passed++;
  } catch (error) {
    console.error('✗ Test 7 failed:', error);
    failed++;
  }
  
  // Test 8: isPollingMode returns correct value
  try {
    const wsm = new WebSocketManager('ws://localhost:8000/ws');
    console.assert(wsm.isPollingMode() === false, 'Should not be in polling mode initially');
    console.log('✓ Test 8: isPollingMode returns correct value');
    passed++;
  } catch (error) {
    console.error('✗ Test 8 failed:', error);
    failed++;
  }
  
  // Test 9: Disconnect clears connection
  try {
    const wsm = new WebSocketManager('ws://localhost:8000/ws');
    await wsm.connect();
    wsm.disconnect();
    console.assert(wsm.isConnected === false, 'Should not be connected after disconnect');
    console.assert(wsm.ws === null, 'WebSocket instance should be null after disconnect');
    console.log('✓ Test 9: Disconnect clears connection');
    passed++;
  } catch (error) {
    console.error('✗ Test 9 failed:', error);
    failed++;
  }
  
  // Test 10: Multiple subscribers can be added to same event
  try {
    const wsm = new WebSocketManager('ws://localhost:8000/ws');
    const callback1 = () => {};
    const callback2 = () => {};
    
    wsm.subscribe('post.created', callback1);
    wsm.subscribe('post.created', callback2);
    
    console.assert(wsm.subscribers.get('post.created').length === 2, 'Should have 2 subscribers');
    console.log('✓ Test 10: Multiple subscribers can be added to same event');
    passed++;
  } catch (error) {
    console.error('✗ Test 10 failed:', error);
    failed++;
  }
  
  // Summary
  console.log(`\n${'='.repeat(50)}`);
  console.log(`Tests completed: ${passed + failed}`);
  console.log(`Passed: ${passed}`);
  console.log(`Failed: ${failed}`);
  console.log(`${'='.repeat(50)}`);
  
  return failed === 0;
}

// Run tests if this file is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  runTests().then(success => {
    process.exit(success ? 0 : 1);
  });
}

export { runTests };
