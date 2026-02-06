/**
 * Theme Switching Functionality
 * Handles dark mode and light mode toggle with localStorage persistence
 */

class ThemeManager {
    constructor() {
        this.storageKey = 'linkup-theme';
        this.darkClass = 'dark';
        this.themeToggle = document.getElementById('theme-toggle');
        this.sunIcon = document.getElementById('sun-icon');
        this.moonIcon = document.getElementById('moon-icon');
        
        this.init();
    }

    init() {
        // Load saved theme or default to light
        const savedTheme = this.getSavedTheme();
        this.setTheme(savedTheme);
        
        // Add event listener to toggle button
        if (this.themeToggle) {
            this.themeToggle.addEventListener('click', () => this.toggleTheme());
        }
        
        // Listen for system theme changes
        if (window.matchMedia) {
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
                if (!this.getSavedTheme()) {
                    // Only auto-switch if user hasn't manually set a preference
                    this.setTheme(e.matches ? 'dark' : 'light');
                }
            });
        }
    }

    getSavedTheme() {
        try {
            return localStorage.getItem(this.storageKey);
        } catch (e) {
            console.warn('Unable to access localStorage:', e);
            return null;
        }
    }

    saveTheme(theme) {
        try {
            localStorage.setItem(this.storageKey, theme);
        } catch (e) {
            console.warn('Unable to save theme to localStorage:', e);
        }
    }

    setTheme(theme) {
        const html = document.documentElement;
        const isDark = theme === 'dark';
        
        // Set data-theme attribute for CSS variables
        html.setAttribute('data-theme', theme);
        
        // Toggle dark class for Tailwind CSS
        if (isDark) {
            html.classList.add(this.darkClass);
        } else {
            html.classList.remove(this.darkClass);
        }
        
        // Update icons
        this.updateIcons(isDark);
        
        // Update button title
        if (this.themeToggle) {
            this.themeToggle.setAttribute('title', isDark ? 'Switch to light mode' : 'Switch to dark mode');
            this.themeToggle.setAttribute('aria-label', isDark ? 'Switch to light mode' : 'Switch to dark mode');
        }
        
        // Save preference
        this.saveTheme(theme);
        
        // Dispatch custom event for other components
        window.dispatchEvent(new CustomEvent('themeChanged', { 
            detail: { theme, isDark } 
        }));
    }

    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        this.setTheme(newTheme);
    }

    updateIcons(isDark) {
        if (this.sunIcon && this.moonIcon) {
            if (isDark) {
                this.sunIcon.classList.remove('hidden');
                this.moonIcon.classList.add('hidden');
            } else {
                this.sunIcon.classList.add('hidden');
                this.moonIcon.classList.remove('hidden');
            }
        }
    }

    // Get current theme
    getCurrentTheme() {
        return document.documentElement.getAttribute('data-theme') || 'light';
    }

    // Check if dark mode is active
    isDarkMode() {
        return this.getCurrentTheme() === 'dark';
    }

    // Reset to system preference
    resetToSystemPreference() {
        const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
        this.setTheme(prefersDark ? 'dark' : 'light');
        localStorage.removeItem(this.storageKey);
    }
}

// Initialize theme manager when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.themeManager = new ThemeManager();
});

// Also initialize immediately if DOM is already loaded
if (document.readyState === 'loading') {
    // DOM is still loading
    document.addEventListener('DOMContentLoaded', () => {
        window.themeManager = new ThemeManager();
    });
} else {
    // DOM is already loaded
    window.themeManager = new ThemeManager();
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ThemeManager;
}
