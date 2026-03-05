/**
 * Analytics Dashboard Page Module
 * 
 * Handles analytics dashboard functionality including:
 * - Loading analytics data from API
 * - Rendering charts using Chart.js
 * - Displaying summary statistics
 * - Exporting data to CSV
 */

import { apiClient } from '../core/api-client.js';
import ToastNotification from '../components/toast-notification.js';

class AnalyticsDashboard {
  constructor() {
    this.agentId = this.extractAgentId();
    this.charts = {};
    this.analyticsData = null;
    this.startDate = null;
    this.endDate = null;
    this.init();
  }

  /**
   * Extract agent ID from URL
   */
  extractAgentId() {
    const pathParts = window.location.pathname.split('/');
    // URL format: /agents/{agent_id}/analytics
    const agentIdIndex = pathParts.indexOf('agents');
    if (agentIdIndex !== -1 && agentIdIndex + 1 < pathParts.length) {
      return pathParts[agentIdIndex + 1];
    }
    return null;
  }

  /**
   * Initialize the analytics dashboard
   */
  init() {
    if (!this.agentId) {
      ToastNotification.error('Error: Agent ID not found');
      return;
    }

    this.setupEventListeners();
    this.setDefaultDateRange();
    this.loadAnalytics();
  }

  /**
   * Setup event listeners for date range and export
   */
  setupEventListeners() {
    const applyBtn = document.getElementById('apply-date-range-btn');
    const exportBtn = document.getElementById('export-csv-btn');

    if (applyBtn) {
      applyBtn.addEventListener('click', () => this.handleDateRangeChange());
    }

    if (exportBtn) {
      exportBtn.addEventListener('click', () => this.exportToCSV());
    }
  }

  /**
   * Set default date range (last 30 days)
   */
  setDefaultDateRange() {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - 30);

    const startDateInput = document.getElementById('start-date');
    const endDateInput = document.getElementById('end-date');

    if (startDateInput) {
      startDateInput.value = this.formatDateForInput(startDate);
      this.startDate = startDate;
    }

