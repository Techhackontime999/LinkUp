/**
 * Admin AI Model Management JavaScript
 * Handles client-side interactions for the admin interface
 */

// CSRF Token Helper
function getCookie(name) {
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

const csrftoken = getCookie('csrftoken');

// Confirmation Dialog Helper
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// Show Loading State
function showLoading(element) {
    element.classList.add('loading');
    element.disabled = true;
}

// Hide Loading State
function hideLoading(element) {
    element.classList.remove('loading');
    element.disabled = false;
}

// Display Message
function displayMessage(message, type = 'info') {
    const messagesContainer = document.querySelector('.messages-container');
    if (!messagesContainer) {
        console.warn('Messages container not found');
        return;
    }

    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} p-4 mb-4 rounded-lg`;
    
    const colorClasses = {
        'error': 'bg-red-50 border border-red-200 text-red-800 dark:bg-red-900/20 dark:border-red-800 dark:text-red-400',
        'success': 'bg-green-50 border border-green-200 text-green-800 dark:bg-green-900/20 dark:border-green-800 dark:text-green-400',
        'warning': 'bg-yellow-50 border border-yellow-200 text-yellow-800 dark:bg-yellow-900/20 dark:border-yellow-800 dark:text-yellow-400',
        'info': 'bg-blue-50 border border-blue-200 text-blue-800 dark:bg-blue-900/20 dark:border-blue-800 dark:text-blue-400'
    };
    
    alertDiv.className += ' ' + (colorClasses[type] || colorClasses['info']);
    alertDiv.innerHTML = `
        <div class="flex items-center">
            <svg class="w-5 h-5 mr-3" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/>
            </svg>
            <span>${message}</span>
        </div>
    `;
    
    messagesContainer.appendChild(alertDiv);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        alertDiv.style.opacity = '0';
        setTimeout(() => alertDiv.remove(), 300);
    }, 5000);
}

// Form Validation
function validateForm(formElement) {
    const requiredFields = formElement.querySelectorAll('[required]');
    let isValid = true;
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            isValid = false;
            field.setAttribute('aria-invalid', 'true');
            field.classList.add('border-red-500');
            
            // Show error message
            const errorId = field.id + '-error';
            let errorElement = document.getElementById(errorId);
            if (!errorElement) {
                errorElement = document.createElement('p');
                errorElement.id = errorId;
                errorElement.className = 'error-message mt-1 text-sm text-red-600 dark:text-red-400';
                errorElement.setAttribute('role', 'alert');
                errorElement.textContent = 'This field is required';
                field.parentNode.appendChild(errorElement);
            }
        } else {
            field.removeAttribute('aria-invalid');
            field.classList.remove('border-red-500');
            
            // Remove error message
            const errorId = field.id + '-error';
            const errorElement = document.getElementById(errorId);
            if (errorElement) {
                errorElement.remove();
            }
        }
    });
    
    return isValid;
}

// Client-side Form Validation
document.addEventListener('DOMContentLoaded', function() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!validateForm(form)) {
                e.preventDefault();
                displayMessage('Please fill in all required fields', 'error');
                
                // Focus on first invalid field
                const firstInvalid = form.querySelector('[aria-invalid="true"]');
                if (firstInvalid) {
                    firstInvalid.focus();
                }
            }
        });
        
        // Real-time validation
        const inputs = form.querySelectorAll('input, textarea, select');
        inputs.forEach(input => {
            input.addEventListener('blur', function() {
                if (this.hasAttribute('required') && !this.value.trim()) {
                    this.setAttribute('aria-invalid', 'true');
                    this.classList.add('border-red-500');
                } else {
                    this.removeAttribute('aria-invalid');
                    this.classList.remove('border-red-500');
                }
            });
        });
    });
});

// Dynamic Form Field Visibility (Model Type-Specific)
document.addEventListener('DOMContentLoaded', function() {
    const providerSelect = document.getElementById('provider');
    if (!providerSelect) return;
    
    const typeSpecificFields = {
        'openai': document.getElementById('openai-fields'),
        'anthropic': document.getElementById('anthropic-fields'),
        'google': document.getElementById('google-fields'),
        'custom': document.getElementById('custom-fields')
    };
    
    function updateVisibleFields() {
        // Hide all type-specific fields
        Object.values(typeSpecificFields).forEach(el => {
            if (el) el.style.display = 'none';
        });
        
        // Show selected type fields
        const selectedType = providerSelect.value.toLowerCase();
        if (typeSpecificFields[selectedType]) {
            typeSpecificFields[selectedType].style.display = 'block';
        }
    }
    
    providerSelect.addEventListener('change', updateVisibleFields);
    updateVisibleFields(); // Initialize on page load
});

// Bulk Actions
function getSelectedModelIds() {
    const checkboxes = document.querySelectorAll('.model-checkbox:checked');
    return Array.from(checkboxes).map(cb => cb.value);
}

async function performBulkAction(action, modelIds) {
    if (modelIds.length === 0) {
        displayMessage('No models selected', 'warning');
        return;
    }
    
    try {
        const response = await fetch(`/api/admin/ai-models/bulk/${action}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            },
            body: JSON.stringify({ model_ids: modelIds })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            displayMessage(data.message || `Successfully ${action}ed ${modelIds.length} model(s)`, 'success');
            setTimeout(() => window.location.reload(), 1500);
        } else {
            displayMessage(data.error || `Failed to ${action} models`, 'error');
        }
    } catch (error) {
        console.error('Bulk action error:', error);
        displayMessage('An error occurred. Please try again.', 'error');
    }
}

