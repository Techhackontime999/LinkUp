// AI Agent Communication JavaScript

// Store registered agents
let myAgents = [];
let allAgents = [];

// Tab switching
function showTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.add('hidden');
    });
    
    // Remove active class from all buttons
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active', 'border-purple-500', 'text-purple-600');
        btn.classList.add('border-transparent', 'text-gray-500');
    });
    
    // Show selected tab
    document.getElementById(`content-${tabName}`).classList.remove('hidden');
    
    // Add active class to selected button
    const activeBtn = document.getElementById(`tab-${tabName}`);
    activeBtn.classList.add('active', 'border-purple-500', 'text-purple-600');
    activeBtn.classList.remove('border-transparent', 'text-gray-500');
    
    // Load data for specific tabs
    if (tabName === 'agents') {
        loadMyAgents();
    } else if (tabName === 'communicate') {
        loadAgentSelectors();
    } else if (tabName === 'conversations') {
        loadConversationAgents();
    }
}

// Get CSRF token
function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

// Register Agent Form
document.getElementById('register-form').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const formData = {
        name: document.getElementById('agent-name').value,
        description: document.getElementById('agent-description').value,
        agent_type: document.getElementById('agent-type').value,
        owner_email: document.getElementById('owner-email').value,
        capabilities: {
            natural_language: document.querySelector('[name="capability_natural_language"]').checked,
            task_execution: document.querySelector('[name="capability_task_execution"]').checked,
            learning: document.querySelector('[name="capability_learning"]').checked,
            reasoning: document.querySelector('[name="capability_reasoning"]').checked
        }
    };
    
    try {
        const response = await fetch('/api/agents/register/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify(formData)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Show success message
            document.getElementById('success-agent-id').textContent = data.agent_id;
            document.getElementById('success-api-key').textContent = data.api_key;
            document.getElementById('register-success').classList.remove('hidden');
            
            // Store agent info in localStorage
            const agentInfo = {
                id: data.agent_id,
                name: formData.name,
                api_key: data.api_key
            };
            
            let storedAgents = JSON.parse(localStorage.getItem('myAgents') || '[]');
            storedAgents.push(agentInfo);
            localStorage.setItem('myAgents', JSON.stringify(storedAgents));
            
            // Reset form
            document.getElementById('register-form').reset();
            
            // Hide success message after 10 seconds
            setTimeout(() => {
                document.getElementById('register-success').classList.add('hidden');
            }, 10000);
        } else {
            alert('Error: ' + (data.error || 'Failed to register agent'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Failed to register agent. Please try again.');
    }
});

// Load My Agents
async function loadMyAgents() {
    const agentsList = document.getElementById('agents-list');
    const storedAgents = JSON.parse(localStorage.getItem('myAgents') || '[]');
    
    if (storedAgents.length === 0) {
        agentsList.innerHTML = '<p class="text-gray-500 dark:text-gray-400">No agents registered yet. Go to the Register Agent tab to create one.</p>';
        return;
    }
    
    agentsList.innerHTML = '<p class="text-gray-500 dark:text-gray-400">Loading agent details...</p>';
    
    let html = '';
    for (const agent of storedAgents) {
        try {
            // Authenticate to get access token
            const authResponse = await fetch('/api/agents/authenticate/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify({
                    agent_id: agent.id,
                    api_key: agent.api_key
                })
            });
            
            if (!authResponse.ok) continue;
            
            const authData = await authResponse.json();
            const token = authData.access_token;
            
            // Get agent profile
            const profileResponse = await fetch(`/api/agents/${agent.id}/`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (!profileResponse.ok) continue;
            
            const profile = await profileResponse.json();
            
            html += `
                <div class="agent-card border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                    <div class="flex justify-between items-start">
                        <div class="flex-1">
                            <h3 class="text-lg font-semibold text-gray-900 dark:text-white">${profile.name}</h3>
                            <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">${profile.description || 'No description'}</p>
                            <div class="mt-2">
                                <span class="status-badge ${profile.is_active ? 'status-active' : 'status-inactive'}">
                                    ${profile.is_active ? 'Active' : 'Inactive'}
                                </span>
                                <span class="ml-2 text-xs text-gray-500 dark:text-gray-400">Type: ${profile.agent_type}</span>
                            </div>
                            <div class="mt-2">
                                ${Object.entries(profile.capabilities).map(([key, value]) => 
                                    value ? `<span class="capability-tag">${key.replace('_', ' ')}</span>` : ''
                                ).join('')}
                            </div>
                            <div class="mt-2 text-xs text-gray-500 dark:text-gray-400">
                                <p>ID: <code class="bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">${profile.id}</code></p>
                                <p class="mt-1">Total Interactions: ${profile.total_interactions || 0}</p>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        } catch (error) {
            console.error('Error loading agent:', error);
        }
    }
    
    agentsList.innerHTML = html || '<p class="text-gray-500 dark:text-gray-400">Failed to load agent details.</p>';
}

// Load Agent Selectors for messaging
async function loadAgentSelectors() {
    const storedAgents = JSON.parse(localStorage.getItem('myAgents') || '[]');
    const senderSelect = document.getElementById('sender-agent');
    const recipientSelect = document.getElementById('recipient-agent');
    
    // Clear existing options
    senderSelect.innerHTML = '<option value="">Select sender agent...</option>';
    recipientSelect.innerHTML = '<option value="">Select recipient agent...</option>';
    
    // Add my agents to sender
    for (const agent of storedAgents) {
        const option = document.createElement('option');
        option.value = JSON.stringify({id: agent.id, api_key: agent.api_key});
        option.textContent = agent.name;
        senderSelect.appendChild(option);
    }
    
    // Load all agents for recipient
    if (storedAgents.length > 0) {
        try {
            const firstAgent = storedAgents[0];
            const authResponse = await fetch('/api/agents/authenticate/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify({
                    agent_id: firstAgent.id,
                    api_key: firstAgent.api_key
                })
            });
            
            if (authResponse.ok) {
                const authData = await authResponse.json();
                const token = authData.access_token;
                
                const agentsResponse = await fetch('/api/agents/', {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });
                
                if (agentsResponse.ok) {
                    const data = await agentsResponse.json();
                    allAgents = data.results || [];
                    
                    for (const agent of allAgents) {
                        const option = document.createElement('option');
                        option.value = agent.id;
                        option.textContent = `${agent.name} (${agent.agent_type})`;
                        recipientSelect.appendChild(option);
                    }
                }
            }
        } catch (error) {
            console.error('Error loading agents:', error);
        }
    }
}

// Send Message Form
document.getElementById('message-form').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const senderData = JSON.parse(document.getElementById('sender-agent').value);
    const recipientId = document.getElementById('recipient-agent').value;
    const content = document.getElementById('message-content').value;
    const priority = parseInt(document.getElementById('message-priority').value);
    
    try {
        // Authenticate sender
        const authResponse = await fetch('/api/agents/authenticate/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({
                agent_id: senderData.id,
                api_key: senderData.api_key
            })
        });
        
        if (!authResponse.ok) {
            alert('Failed to authenticate sender agent');
            return;
        }
        
        const authData = await authResponse.json();
        const token = authData.access_token;
        
        // Send message
        const messageResponse = await fetch('/api/messages/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({
                recipient_id: recipientId,
                content: content,
                message_type: 'TEXT',
                priority: priority
            })
        });
        
        if (messageResponse.ok) {
            document.getElementById('message-success').classList.remove('hidden');
            document.getElementById('message-form').reset();
            
            setTimeout(() => {
                document.getElementById('message-success').classList.add('hidden');
            }, 3000);
        } else {
            const error = await messageResponse.json();
            alert('Error: ' + (error.error || 'Failed to send message'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Failed to send message. Please try again.');
    }
});

// Load Conversation Agents
function loadConversationAgents() {
    const storedAgents = JSON.parse(localStorage.getItem('myAgents') || '[]');
    const select = document.getElementById('conversation-agent');
    
    select.innerHTML = '<option value="">Select an agent...</option>';
    
    for (const agent of storedAgents) {
        const option = document.createElement('option');
        option.value = JSON.stringify({id: agent.id, api_key: agent.api_key, name: agent.name});
        option.textContent = agent.name;
        select.appendChild(option);
    }
}

// Load Conversations
async function loadConversations() {
    const agentData = document.getElementById('conversation-agent').value;
    if (!agentData) return;
    
    const agent = JSON.parse(agentData);
    const conversationsList = document.getElementById('conversations-list');
    
    conversationsList.innerHTML = '<p class="text-gray-500 dark:text-gray-400">Loading conversations...</p>';
    
    try {
        // Authenticate
        const authResponse = await fetch('/api/agents/authenticate/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({
                agent_id: agent.id,
                api_key: agent.api_key
            })
        });
        
        if (!authResponse.ok) {
            conversationsList.innerHTML = '<p class="text-red-500">Failed to authenticate agent</p>';
            return;
        }
        
        const authData = await authResponse.json();
        const token = authData.access_token;
        
        // Get messages
        const messagesResponse = await fetch('/api/messages/list/', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!messagesResponse.ok) {
            conversationsList.innerHTML = '<p class="text-red-500">Failed to load messages</p>';
            return;
        }
        
        const data = await messagesResponse.json();
        const messages = data.results || [];
        
        if (messages.length === 0) {
            conversationsList.innerHTML = '<p class="text-gray-500 dark:text-gray-400">No messages yet</p>';
            return;
        }
        
        let html = '<div class="space-y-3">';
        for (const message of messages) {
            const isSent = message.sender === agent.id;
            html += `
                <div class="flex ${isSent ? 'justify-end' : 'justify-start'}">
                    <div class="message-bubble ${isSent ? 'message-sent' : 'message-received'} rounded-lg p-3">
                        <p class="text-xs font-semibold mb-1">${isSent ? 'You' : message.sender_name}</p>
                        <p class="text-sm">${message.content}</p>
                        <p class="text-xs mt-1 opacity-75">${new Date(message.created_at).toLocaleString()}</p>
                    </div>
                </div>
            `;
        }
        html += '</div>';
        
        conversationsList.innerHTML = html;
    } catch (error) {
        console.error('Error:', error);
        conversationsList.innerHTML = '<p class="text-red-500">Failed to load conversations</p>';
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    showTab('register');
});
