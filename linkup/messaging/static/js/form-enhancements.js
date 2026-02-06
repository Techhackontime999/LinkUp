// Form Enhancements JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Enhanced form validation
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!form.checkValidity()) {
                e.preventDefault();
                showFormErrors(form);
            }
        });
        
        // Real-time validation
        const inputs = form.querySelectorAll('input, textarea, select');
        inputs.forEach(input => {
            input.addEventListener('blur', function() {
                validateField(input);
            });
            
            input.addEventListener('input', function() {
                clearFieldError(input);
            });
        });
    });
    
    function validateField(field) {
        if (field.validity.valid) {
            field.classList.remove('border-red-500');
            field.classList.add('border-green-500');
        } else {
            field.classList.remove('border-green-500');
            field.classList.add('border-red-500');
        }
    }
    
    function clearFieldError(field) {
        field.classList.remove('border-red-500', 'border-green-500');
    }
    
    function showFormErrors(form) {
        const firstInvalid = form.querySelector(':invalid');
        if (firstInvalid) {
            firstInvalid.focus();
            firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }
});

// Auto-save functionality
const autoSaveForms = document.querySelectorAll('[data-auto-save]');
autoSaveForms.forEach(form => {
    let autoSaveTimer;
    const inputs = form.querySelectorAll('input, textarea');
    
    inputs.forEach(input => {
        input.addEventListener('input', function() {
            clearTimeout(autoSaveTimer);
            autoSaveTimer = setTimeout(() => {
                saveFormData(form);
            }, 2000);
        });
    });
});

function saveFormData(form) {
    const formData = new FormData(form);
    const saveUrl = form.dataset.autoSave;
    
    if (saveUrl) {
        fetch(saveUrl, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCSRFToken()
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showAutoSaveIndicator(true);
            }
        })
        .catch(error => {
            console.error('Auto-save failed:', error);
        });
    }
}

function getCSRFToken() {
    const token = document.querySelector('[name=csrfmiddlewaretoken]');
    return token ? token.value : '';
}

function showAutoSaveIndicator(success) {
    const indicator = document.createElement('div');
    indicator.className = success ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800';
    indicator.textContent = success ? 'Auto-saved' : 'Auto-save failed';
    indicator.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 8px 16px;
        border-radius: 4px;
        z-index: 1000;
        font-size: 14px;
        transition: opacity 0.3s;
    `;
    
    document.body.appendChild(indicator);
    
    setTimeout(() => {
        indicator.style.opacity = '0';
        setTimeout(() => {
            document.body.removeChild(indicator);
        }, 300);
    }, 2000);
}