window.bulkActivate = function() {
    const selectedIds = getSelectedModelIds();
    confirmAction(
        `Activate ${selectedIds.length} model(s)?`,
        () => performBulkAction('activate', selectedIds)
    );
};

window.bulkSuspend = function() {
    const selectedIds = getSelectedModelIds();
    confirmAction(
        `Suspend ${selectedIds.length} model(s)?`,
        () => performBulkAction('suspend', selectedIds)
    );
};

window.bulkDelete = function() {
    const selectedIds = getSelectedModelIds();
    confirmAction(
        `Delete ${selectedIds.length} model(s)? This action cannot be undone.`,
        () => performBulkAction('delete', selectedIds)
    );
};

// AJAX Status Toggle (Optional Enhancement)
async function toggleStatusAjax(agentId, suspend) {
    const action = suspend ? 'suspend' : 'activate';
    
    try {
        const response = await fetch(`/api/admin/ai-models/${agentId}/toggle-status/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            },
            body: JSON.stringify({ suspend: suspend })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            displayMessage(`Model ${action}ed successfully`, 'success');
            // Update UI without page reload
            updateModelStatusUI(agentId, suspend);
        } else {
            displayMessage(data.error || `Failed to ${action} model`, 'error');
        }
    } catch (error) {
        console.error('Status toggle error:', error);
        displayMessage('An error occurred. Please try again.', 'error');
    }
}

function updateModelStatusUI(agentId, isSuspended) {
    // Find the model row
    const row = document.querySelector(`input[value="${agentId}"]`)?.closest('tr');
    if (!row) return;
    
    // Update status badge
    const statusCell = row.querySelector('td:nth-child(5)');
    if (statusCell) {
        statusCell.innerHTML = isSuspended
            ? '<span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400">Suspended</span>'
            : '<span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">Active</span>';
    }
    
    // Update action button
    const actionCell = row.querySelector('td:last-child');
    const toggleButton = actionCell?.querySelector('button[onclick*="toggleStatus"]');
    if (toggleButton) {
        toggleButton.textContent = isSuspended ? 'Activate' : 'Suspend';
        toggleButton.className = isSuspended
            ? 'text-green-600 hover:text-green-900 dark:text-green-400 dark:hover:text-green-300'
            : 'text-yellow-600 hover:text-yellow-900 dark:text-yellow-400 dark:hover:text-yellow-300';
    }
}

// Keyboard Shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + K: Focus search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.getElementById('search');
        if (searchInput) {
            searchInput.focus();
            searchInput.select();
        }
    }
    
    // Escape: Clear selection
    if (e.key === 'Escape') {
        const selectAll = document.getElementById('select-all');
        if (selectAll && selectAll.checked) {
            selectAll.checked = false;
            selectAll.dispatchEvent(new Event('change'));
        }
    }
});

// Accessibility: Announce dynamic changes
function announceToScreenReader(message) {
    const announcer = document.getElementById('accessibility-announcements');
    if (announcer) {
        announcer.textContent = message;
        setTimeout(() => {
            announcer.textContent = '';
        }, 1000);
    }
}

// Copy to Clipboard Helper
function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => {
            displayMessage('Copied to clipboard', 'success');
        }).catch(err => {
            console.error('Failed to copy:', err);
            displayMessage('Failed to copy to clipboard', 'error');
        });
    } else {
        // Fallback for older browsers
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        try {
            document.execCommand('copy');
            displayMessage('Copied to clipboard', 'success');
        } catch (err) {
            console.error('Failed to copy:', err);
            displayMessage('Failed to copy to clipboard', 'error');
        }
        document.body.removeChild(textarea);
    }
}

// Add copy buttons to API keys
document.addEventListener('DOMContentLoaded', function() {
    const apiKeyCodes = document.querySelectorAll('code');
    apiKeyCodes.forEach(code => {
        if (code.textContent.includes('••••')) {
            const copyButton = document.createElement('button');
            copyButton.type = 'button';
            copyButton.className = 'ml-2 text-purple-600 hover:text-purple-800 text-xs';
            copyButton.textContent = 'Copy';
            copyButton.setAttribute('aria-label', 'Copy API key prefix');
            copyButton.addEventListener('click', () => {
                copyToClipboard(code.textContent);
            });
            code.parentNode.insertBefore(copyButton, code.nextSibling);
        }
    });
});

// Auto-save form data to localStorage (draft feature)
function enableAutoSave(formId) {
    const form = document.getElementById(formId);
    if (!form) return;
    
    const storageKey = `admin_form_draft_${formId}`;
    
    // Load saved data
    const savedData = localStorage.getItem(storageKey);
    if (savedData) {
        try {
            const data = JSON.parse(savedData);
            Object.keys(data).forEach(key => {
                const field = form.elements[key];
                if (field) {
                    if (field.type === 'checkbox') {
                        field.checked = data[key];
                    } else {
                        field.value = data[key];
                    }
                }
            });
            displayMessage('Draft restored', 'info');
        } catch (e) {
            console.error('Failed to restore draft:', e);
        }
    }
    
    // Save on input
    form.addEventListener('input', function() {
        const formData = new FormData(form);
        const data = {};
        for (let [key, value] of formData.entries()) {
            data[key] = value;
        }
        localStorage.setItem(storageKey, JSON.stringify(data));
    });
    
    // Clear on submit
    form.addEventListener('submit', function() {
        localStorage.removeItem(storageKey);
    });
}

// Initialize auto-save for add model form
document.addEventListener('DOMContentLoaded', function() {
    enableAutoSave('add-model-form');
});

// Toggle Status Function (Fixed to use POST)
window.toggleStatus = async function(agentId, suspend) {
    const action = suspend ? 'suspend' : 'activate';
    
    if (!confirm(`Are you sure you want to ${action} this model?`)) {
        return;
    }
    
    try {
        // Create a form and submit it
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/api/admin/ai-models/${agentId}/toggle-status/`;
        
        // Add CSRF token
        const csrfInput = document.createElement('input');
        csrfInput.type = 'hidden';
        csrfInput.name = 'csrfmiddlewaretoken';
        csrfInput.value = csrftoken;
        form.appendChild(csrfInput);
        
        document.body.appendChild(form);
        form.submit();
    } catch (error) {
        console.error('Toggle status error:', error);
        displayMessage('An error occurred. Please try again.', 'error');
    }
};

// Delete Model Function (Fixed to use POST)
window.deleteModel = async function(agentId, agentName) {
    if (!confirm(`Are you sure you want to delete "${agentName}"? This will deactivate the model.`)) {
        return;
    }
    
    try {
        // Create a form and submit it
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/api/admin/ai-models/${agentId}/delete/`;
        
        // Add CSRF token
        const csrfInput = document.createElement('input');
        csrfInput.type = 'hidden';
        csrfInput.name = 'csrfmiddlewaretoken';
        csrfInput.value = csrftoken;
        form.appendChild(csrfInput);
        
        document.body.appendChild(form);
        form.submit();
    } catch (error) {
        console.error('Delete model error:', error);
        displayMessage('An error occurred. Please try again.', 'error');
    }
};

console.log('Admin AI Model Management JavaScript loaded');
