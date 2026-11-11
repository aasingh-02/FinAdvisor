/**
 * frontend/src/services/dashboardService.js
 * ─────────────────────────────────────────
 * Axios client service for the Unified Financial Dashboard & Financial Health Score Engine.
 *
 * Guarantees:
 * - Direct HTTP integration with FastAPI GET /api/v1/dashboard.
 * - HTTP-only session cookie authentication (withCredentials: true via api instance).
 * - Zero client-side mathematical calculations or mock figures.
 * - Robust error handling with error propagation.
 */

import api from './api';

export const dashboardService = {
  /**
   * Fetch complete financial dashboard overview, health score, metric cards, and risk summary.
   *
   * @param {Object} [options]
   * @param {number|string} [options.threshold=40.0] - Policy FOIR benchmark percentage (1.0 to 100.0)
   * @returns {Promise<Object>} Backend DashboardSummaryResponse
   */
  async getDashboardSummary({ threshold = 40.0 } = {}) {
    const params = {};
    if (threshold !== undefined && threshold !== null && threshold !== '') {
      const parsed = parseFloat(threshold);
      if (!isNaN(parsed) && parsed > 0) {
        params.threshold = parsed;
      }
    }

    const response = await api.get('/api/v1/dashboard', { params });
    return response.data;
  },
};

export default dashboardService;
