/**
 * frontend/src/services/riskService.js
 * ────────────────────────────────────
 * Axios service for the Financial Risk Assessment and Advisory Engine.
 * All computations are performed strictly on the FastAPI backend.
 * Uses HTTP-only cookie session authentication (withCredentials: true).
 */

import api from './api';

export const riskService = {
  /**
   * Fetch comprehensive financial risk assessment and recommendations for the current user.
   *
   * @param {Object} options
   * @param {number|string} [options.threshold=40.0] - Configured FOIR policy limit percentage (1 - 100)
   * @returns {Promise<Object>} Backend RiskAssessmentResponse
   */
  async getRiskAssessment({ threshold = 40.0 } = {}) {
    const params = {};
    if (threshold !== undefined && threshold !== null && threshold !== '') {
      params.threshold = parseFloat(threshold);
    }

    const response = await api.get('/api/v1/risk/assessment', { params });
    return response.data;
  },
};

export default riskService;
