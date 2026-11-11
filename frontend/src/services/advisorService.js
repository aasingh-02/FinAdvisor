/**
 * frontend/src/services/advisorService.js
 * ───────────────────────────────────────
 * Axios API client service for the AI Financial Advisor & Copilot engine.
 *
 * Guarantees:
 * - Direct HTTP integration with FastAPI /api/v1/advisor/chat and /api/v1/advisor/explain.
 * - Exact schema alignment (message, context, history, user_query, custom_scenario).
 * - Enforces last 6 messages history constraint on client before transmission.
 * - HTTP-only session cookie authentication (withCredentials: true via api instance).
 * - All financial numbers returned originate deterministically from backend.
 */

import api from './api';

export const ADVISOR_CONTEXTS = {
  GENERAL: 'GENERAL',
  HEALTH_SCORE: 'HEALTH_SCORE',
  FOIR_AFFORDABILITY: 'FOIR_AFFORDABILITY',
  RISK_ASSESSMENT: 'RISK_ASSESSMENT',
  LOAN_RECOMMENDATIONS: 'LOAN_RECOMMENDATIONS',
  EMI_SIMULATION: 'EMI_SIMULATION',
};

export const advisorService = {
  /**
   * Send a conversational query to the AI Advisor.
   *
   * @param {Object} params
   * @param {string} params.message - User prompt or financial question (min 2 chars)
   * @param {string} [params.context='GENERAL'] - Advisor context domain
   * @param {Array<{role: string, content: string}>} [params.history=[]] - Conversation history
   * @returns {Promise<Object>} Backend AdvisorResponse
   */
  async chat({ message, context = ADVISOR_CONTEXTS.GENERAL, history = [] }) {
    const trimmedMessage = (message || '').trim();
    if (!trimmedMessage || trimmedMessage.length < 2) {
      throw new Error('Message must be at least 2 characters long.');
    }
    if (trimmedMessage.length > 1000) {
      throw new Error('Message must be at most 1000 characters long.');
    }

    // Strictly limit history to the last 6 messages and safely truncate oversized content
    const MAX_HISTORY_MSG_LEN = 1400;
    const sanitizedHistory = (history || [])
      .slice(-6)
      .filter((m) => m && m.content && typeof m.content === 'string' && m.content.trim())
      .map((m) => {
        const trimmed = m.content.trim();
        return {
          role: m.role === 'user' ? 'user' : 'model',
          content:
            trimmed.length > MAX_HISTORY_MSG_LEN
              ? trimmed.slice(0, MAX_HISTORY_MSG_LEN) + '... [truncated]'
              : trimmed,
        };
      });

    const payload = {
      message: trimmedMessage,
      context,
      history: sanitizedHistory,
    };

    const response = await api.post('/api/v1/advisor/chat', payload);
    return response.data;
  },

  /**
   * Request a focused explanation for a specific financial component.
   *
   * @param {Object} params
   * @param {string} params.context - Financial context domain (required)
   * @param {string} [params.userQuery] - Optional specific question about the metric
   * @param {Object} [params.customScenario] - Optional custom simulation payload (exact field: custom_scenario)
   * @returns {Promise<Object>} Backend AdvisorResponse
   */
  async explain({ context, userQuery = null, customScenario = null }) {
    if (!context) {
      throw new Error('Advisor context is required for an explanation.');
    }

    const payload = {
      context,
    };

    if (userQuery && typeof userQuery === 'string' && userQuery.trim()) {
      payload.user_query = userQuery.trim();
    }

    if (customScenario && typeof customScenario === 'object') {
      payload.custom_scenario = customScenario;
    }

    const response = await api.post('/api/v1/advisor/explain', payload);
    return response.data;
  },
};

export default advisorService;
