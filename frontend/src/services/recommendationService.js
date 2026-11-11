/**
 * frontend/src/services/recommendationService.js
 * ──────────────────────────────────────────────
 * Axios service for the Personalized Loan Recommendation Engine.
 *
 * Guarantees:
 * - Powered exclusively by FastAPI deterministic recommendation engine.
 * - Zero client-side financial calculations or mock figures.
 * - Uses HTTP-only cookie session authentication (withCredentials: true via api instance).
 * - Maps client options to backend RecommendationRequest Pydantic schema.
 */

import api from './api';

export const recommendationService = {
  /**
   * Request personalized loan recommendations based on the authenticated user's profile.
   *
   * @param {Object} options
   * @param {number|string} [options.foirThreshold=40.0] - Policy FOIR benchmark (1.0 to 100.0)
   * @param {string} [options.preferredCategory] - Optional loan category:
   *   'PERSONAL_LOAN' | 'HOME_LOAN' | 'VEHICLE_LOAN' | 'EDUCATION_LOAN'
   * @param {number|string} [options.desiredAmount] - Optional requested loan principal
   * @param {number} [options.preferredTenure] - Optional preferred tenure in months (6 to 360)
   * @returns {Promise<Object>} Backend RecommendationResponse
   */
  async generateRecommendations({
    foirThreshold = 40.0,
    preferredCategory = null,
    desiredAmount = null,
    preferredTenure = null,
  } = {}) {
    const payload = {};

    if (foirThreshold !== undefined && foirThreshold !== null && foirThreshold !== '') {
      payload.foir_threshold = parseFloat(foirThreshold);
    }

    if (preferredCategory) {
      payload.preferred_loan_category = preferredCategory;
    }

    if (desiredAmount !== undefined && desiredAmount !== null && desiredAmount !== '') {
      const parsedAmount = parseFloat(desiredAmount);
      if (!isNaN(parsedAmount) && parsedAmount > 0) {
        payload.desired_loan_amount = parsedAmount;
      }
    }

    if (preferredTenure !== undefined && preferredTenure !== null && preferredTenure !== '') {
      const parsedTenure = parseInt(preferredTenure, 10);
      if (!isNaN(parsedTenure) && parsedTenure > 0) {
        payload.preferred_tenure_months = parsedTenure;
      }
    }

    const response = await api.post('/api/v1/recommendations/generate', payload);
    return response.data;
  },
};

export default recommendationService;
