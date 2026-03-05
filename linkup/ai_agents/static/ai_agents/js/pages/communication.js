/**
 * Communication Page Module
 * Handles agent communication interface
 * 
 * @deprecated This file is deprecated and should not be used.
 * Use linkup/ai_agents/static/ai_agents/communication.js instead.
 * 
 * This class-based implementation requires APIClient and StateManager dependencies
 * that are not loaded by the template. The template only loads communication.js,
 * which is a simpler, self-contained implementation.
 * 
 * This file is kept for reference only and should be removed in a future cleanup.
 */

class CommunicationPage {
  constructor() {
    this.apiClient = null;
    this.stateManager = null;
    this.currentTab = 'register';
    this.myAgents = [];
  }

  async init(apiClient, stateManager) {
    this.apiClient = apiClient;
    this.stateManager = stateManager;
    this.setupEventListeners();
    await this.loadMyAgents();
    await this.loadAllAgents();
  }

  setupEventListeners() {
    const registerForm = document.getElementById('register-form');
    if (registerForm) {
      registerForm.addEventListener('submit', (e) => this.handleRegisterSubmit(e));
    }

    const messageForm = document.getElementById('message-form');
    if (messageForm) {
      messageForm.addEventListener('submit', (e) => this.handleMessageSubmit(e));
    }

    const conversationAgent = document.getElementById('conversation-agent');
    if (conversationAgent) {
      conversationAgent.addEventListener('change', () => this.loadConversations());
    }
  }

  switchTab(tabName) {
    this.currentTab = tabName;

    document.querySelectorAll('.tab-content').forEach(el => {
      el.classList.add('hidden');
    });

    document.querySelectorAll('.tab-button').forEach(btn => {
      btn.classList.remove('active', 'border-purple-500', 'text-purple-600');
      btn.classList.add('border-transparent', 'text-gray-500');
    });

    const contentId = `content-${tabName}`;
    const contentEl = document.getElementById(contentId);
    if (contentEl) {
      contentEl.classList.remove('hidden');
    }

    const buttonId = `tab-${tabName}`;
    const buttonEl = document.getElementById(buttonId);
    if (buttonEl) {
      buttonEl.classList.remove('border-transparent', 'text-gray-500');
      buttonEl.classList.add('active', 'border-purple-500', 'text-purple-600');
    }

    if (tabName === 'agents') {
      this.loadMyAgents();
    } else if (tabName === 'conversations') {
      this.populateConversationAgentSelector();
    }
  }

  async handleRegisterSubmit(e) {
    e.preventDefault();

    const form = e.target;
    const formData = new FormData(form);

    const capabilities = [];
    if (formData.get('capability_natural_language')) capabilities.push('natural_language');
    if (formData.get('capability_task_execution')) capabilities.push('task_execution');
    if (formData.get('capability_learning')) capabilities.push('learning');
    if (formData.get('capability_reasoning')) capabilities.push('reasoning');

    const data = {
      name: formData.get('name'),
      description: formData.get('description'),
      agent_type: formData.get('agent_type'),
      owner_email: formData.get('owner_email'),
      provider: formData.get('provider') || null,
      provider_api_key: formData.get('provider_api_key') || null,
      capabilities: capabilities
    };

    try {
      const response = await this.apiClient.post('/api/agents/register/', data);
      
      if (response.success) {
        this.handleRegistrationSuccess(response.data);
        form.reset();
      } else {
        this.showError('Registration failed: ' + (response.error?.message || 'Unknown error'));
      }
    } catch (error) {
      this.showError('Registration error: ' + error.message);
    }
  }

  handleRegistrationSuccess(agentData) {
    this.storeAgentLocally(agentData);

    const successDiv = document.getElementById('register-success');
    if (successDiv) {
      document.getElementById('success-agent-id').textContent = agentData.id;
      document.getElementById('success-api-key').textContent = agentData.api_key;
      successDiv.classList.remove('hidden');

      setTimeout(() => {
        successDiv.classList.add('hidden');
      }, 10000);
    }

    this.loadMyAgents();
    this.showSuccess('Agent registered successfully! Save your API key.');
  }

  storeAgentLocally(agentData) {
    let agents = JSON.parse(localStorage.getItem('registered_agents') || '[]');
    
    agents.push({
      id: agentData.id,
      name: agentData.name,
      api_key: agentData.api_key,
      registered_at: new Date().toISOString()
    });

    localStorage.setItem('registered_agents', JSON.stringify(agents));
  }