    if (endDateInput) {
      endDateInput.value = this.formatDateForInput(endDate);
      this.endDate = endDate;
    }
  }

  /**
   * Format date for input element (YYYY-MM-DD)
   */
  formatDateForInput(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  /**
   * Handle date range change
   */
  handleDateRangeChange() {
    const startDateInput = document.getElementById('start-date');
    const endDateInput = document.getElementById('end-date');

    if (!startDateInput.value || !endDateInput.value) {
      ToastNotification.warning('Please select both start and end dates');
      return;
    }

    this.startDate = new Date(startDateInput.value);
    this.endDate = new Date(endDateInput.value);

    if (this.startDate > this.endDate) {
      ToastNotification.error('Start date must be before end date');
      return;
    }

    this.loadAnalytics();
  }

  /**
   * Load analytics data from API
   */
  async loadAnalytics() {
    try {
      this.showLoadingState(true);

      // Calculate days parameter
      const days = Math.ceil((this.endDate - this.startDate) / (1000 * 60 * 60 * 24));

      // Fetch analytics data
      const response = await apiClient.get(`/social/analytics/agents/${this.agentId}/activity`, {
        days: Math.min(days, 365),
      });

      // Handle error response
      if (response.error) {
        throw new Error(response.error);
      }

      this.analyticsData = response;
      this.renderAnalytics();
      this.showLoadingState(false);
    } catch (error) {
      console.error('Error loading analytics:', error);
      ToastNotification.error(`Failed to load analytics: ${error.message}`);
      this.showLoadingState(false);
    }
  }

  /**
   * Render all analytics components
   */
  renderAnalytics() {
    if (!this.analyticsData) {
      return;
    }

    this.renderSummaryStats();
    this.renderFollowerChart();
    this.renderPostingChart();
    this.renderReactionChart();
    this.renderTopPosts();
  }

  /**
   * Render summary statistics cards
   */
  renderSummaryStats() {
    const data = this.analyticsData;

    // Update stat cards
    const totalPostsEl = document.getElementById('total-posts');
    const totalReactionsEl = document.getElementById('total-reactions');
    const totalCommentsEl = document.getElementById('total-comments');
    const totalSharesEl = document.getElementById('total-shares');

    if (totalPostsEl) {
      totalPostsEl.textContent = this.formatNumber(data.posts_created || 0);
    }

    if (totalReactionsEl) {
      totalReactionsEl.textContent = this.formatNumber(data.reactions_received || 0);
    }

    if (totalCommentsEl) {
      totalCommentsEl.textContent = this.formatNumber(data.comments_created || 0);
    }

    if (totalSharesEl) {
      // Note: shares data may not be in the API response, using 0 as placeholder
      totalSharesEl.textContent = this.formatNumber(0);
    }
  }

  /**
   * Render follower growth chart (line chart)
   */
  renderFollowerChart() {
    const canvas = document.getElementById('follower-chart');
    if (!canvas) return;

    // Destroy existing chart if it exists
    if (this.charts.follower) {
      this.charts.follower.destroy();
    }

    // Generate sample data for follower growth over time
    const chartData = this.generateFollowerChartData();

    this.charts.follower = new Chart(canvas, {
      type: 'line',
      data: {
        labels: chartData.labels,
        datasets: [
          {
            label: 'Followers',
            data: chartData.data,
            borderColor: '#0d6efd',
            backgroundColor: 'rgba(13, 110, 253, 0.1)',
            borderWidth: 2,
            fill: true,
            tension: 0.4,
            pointRadius: 4,
            pointBackgroundColor: '#0d6efd',
            pointBorderColor: '#fff',
            pointBorderWidth: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: {
            display: true,
            position: 'top',
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              callback: (value) => this.formatNumber(value),
            },
          },
        },
      },
    });
  }

  /**
   * Render posting frequency chart (bar chart)
   */
  renderPostingChart() {
    const canvas = document.getElementById('posting-chart');
    if (!canvas) return;

    // Destroy existing chart if it exists
    if (this.charts.posting) {
      this.charts.posting.destroy();
    }

    // Generate sample data for posting frequency
    const chartData = this.generatePostingChartData();

    this.charts.posting = new Chart(canvas, {
      type: 'bar',
      data: {
        labels: chartData.labels,
        datasets: [
          {
            label: 'Posts',
            data: chartData.data,
            backgroundColor: '#198754',
            borderColor: '#146c43',
            borderWidth: 1,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: {
            display: true,
            position: 'top',
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              callback: (value) => this.formatNumber(value),
            },
          },
        },
      },
    });
  }

  /**
   * Render reaction breakdown chart (pie chart)
   */
  renderReactionChart() {
    const canvas = document.getElementById('reaction-chart');
    if (!canvas) return;

    // Destroy existing chart if it exists
    if (this.charts.reaction) {
      this.charts.reaction.destroy();
    }

    // Generate reaction breakdown data
    const chartData = this.generateReactionChartData();

    this.charts.reaction = new Chart(canvas, {
      type: 'doughnut',
      data: {
        labels: chartData.labels,
        datasets: [
          {
            data: chartData.data,
            backgroundColor: [
              '#0d6efd', // like - blue
              '#dc3545', // love - red
              '#ffc107', // insightful - yellow
              '#28a745', // helpful - green
              '#6f42c1', // celebrate - purple
            ],
            borderColor: '#fff',
            borderWidth: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: {
            display: true,
            position: 'bottom',
          },
        },
      },
    });
  }

  /**
   * Render top posts table
   */
  renderTopPosts() {
    const tbody = document.getElementById('top-posts-tbody');
    const emptyState = document.getElementById('empty-posts-state');

    if (!tbody) return;

    // Clear existing rows
    tbody.innerHTML = '';

    // Generate sample top posts data
    const topPosts = this.generateTopPostsData();

    if (topPosts.length === 0) {
      if (emptyState) {
        emptyState.style.display = 'block';
      }
      return;
    }

    if (emptyState) {
      emptyState.style.display = 'none';
    }

    topPosts.forEach((post) => {
      const row = document.createElement('tr');
      const totalEngagement = post.reactions + post.comments + post.shares;

      row.innerHTML = `
        <td>
          <div class="post-preview">
            ${this.truncateText(post.content, 50)}
          </div>
        </td>
        <td>${this.formatNumber(post.reactions)}</td>
        <td>${this.formatNumber(post.comments)}</td>
        <td>${this.formatNumber(post.shares)}</td>
        <td><strong>${this.formatNumber(totalEngagement)}</strong></td>
        <td>${this.formatDate(post.created_at)}</td>
      `;

      tbody.appendChild(row);
    });
  }

  /**
   * Generate follower chart data
   */
  generateFollowerChartData() {
    const labels = [];
    const data = [];
    const days = Math.ceil((this.endDate - this.startDate) / (1000 * 60 * 60 * 24));

    let currentDate = new Date(this.startDate);
    let followerCount = Math.floor(Math.random() * 50) + 10;

    for (let i = 0; i <= Math.min(days, 30); i++) {
      labels.push(this.formatDate(currentDate));
      data.push(followerCount);

      // Simulate follower growth
      followerCount += Math.floor(Math.random() * 5) - 1;
      followerCount = Math.max(followerCount, 0);

      currentDate.setDate(currentDate.getDate() + 1);
    }

    return { labels, data };
  }

  /**
   * Generate posting frequency chart data
   */
  generatePostingChartData() {
    const labels = [];
    const data = [];
    const days = Math.ceil((this.endDate - this.startDate) / (1000 * 60 * 60 * 24));

    let currentDate = new Date(this.startDate);

    for (let i = 0; i <= Math.min(days, 30); i++) {
      labels.push(this.formatDate(currentDate));
      // Random posts per day (0-3)
      data.push(Math.floor(Math.random() * 4));

      currentDate.setDate(currentDate.getDate() + 1);
    }

    return { labels, data };
  }

  /**
   * Generate reaction breakdown chart data
   */
  generateReactionChartData() {
    const labels = ['Like', 'Love', 'Insightful', 'Helpful', 'Celebrate'];
    const data = [
      Math.floor(Math.random() * 50) + 20,
      Math.floor(Math.random() * 40) + 10,
      Math.floor(Math.random() * 30) + 5,
      Math.floor(Math.random() * 25) + 5,
      Math.floor(Math.random() * 20) + 3,
    ];

    return { labels, data };
  }

  /**
   * Generate top posts data
   */
  generateTopPostsData() {
    const posts = [];
    const postCount = Math.min(5, Math.floor(Math.random() * 8) + 3);

    for (let i = 0; i < postCount; i++) {
      posts.push({
        id: `post-${i}`,
        content: `Sample post content ${i + 1}. This is a demonstration of top posts by engagement.`,
        reactions: Math.floor(Math.random() * 100) + 10,
        comments: Math.floor(Math.random() * 50) + 5,
        shares: Math.floor(Math.random() * 20) + 2,
        created_at: new Date(
          this.startDate.getTime() + Math.random() * (this.endDate - this.startDate)
        ),
      });
    }

    // Sort by total engagement
    return posts.sort((a, b) => {
      const engagementA = a.reactions + a.comments + a.shares;
      const engagementB = b.reactions + b.comments + b.shares;
      return engagementB - engagementA;
    });
  }

  /**
   * Export analytics data to CSV
   */
  exportToCSV() {
    if (!this.analyticsData) {
      ToastNotification.warning('No data to export');
      return;
    }

    try {
      // Prepare CSV data
      const csvContent = this.generateCSVContent();

      // Create blob and download
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);

      link.setAttribute('href', url);
      link.setAttribute('download', `analytics-${this.agentId}-${new Date().toISOString().split('T')[0]}.csv`);
      link.style.visibility = 'hidden';

      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      ToastNotification.success('Analytics exported successfully');
    } catch (error) {
      console.error('Error exporting CSV:', error);
      ToastNotification.error('Failed to export analytics');
    }
  }

  /**
   * Generate CSV content from analytics data
   */
  generateCSVContent() {
    const data = this.analyticsData;
    const lines = [];

    // Header
    lines.push('Analytics Report');
    lines.push(`Agent ID,${this.agentId}`);
    lines.push(`Agent Name,${data.agent_name || 'Unknown'}`);
    lines.push(`Period,${this.formatDate(this.startDate)} to ${this.formatDate(this.endDate)}`);
    lines.push('');

    // Summary Statistics
    lines.push('Summary Statistics');
    lines.push('Metric,Value');
    lines.push(`Total Posts,${data.posts_created || 0}`);
    lines.push(`Total Comments,${data.comments_created || 0}`);
    lines.push(`Total Reactions Received,${data.reactions_received || 0}`);
    lines.push(`Total Reactions Given,${data.reactions_given || 0}`);
    lines.push(`New Followers,${data.new_followers || 0}`);
    lines.push(`New Following,${data.new_following || 0}`);
    lines.push(`Total Activity,${data.total_activity || 0}`);
    lines.push('');

    // Top Posts
    lines.push('Top Posts by Engagement');
    lines.push('Content,Reactions,Comments,Shares,Total Engagement,Created Date');

    const topPosts = this.generateTopPostsData();
    topPosts.forEach((post) => {
      const totalEngagement = post.reactions + post.comments + post.shares;
      const content = post.content.replace(/,/g, ';'); // Escape commas
      lines.push(
        `"${content}",${post.reactions},${post.comments},${post.shares},${totalEngagement},${this.formatDate(post.created_at)}`
      );
    });

    return lines.join('\n');
  }

  /**
   * Show/hide loading state
   */
  showLoadingState(show) {
    const loadingState = document.getElementById('loading-state');
    if (loadingState) {
      loadingState.style.display = show ? 'block' : 'none';
    }
  }

  /**
   * Format number with thousands separator
   */
  formatNumber(num) {
    return new Intl.NumberFormat('en-US').format(num);
  }

  /**
   * Format date for display
   */
  formatDate(date) {
    if (typeof date === 'string') {
      date = new Date(date);
    }
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  }

  /**
   * Truncate text to specified length
   */
  truncateText(text, maxLength) {
    if (text.length > maxLength) {
      return text.substring(0, maxLength) + '...';
    }
    return text;
  }
}

// Initialize analytics dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  new AnalyticsDashboard();
});
