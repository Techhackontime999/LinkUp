// Accessibility Enhancements JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Skip links functionality
    const skipLinks = document.querySelectorAll('.skip-link');
    skipLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href').substring(1);
            const targetElement = document.getElementById(targetId);
            
            if (targetElement) {
                targetElement.focus();
                targetElement.scrollIntoView();
            }
        });
    });
    
    // Focus management
    const focusableElements = document.querySelectorAll(
        'a, button, input, textarea, select, [tabindex]:not([tabindex="-1"])'
    );
    
    // Trap focus within modals
    const modals = document.querySelectorAll('[role="dialog"], .modal');
    modals.forEach(modal => {
        modal.addEventListener('keydown', function(e) {
            if (e.key === 'Tab') {
                const focusableModalElements = modal.querySelectorAll(
                    'a, button, input, textarea, select, [tabindex]:not([tabindex="-1"])'
                );
                
                if (focusableModalElements.length > 0) {
                    if (e.shiftKey) {
                        // Shift + Tab
                        if (document.activeElement === focusableModalElements[0]) {
                            e.preventDefault();
                            focusableModalElements[focusableModalElements.length - 1].focus();
                        }
                    } else {
                        // Tab
                        if (document.activeElement === focusableModalElements[focusableModalElements.length - 1]) {
                            e.preventDefault();
                            focusableModalElements[0].focus();
                        }
                    }
                }
            }
        });
    });
    
    // Announce dynamic content changes
    const announceChange = function(message) {
        const announcement = document.createElement('div');
        announcement.setAttribute('aria-live', 'polite');
        announcement.setAttribute('aria-atomic', 'true');
        announcement.className = 'sr-only';
        announcement.textContent = message;
        
        document.body.appendChild(announcement);
        
        setTimeout(() => {
            document.body.removeChild(announcement);
        }, 1000);
    };
    
    // Enhanced form validation with accessibility
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const invalidFields = form.querySelectorAll(':invalid');
            
            if (invalidFields.length > 0) {
                e.preventDefault();
                
                // Focus first invalid field
                invalidFields[0].focus();
                invalidFields[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
                
                // Announce validation errors
                const errorCount = invalidFields.length;
                announceChange(`Form has ${errorCount} validation error${errorCount !== 1 ? 's' : ''}. Please review and correct.`);
                
                // Add error messages to screen readers
                invalidFields.forEach((field, index) => {
                    const errorId = `error-${field.name || field.id || index}`;
                    let errorElement = document.getElementById(errorId);
                    
                    if (!errorElement) {
                        errorElement = document.createElement('div');
                        errorElement.id = errorId;
                        errorElement.className = 'text-red-600 text-sm mt-1';
                        errorElement.setAttribute('role', 'alert');
                        
                        field.parentNode.insertBefore(errorElement, field.nextSibling);
                    }
                    
                    errorElement.textContent = field.validationMessage || 'This field is required';
                });
            }
        });
    });
    
    // Keyboard navigation enhancement
    document.addEventListener('keydown', function(e) {
        // Alt + S for search
        if (e.altKey && e.key === 's') {
            e.preventDefault();
            const searchInput = document.getElementById('search-input') || document.querySelector('input[type="search"]');
            if (searchInput) {
                searchInput.focus();
            }
        }
        
        // Escape to close modals
        if (e.key === 'Escape') {
            const openModals = document.querySelectorAll('.modal:not(.hidden)');
            openModals.forEach(modal => {
                modal.classList.add('hidden');
            });
        }
    });
    
    // Color contrast checker
    function checkColorContrast() {
        const elements = document.querySelectorAll('[data-check-contrast]');
        elements.forEach(element => {
            const bgColor = window.getComputedStyle(element).backgroundColor;
            const textColor = window.getComputedStyle(element).color;
            
            // Simple contrast ratio calculation
            const contrast = getContrastRatio(bgColor, textColor);
            
            if (contrast < 4.5) {
                console.warn('Low contrast detected:', element);
                element.classList.add('low-contrast-warning');
            }
        });
    }
    
    function getContrastRatio(rgb1, rgb2) {
        // Simplified contrast ratio calculation
        const l1 = getLuminance(rgb1);
        const l2 = getLuminance(rgb2);
        return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
    }
    
    function getLuminance(rgb) {
        const rgb = rgb.match(/\d+/g);
        if (rgb && rgb.length >= 3) {
            const [r, g, b] = rgb.map(val => val / 255);
            const rsRGB = r <= 0.03928 ? r / 12.92 : Math.pow((r + 0.055) / 1.055, 2.4);
            const gsRGB = g <= 0.03928 ? g / 12.92 : Math.pow((g + 0.055) / 1.055, 2.4);
            const bsRGB = b <= 0.03928 ? b / 12.92 : Math.pow((b + 0.055) / 1.055, 2.4);
            
            return 0.2126 * rsRGB + 0.7152 * gsRGB + 0.0722 * bsRGB;
        }
        return 0;
    }
    
    // Initialize contrast checking
    if (window.matchMedia('(prefers-contrast: high)').matches) {
        checkColorContrast();
    }
});