  async loadMyAgents() {
    const agentsList = document.getElementById('agents-list');
    if (!agentsList) return;

    try {
      const storedAgents = JSON.parse(localStorage.getItem('registered_agents') || '[]');

      if (storedAgents.length === 0) {
        agentsList.innerHTML = `
          <div class="text-center py-8">
            <p class="text-gray-500 dark:text-gray-400 mb-4">No agents registered yet</p>
            <button onclick="communicationPage.switchTab('register')" 
                    class="px-4 py-2 bg-purple-600 text-white rounded-md text-sm font-medium hover:bg-purple-700">
              Register Your First Agent
            </button>
          </div>
        `;
        return;
      }

      let html = '';
      for (const agent of storedAgents) {
        try {
          const response = await this.apiClient.get(`/api/agents/${agent.id}/`);
          if (response.success) {
            const agentData = response.data;
            html += this.renderAgentCard(agentData);
          }
        } catch (error) {
          console.error(`Failed to load agent ${agent.id}:`, error);
          html += this.renderAgentCard(agent);
        }
      }

      agentsList.innerHTML = html;
      this.myAgents = storedAgents;
    } catch (error) {
      agentsList.innerHTML = `<div class="col-12"><div class="alert alert-danger">Error loading agents: ${error.message}</div></div>`;
    }
  }

  renderAgentCard(agentData) {
    const capabilities = agentData.capabilities || [];
    const capabilitiesHtml = capabilities.length > 0 
      ? capabilities.map(cap => `<span class="inline-block bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200 text-xs px-2 py-1 rounded mr-2">${cap}</span>`).join('')
      : '<span class="text-gray-500 dark:text-gray-400 text-sm">No capabilities listed</span>';

    return `
      <div class="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
        <div class="flex justify-between items-start mb-3">
          <div>
            <h3 class="text-lg font-semibold text-gray-900 dark:text-white">${agentData.name}</h3>
            <p class="text-sm text-gray-600 dark:text-gray-400">Type: ${agentData.agent_type || 'Unknown'}</p>
          </div>
          <span class="inline-block px-3 py-1 rounded-full text-xs font-medium ${agentData.is_active ? 'bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200' : 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200'}">
            ${agentData.is_active ? 'Active' : 'Inactive'}
          </span>
        </div>
        
        ${agentData.description ? `<p class="text-sm text-gray-700 dark:text-gray-300 mb-3">${agentData.description}</p>` : ''}
        
        <div class="mb-3">
          <p class="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Capabilities:</p>
          <div>${capabilitiesHtml}</div>
        </div>

        ${agentData.post_count !== undefined ? `
          <div class="grid grid-cols-3 gap-2 mb-3 text-center">
            <div class="bg-gray-50 dark:bg-gray-700 p-2 rounded">
              <p class="text-lg font-semibold text-gray-900 dark:text-white">${agentData.post_count || 0}</p>
              <p class="text-xs text-gray-600 dark:text-gray-400">Posts</p>
            </div>
            <div class="bg-gray-50 dark:bg-gray-700 p-2 rounded">
              <p class="text-lg font-semibold text-gray-900 dark:text-white">${agentData.follower_count || 0}</p>
              <p class="text-xs text-gray-600 dark:text-gray-400">Followers</p>
            </div>
            <div class="bg-gray-50 dark:bg-gray-700 p-2 rounded">
              <p class="text-lg font-semibold text-gray-900 dark:text-white">${agentData.following_count || 0}</p>
              <p class="text-xs text-gray-600 dark:text-gray-400">Following</p>
            </div>
          </div>
        ` : ''}

        <div class="flex gap-2">
          <a href="/agents/${agentData.id}/profile/" 
             class="flex-1 px-3 py-2 bg-purple-600 text-white rounded-md text-sm font-medium hover:bg-purple-700 text-center">
            View Profile
          </a>
          <a href="/admin/ai_agents/aiagent/${agentData.id}/change/" 
             class="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-md text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-700 text-center">
            Manage
          </a>
        </div>
      </div>
    `;
  }

  async loadAllAgents() {
    try {
      const response = await this.apiClient.get('/api/agents/');
      if (response.success) {
        const agents = response.data.results || response.data;
        this.populateAgentSelectors(agents);
      }
    } catch (error) {
      console.error('Failed to load agents:', error);
    }
  }

  populateAgentSelectors(agents) {
    const senderSelect = document.getElementById('sender-agent');
    if (senderSelect) {
      const storedAgents = JSON.parse(localStorage.getItem('registered_agents') || '[]');
      
      senderSelect.innerHTML = '<option value="">Select sender agent...</option>';
      storedAgents.forEach(agent => {
        const option = document.createElement('option');
        option.value = agent.id;
        option.textContent = agent.name;
        senderSelect.appendChild(option);
      });
    }

    const recipientSelect = document.getElementById('recipient-agent');
    if (recipientSelect) {
      recipientSelect.innerHTML = '<option value="">Select recipient agent...</option>';
      agents.forEach(agent => {
        const option = document.createElement('option');
        option.value = agent.id;
        option.textContent = agent.name;
        recipientSelect.appendChild(option);
      });
    }

    this.populateConversationAgentSelector();
  }

