/**
 * frontend/src/utils/advisorProvider.js
 * ────────────────────────────────────────
 * Single source of truth for resolving and formatting AI Advisor provider labels
 * consistently across the sidebar, chat header, response badges, and Ground Truth panel.
 */

export const ADVISOR_PROVIDER_LABELS = Object.freeze({
  RULE_BASED: 'Rule-Based AI Advisor',
  GEMINI: 'Gemini AI',
});

export const DEFAULT_ADVISOR_PROVIDER = Object.freeze({
  key: 'rule_based',
  label: ADVISOR_PROVIDER_LABELS.RULE_BASED,
  isGemini: false,
  isFallback: true,
});

/**
 * Resolve the active AI Advisor provider solely from a backend AdvisorResponse
 * (or chat message object). Displays "Gemini AI" only when an actual Gemini
 * model response succeeded with is_fallback=false.
 */
export function resolveAdvisorProvider(source) {
  if (!source || typeof source !== 'object') {
    return DEFAULT_ADVISOR_PROVIDER;
  }

  const modelUsed = typeof source.model_used === 'string' ? source.model_used.trim() : '';
  const isExplicitFallback =
    Boolean(source.is_fallback) ||
    modelUsed.toLowerCase() === 'finadvisor-deterministic-fallback';

  const isGeminiModel = /^(models\/)?gemini(\b|[-_.\s]|$)/i.test(modelUsed);

  if (!isExplicitFallback && isGeminiModel) {
    return {
      key: 'gemini',
      label: ADVISOR_PROVIDER_LABELS.GEMINI,
      isGemini: true,
      isFallback: false,
    };
  }

  return DEFAULT_ADVISOR_PROVIDER;
}

/**
 * Build consistent Financial Ground Truth guardrail wording for the active provider.
 */
export function getGroundTruthGuardrailText(provider) {
  const resolved =
    provider && typeof provider.label === 'string'
      ? provider
      : DEFAULT_ADVISOR_PROVIDER;

  return `${resolved.label} strictly references verified figures above and never recalculates them.`;
}
