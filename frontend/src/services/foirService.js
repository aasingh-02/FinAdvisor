/**
 * frontend/src/services/foirService.js
 * ────────────────────────────────────
 * Axios API service for FOIR (Fixed Obligation to Income Ratio) calculation.
 * Calls the FastAPI backend which serves as the single source of truth.
 * Authentication uses HTTP-only session cookies (withCredentials: true).
 */

import api from './api';

export const foirService = {
  /**
   * Fetch FOIR calculation and borrowing capacity for the authenticated user.
   *
   * @param {Object} options
   * @param {number|string} [options.threshold=40.0] - Configured FOIR policy limit percentage (1 - 100)
   * @param {number|string|null} [options.proposedEmi=null] - Optional proposed monthly loan EMI to simulate
   * @returns {Promise<Object>} Backend FOIRCalculationResponse
   */
  async calculateFOIR({ threshold = 40.0, proposedEmi = null } = {}) {
    const params = {};

    if (threshold !== undefined && threshold !== null && threshold !== '') {
      params.threshold = parseFloat(threshold);
    }

    if (
      proposedEmi !== undefined &&
      proposedEmi !== null &&
      proposedEmi !== '' &&
      !isNaN(proposedEmi) &&
      parseFloat(proposedEmi) >= 0
    ) {
      params.proposed_emi = parseFloat(proposedEmi);
    }

    const response = await api.get('/api/v1/foir/calculate', { params });
    return response.data;
  },
};

export default foirService;
