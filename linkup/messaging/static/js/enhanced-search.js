// Enhanced Search JavaScript
document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('search-input');
    const searchForm = document.querySelector('form[role="search"]');
    
    if (!searchInput || !searchForm) return;
    
    let searchTimeout;
    let searchResults = [];
    let currentSearch = '';
    
    // Enhanced search suggestions
    searchInput.addEventListener('input', function(e) {
        const query = e.target.value.trim();
        
        if (query.length < 2) {
            hideSearchSuggestions();
            return;
        }
        
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            if (query !== currentSearch) {
                currentSearch = query;
                fetchSearchSuggestions(query);
            }
        }, 300);
    });
    
    // Search with keyboard navigation
    searchInput.addEventListener('keydown', function(e) {
        const suggestionsContainer = document.getElementById('search-suggestions');
        
        if (!suggestionsContainer) return;
        
        const items = suggestionsContainer.querySelectorAll('.suggestion-item');
        let currentIndex = -1;
        
        // Find current selected item
        items.forEach((item, index) => {
            if (item.classList.contains('selected')) {
                currentIndex = index;
            }
        });
        
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            currentIndex = Math.min(currentIndex + 1, items.length - 1);
            updateSelectedSuggestion(items, currentIndex);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            currentIndex = Math.max(currentIndex - 1, 0);
            updateSelectedSuggestion(items, currentIndex);
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (currentIndex >= 0 && items[currentIndex]) {
                items[currentIndex].click();
            } else {
                searchForm.submit();
            }
        } else if (e.key === 'Escape') {
            hideSearchSuggestions();
            searchInput.focus();
        }
    });
    
    // Click outside to close suggestions
    document.addEventListener('click', function(e) {
        const suggestionsContainer = document.getElementById('search-suggestions');
        if (suggestionsContainer && !suggestionsContainer.contains(e.target) && e.target !== searchInput) {
            hideSearchSuggestions();
        }
    });
    
    function fetchSearchSuggestions(query) {
        const searchUrl = `/search/suggestions/?q=${encodeURIComponent(query)}`;
        
        fetch(searchUrl, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            searchResults = data.suggestions || [];
            displaySearchSuggestions(searchResults);
        })
        .catch(error => {
            console.error('Search suggestions failed:', error);
        });
    }
    
    function displaySearchSuggestions(suggestions) {
        if (suggestions.length === 0) {
            hideSearchSuggestions();
            return;
        }
        
        let suggestionsContainer = document.getElementById('search-suggestions');
        if (!suggestionsContainer) {
            suggestionsContainer = document.createElement('div');
            suggestionsContainer.id = 'search-suggestions';
            suggestionsContainer.className = 'absolute top-full left-0 right-0 bg-white border border-gray-200 rounded-lg shadow-lg z-50 max-h-64 overflow-y-auto';
            suggestionsContainer.style.cssText = `
                margin-top: 4px;
                min-width: 100%;
            `;
            
            searchInput.parentNode.appendChild(suggestionsContainer);
        }
        
        suggestionsContainer.innerHTML = '';
        
        suggestions.forEach((suggestion, index) => {
            const item = document.createElement('div');
            item.className = 'suggestion-item px-4 py-3 hover:bg-gray-100 cursor-pointer border-b border-gray-100 last:border-b-0';
            item.innerHTML = `
                <div class="flex items-center">
                    <div class="flex-shrink-0 w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center mr-3">
                        <svg class="w-4 h-4 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
                        </svg>
                    </div>
                    <div class="flex-1">
                        <div class="text-sm font-medium text-gray-900">${suggestion.title}</div>
                        <div class="text-xs text-gray-500">${suggestion.category}</div>
                    </div>
                </div>
            `;
            
            item.addEventListener('click', function() {
                searchInput.value = suggestion.query;
                searchForm.submit();
            });
            
            item.addEventListener('mouseenter', function() {
                updateSelectedSuggestion(suggestionsContainer.children, index);
            });
            
            suggestionsContainer.appendChild(item);
        });
        
        suggestionsContainer.classList.remove('hidden');
    }
    
    function updateSelectedSuggestion(items, selectedIndex) {
        items.forEach((item, index) => {
            if (index === selectedIndex) {
                item.classList.add('selected', 'bg-purple-50');
            } else {
                item.classList.remove('selected', 'bg-purple-50');
            }
        });
    }
    
    function hideSearchSuggestions() {
        const suggestionsContainer = document.getElementById('search-suggestions');
        if (suggestionsContainer) {
            suggestionsContainer.classList.add('hidden');
        }
    }
    
    // Search history management
    const searchHistory = JSON.parse(localStorage.getItem('searchHistory') || '[]');
    
    function addToSearchHistory(query) {
        if (query.length < 2) return;
        
        const updatedHistory = [query, ...searchHistory.filter(item => item !== query)].slice(0, 10);
        localStorage.setItem('searchHistory', JSON.stringify(updatedHistory));
    }
    
    // Enhanced search analytics
    function trackSearch(query, resultsCount) {
        if (typeof gtag !== 'undefined') {
            gtag('event', 'search', {
                'search_term': query,
                'results_count': resultsCount
            });
        }
    }
    
    // Voice search support
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const voiceSearchButton = document.createElement('button');
        voiceSearchButton.className = 'absolute right-2 top-1/2 text-gray-400 hover:text-gray-600';
        voiceSearchButton.innerHTML = `
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7 0m0 0a7 7 0 017 7 0m-7-7v14m7 0l3-3m-3 3h14M8 21h8a2 2 0 002-2v-2a2 2 0 00-2-2H6a2 2 0 00-2 2v2a2 2 0 002 2h2m-3 3h6l-3-3"></path>
            </svg>
        `;
        
        voiceSearchButton.addEventListener('click', function() {
            startVoiceSearch();
        });
        
        searchInput.parentNode.appendChild(voiceSearchButton);
    }
    
    function startVoiceSearch() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const recognition = new SpeechRecognition();
        
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';
        
        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            searchInput.value = transcript;
            searchForm.submit();
        };
        
        recognition.onerror = function(event) {
            console.error('Speech recognition error:', event.error);
        };
        
        recognition.start();
    }
});
