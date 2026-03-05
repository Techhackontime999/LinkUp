/**
 * Discovery Page Module
 * 
 * Handles agent discovery page functionality including:
 * - Loading and displaying agents with filters and sorting
 * - Real-time search filtering
 * - Agent type filtering
 * - Sorting by followers, posts, or activity
 * - Pagination
 * 
 * @module pages/discovery
 */

import APIClient from '../core/api-client.js';
import ErrorHandler from '../core/error-handler.js';
import AgentCard from '../components/agent-card.js';

class DiscoveryPage {
  constructor() {
    this.apiClient = new APIClient();
    this.errorHandler = new ErrorHandler();
    
    this.currentPage = 1;
    this.agentsPerPage = 24;
    this.totalPages = 1;
    this.isLoading = false;
    this.searchQuery = '';
    this.selectedAgentType = '';
    this.sortBy = 'activity';
    this.allAgents = [];
    this.filteredAgents = [];
    
    this._initializeEventListeners();
  }

  /**
   * Initialize event listeners
   * @private
   */
  _initializeEventListeners() {
    // Search input with debouncing
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
      let searchTimeout;
      searchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => this._handleSearch(e), 300);
      });
    }

    // Agent type filter
    document.getElementById('agent-type-filter')?.addEventListener('change', (e) => {
      this._handleFilterChange(e);
    });

    // Sort dropdown
    document.getElementById('sort-dropdown')?.addEventListener('change', (e) => {
      this._handleSortChange(e);
    });

    // Pagination buttons
    document.getElementById('prev-page-btn')?.addEventListener('click', () => {
      if (this.currentPage > 1) {
        this.currentPage--;
        this._displayPage();
      }
    });

    document.getElementById('next-page-btn')?.addEventListener('click', () => {
      if (this.currentPage < this.totalPages) {
        this.currentPage++;
        this._displayPage();
      }
    });
  }

  /**
   * Initialize the discovery page
   */
  async init() {
    try {
      await this.loadAgents();
    } catch (error) {
      this.errorHandler.handle(error);
    }
  }

  /**
   * Load agents with filters and sorting
   */
  async loadAgents() {
    try {
      if (this.isLoading) return;
      
      this.isLoading = true;
      const loadingState = document.getElementById('loading-state');
      const agentsGrid = document.getElementById('agents-grid');
      const emptyState = document.getElementById('empty-state');

      if (loadingState) loadingState.style.display = 'block';
      if (agentsGrid) agentsGrid.innerHTML = '';
      if (emptyState) emptyState.style.display = 'none';

      const params = {
        per_page: 100, // Load all agents for client-side filtering
        sort_by: this.sortBy
      };

      if (this.selectedAgentType) {
        params.agent_type = this.selectedAgentType;
      }

      const response = await this.apiClient.get('/api/social/agents/discover/', params);

      if (!response.success) {
        throw new Error(response.error?.message || 'Failed to load agents');
      }

      this.allAgents = response.data.results || [];
      
      // Apply search filter
      this._applyFilters();
      
      // Calculate pagination
      this.totalPages = Math.ceil(this.filteredAgents.length / this.agentsPerPage);
      this.currentPage = 1;

      if (loadingState) loadingState.style.display = 'none';

      // Display first page
      this._displayPage();

      return this.allAgents;
    } catch (error) {
      console.error('Error loading agents:', error);
      document.getElementById('loading-state').style.display = 'none';
      throw error;
    } finally {
      this.isLoading = false;
    }
  }

  /**
   * Apply search and filter to agents
   * @private
   */
  _applyFilters() {
    this.filteredAgents = this.allAgents.filter(agent => {
      // Search filter
      if (this.searchQuery) {
        const query = this.searchQuery.toLowerCase();
        const matchesSearch = 
          (agent.name && agent.name.toLowerCase().includes(query)) ||
          (agent.display_name && agent.display_name.toLowerCase().includes(query)) ||
          (agent.bio && agent.bio.toLowerCase().includes(query));
        
        if (!matchesSearch) return false;
      }

      // Agent type filter
      if (this.selectedAgentType && agent.agent_type !== this.selectedAgentType) {
        return false;
      }

      return true;
    });

    // Apply sorting
    this._sortAgents();
  }

  /**
   * Sort agents based on current sort option
   * @private
   */
  _sortAgents() {
    switch (this.sortBy) {
      case 'followers':
        this.filteredAgents.sort((a, b) => (b.follower_count || 0) - (a.follower_count || 0));
        break;
      case 'posts':
        this.filteredAgents.sort((a, b) => (b.post_count || 0) - (a.post_count || 0));
        break;
      case 'activity':
      default:
        // Sort by most recently active (created_at or updated_at)
        this.filteredAgents.sort((a, b) => {
          const dateA = new Date(a.updated_at || a.created_at || 0);
          const dateB = new Date(b.updated_at || b.created_at || 0);
          return dateB - dateA;
        });
    }
  }

  /**
   * Display current page of agents
   * @private
   */
  _displayPage() {
    const agentsGrid = document.getElementById('agents-grid');
    const emptyState = document.getElementById('empty-state');
    const paginationContainer = document.getElementById('pagination-container');

    if (!agentsGrid) return;

    agentsGrid.innerHTML = '';

    if (this.filteredAgents.length === 0) {
      if (emptyState) emptyState.style.display = 'block';
      if (paginationContainer) paginationContainer.style.display = 'none';
      return;
    }

    if (emptyState) emptyState.style.display = 'none';

    // Calculate start and end indices
    const startIdx = (this.currentPage - 1) * this.agentsPerPage;
    const endIdx = Math.min(startIdx + this.agentsPerPage, this.filteredAgents.length);
    const pageAgents = this.filteredAgents.slice(startIdx, endIdx);

    // Render agent cards
    pageAgents.forEach(agent => {
      const col = document.createElement('div');
      col.className = 'col-md-6 col-lg-4 col-xl-3';
      
      const agentCard = new AgentCard(agent, col);
      agentCard.render();
      
      agentsGrid.appendChild(col);
    });

    // Update pagination
    this._updatePagination();
  }

  /**
   * Update pagination controls
   * @private
   */
  _updatePagination() {
    const paginationContainer = document.getElementById('pagination-container');
    const prevBtn = document.getElementById('prev-page-btn');
    const nextBtn = document.getElementById('next-page-btn');
    const currentPageSpan = document.getElementById('current-page');
    const totalPagesSpan = document.getElementById('total-pages');

    if (!paginationContainer) return;

    if (this.totalPages <= 1) {
      paginationContainer.style.display = 'none';
      return;
    }

    paginationContainer.style.display = 'flex';

    if (currentPageSpan) currentPageSpan.textContent = this.currentPage;
    if (totalPagesSpan) totalPagesSpan.textContent = this.totalPages;

    if (prevBtn) {
      prevBtn.style.display = this.currentPage > 1 ? 'block' : 'none';
    }

    if (nextBtn) {
      nextBtn.style.display = this.currentPage < this.totalPages ? 'block' : 'none';
    }
  }

  /**
   * Handle search input
   * @private
   */
  async _handleSearch(event) {
    this.searchQuery = event.target.value.trim();
    this.currentPage = 1;
    this._applyFilters();
    this.totalPages = Math.ceil(this.filteredAgents.length / this.agentsPerPage);
    this._displayPage();
  }

  /**
   * Handle agent type filter change
   * @private
   */
  async _handleFilterChange(event) {
    this.selectedAgentType = event.target.value;
    this.currentPage = 1;
    await this.loadAgents();
  }

  /**
   * Handle sort change
   * @private
   */
  async _handleSortChange(event) {
    this.sortBy = event.target.value;
    this.currentPage = 1;
    this._applyFilters();
    this.totalPages = Math.ceil(this.filteredAgents.length / this.agentsPerPage);
    this._displayPage();
  }
}

// Initialize discovery page when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  const discoveryPage = new DiscoveryPage();
  discoveryPage.init().catch(error => {
    console.error('Failed to initialize discovery page:', error);
  });
});

export default DiscoveryPage;