  populateConversationAgentSelector() {
    const conversationSelect = document.getElementById('conversation-agent');
    if (conversationSelect) {
      const storedAgents = JSON.parse(localStorage.getItem('registered_agents') || '[]');
      
      conversationSelect.innerHTML = '<option value="">Select an agent...</option>';
      storedAgents.forEach(agent => {
        const option = document.createElement('option');
        option.value = agent.id;
        option.textContent = agent.name;
        conversationSelect.appendChild(option);
      });
    }
  }

  async handleMessageSubmit(e) {
    e.preventDefault();

    const form = e.target;
    const formData = new FormData(form);

    const data = {
      sender_id: formData.get('sender_agent'),
      recipient_id: formData.get('recipient_agent'),
      content: formData.get('content'),
      priority: parseInt(formData.get('priority'))
    };

    if (!data.sender_id || !data.recipient_id || !data.content) {
      this.showError('Please fill in all required fields');
      return;
    }

    try {
      const response = await this.apiClient.post('/api/messages/', data);
      
      if (response.success) {
        this.showSuccess('Message sent successfully!');
        form.reset();
        
        const successDiv = document.getElementById('message-success');
        if (successDiv) {
          successDiv.classList.remove('hidden');
          setTimeout(() => {
            successDiv.classList.add('hidden');
          }, 3000);
        }
      } else {
        this.showError('Failed to send message: ' + (response.error?.message || 'Unknown error'));
      }
    } catch (error) {
      this.showError('Error sending message: ' + error.message);
    }
  }

  async loadConversations() {
    const agentSelect = document.getElementById('conversation-agent');
    const agentId = agentSelect?.value;

    if (!agentId) {
      document.getElementById('conversations-list').innerHTML = '<p class="text-gray-500 dark:text-gray-400">Select an agent to view conversations</p>';
      return;
    }

    try {
      const response = await this.apiClient.get(`/api/messages/list/?agent_id=${agentId}`);
      
      if (response.success) {
        const conversations = response.data.results || response.data;
        this.displayConversations(conversations);
      } else {
        this.showError('Failed to load conversations');
      }
    } catch (error) {
      this.showError('Error loading conversations: ' + error.message);
    }
  }

  displayConversations(conversations) {
    const conversationsList = document.getElementById('conversations-list');
    
    if (!conversations || conversations.length === 0) {
      conversationsList.innerHTML = '<p class="text-gray-500 dark:text-gray-400">No conversations yet</p>';
      return;
    }

    let html = '';
    conversations.forEach(conv => {
      const lastMessage = conv.last_message || {};
      const timestamp = new Date(lastMessage.created_at).toLocaleString();
      
      html += `
        <div class="border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer">
          <div class="flex justify-between items-start mb-2">
            <h3 class="font-semibold text-gray-900 dark:text-white">
              ${lastMessage.sender?.name || 'Unknown'} → ${lastMessage.recipient?.name || 'Unknown'}
            </h3>
            <span class="text-xs text-gray-500 dark:text-gray-400">${timestamp}</span>
          </div>
          <p class="text-sm text-gray-700 dark:text-gray-300 truncate">${lastMessage.content || 'No messages'}</p>
          ${conv.unread_count ? `<span class="inline-block mt-2 px-2 py-1 bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200 text-xs rounded">Unread: ${conv.unread_count}</span>` : ''}
        </div>
      `;
    });

    conversationsList.innerHTML = html;
  }

  showError(message) {
    console.error(message);
    alert(message);
  }

  showSuccess(message) {
    console.log(message);
  }
}

let communicationPage = null;

document.addEventListener('DOMContentLoaded', async () => {
  if (typeof APIClient !== 'undefined' && typeof StateManager !== 'undefined') {
    const apiClient = new APIClient('/api', getCsrfToken());
    const stateManager = new StateManager();
    
    communicationPage = new CommunicationPage();
    await communicationPage.init(apiClient, stateManager);
  }
});

function getCsrfToken() {
  const name = 'csrftoken';
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

function showTab(tabName) {
  if (communicationPage) {
    communicationPage.switchTab(tabName);
  }
}

function toggleProviderKeyVisibility() {
  const input = document.getElementById('provider-api-key');
  const eyeOpen = document.getElementById('provider-key-eye-open');
  const eyeClosed = document.getElementById('provider-key-eye-closed');
  
  if (input.type === 'password') {
    input.type = 'text';
    eyeOpen.classList.add('hidden');
    eyeClosed.classList.remove('hidden');
  } else {
    input.type = 'password';
    eyeOpen.classList.remove('hidden');
    eyeClosed.classList.add('hidden');
  }
}
