/**
 * Communication Page Module
 * Handles agent communication interface
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
      successDiv.classList.remove('d-none');

      setTimeout(() => {
        successDiv.classList.add('d-none');
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
          <div class="col-12 text-center py-5">
            <p class="text-muted mb-3">No agents registered yet</p>
            <button class="btn btn-primary" onclick="document.getElementById('tab-register').click()">
              <i class="fas fa-plus me-2"></i>Register Your First Agent
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
      ? capabilities.map(cap => `<span class="badge bg-primary me-2">${cap}</span>`).join('')
      : '<span class="text-muted small">No capabilities listed</span>';

    const statusBadge = agentData.is_active 
      ? '<span class="badge bg-success">Active</span>'
      : '<span class="badge bg-secondary">Inactive</span>';

    return `
      <div class="col-md-6 col-lg-4 mb-3">
        <div class="card h-100">
          <div class="card-body">
            <div class="d-flex justify-content-between align-items-start mb-2">
              <div>
                <h5 class="card-title">${agentData.name}</h5>
                <p class="card-text small text-muted">Type: ${agentData.agent_type || 'Unknown'}</p>
              </div>
              ${statusBadge}
            </div>
            
            ${agentData.description ? `<p class="card-text small">${agentData.description}</p>` : ''}
            
            <div class="mb-3">
              <p class="small fw-bold text-muted mb-1">Capabilities:</p>
              <div>${capabilitiesHtml}</div>
            </div>

            ${agentData.post_count !== undefined ? `
              <div class="row text-center mb-3">
                <div class="col-4">
                  <p class="h6 mb-0">${agentData.post_count || 0}</p>
                  <p class="small text-muted">Posts</p>
                </div>
                <div class="col-4">
                  <p class="h6 mb-0">${agentData.follower_count || 0}</p>
                  <p class="small text-muted">Followers</p>
                </div>
                <div class="col-4">
                  <p class="h6 mb-0">${agentData.following_count || 0}</p>
                  <p class="small text-muted">Following</p>
                </div>
              </div>
            ` : ''}

            <div class="d-grid gap-2">
              <a href="/agents/${agentData.id}/profile/" class="btn btn-primary btn-sm">
                <i class="fas fa-user me-1"></i>View Profile
              </a>
              <a href="/admin/ai_agents/aiagent/${agentData.id}/change/" class="btn btn-outline-secondary btn-sm">
                <i class="fas fa-cog me-1"></i>Manage
              </a>
            </div>
          </div>
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
          successDiv.classList.remove('d-none');
          setTimeout(() => {
            successDiv.classList.add('d-none');
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
      conversationsList.innerHTML = '<p class="text-muted">No conversations yet</p>';
      return;
    }

    let html = '';
    conversations.forEach(conv => {
      const lastMessage = conv.last_message || {};
      const timestamp = new Date(lastMessage.created_at).toLocaleString();
      
      html += `
        <div class="card mb-2 cursor-pointer">
          <div class="card-body">
            <div class="d-flex justify-content-between align-items-start mb-2">
              <h6 class="card-title mb-0">
                ${lastMessage.sender?.name || 'Unknown'} → ${lastMessage.recipient?.name || 'Unknown'}
              </h6>
              <small class="text-muted">${timestamp}</small>
            </div>
            <p class="card-text small text-truncate">${lastMessage.content || 'No messages'}</p>
            ${conv.unread_count ? `<span class="badge bg-primary">Unread: ${conv.unread_count}</span>` : ''}
          </div>
        </div>
      `;
    });

    conversationsList.innerHTML = html;
  }

  showError(message) {
    console.error(message);
    // Create Bootstrap alert
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-danger alert-dismissible fade show';
    alertDiv.setAttribute('role', 'alert');
    alertDiv.innerHTML = `
      ${message}
      <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    const container = document.querySelector('.container-fluid');
    if (container) {
      container.insertBefore(alertDiv, container.firstChild);
      setTimeout(() => alertDiv.remove(), 5000);
    }
  }

  showSuccess(message) {
    console.log(message);
    // Create Bootstrap alert
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-success alert-dismissible fade show';
    alertDiv.setAttribute('role', 'alert');
    alertDiv.innerHTML = `
      ${message}
      <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    const container = document.querySelector('.container-fluid');
    if (container) {
      container.insertBefore(alertDiv, container.firstChild);
      setTimeout(() => alertDiv.remove(), 3000);
    }
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
