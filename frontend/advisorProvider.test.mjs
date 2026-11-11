import test, { after, before, describe } from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { StaticRouter } from 'react-router-dom/server.mjs';
import { createServer } from 'vite';

import {
  ADVISOR_PROVIDER_LABELS,
  DEFAULT_ADVISOR_PROVIDER,
  getGroundTruthGuardrailText,
  resolveAdvisorProvider,
} from './src/utils/advisorProvider.js';

describe('advisorProvider utility', () => {
  test('defaults to Rule-Based AI Advisor when no response or empty input is provided', () => {
    assert.deepEqual(resolveAdvisorProvider(null), DEFAULT_ADVISOR_PROVIDER);
    assert.deepEqual(resolveAdvisorProvider(undefined), DEFAULT_ADVISOR_PROVIDER);
    assert.deepEqual(resolveAdvisorProvider({}), DEFAULT_ADVISOR_PROVIDER);
    assert.equal(DEFAULT_ADVISOR_PROVIDER.label, 'Rule-Based AI Advisor');
    assert.equal(DEFAULT_ADVISOR_PROVIDER.isGemini, false);
    assert.equal(DEFAULT_ADVISOR_PROVIDER.isFallback, true);
  });

  test('returns Rule-Based AI Advisor when deterministic fallback is active', () => {
    const provider = resolveAdvisorProvider({
      is_fallback: true,
      model_used: 'finadvisor-deterministic-fallback',
    });

    assert.equal(provider.label, ADVISOR_PROVIDER_LABELS.RULE_BASED);
    assert.equal(provider.isGemini, false);
    assert.equal(provider.isFallback, true);
  });

  test('never displays Gemini AI when is_fallback is true even if a gemini model name is attached', () => {
    const provider = resolveAdvisorProvider({
      is_fallback: true,
      model_used: 'gemini-3.8-flash',
    });

    assert.equal(provider.label, 'Rule-Based AI Advisor');
    assert.equal(provider.isGemini, false);
  });

  test('never displays Gemini AI for generic non-Gemini model names', () => {
    assert.equal(
      resolveAdvisorProvider({ is_fallback: false, model_used: 'finadvisor-copilot' }).label,
      'Rule-Based AI Advisor'
    );
    assert.equal(
      resolveAdvisorProvider({ is_fallback: false, model_used: '' }).label,
      'Rule-Based AI Advisor'
    );
  });

  test('returns Gemini AI only when actual Gemini API response succeeds with is_fallback=false', () => {
    const flash = resolveAdvisorProvider({
      is_fallback: false,
      model_used: 'gemini-3.8-flash',
    });
    assert.equal(flash.label, ADVISOR_PROVIDER_LABELS.GEMINI);
    assert.equal(flash.isGemini, true);
    assert.equal(flash.isFallback, false);

    const prefixed = resolveAdvisorProvider({
      is_fallback: false,
      model_used: 'models/gemini-2.0-flash',
    });
    assert.equal(prefixed.label, 'Gemini AI');
    assert.equal(prefixed.isGemini, true);
  });

  test('builds accurate Ground Truth guardrail text matching active provider', () => {
    assert.equal(
      getGroundTruthGuardrailText(DEFAULT_ADVISOR_PROVIDER),
      'Rule-Based AI Advisor strictly references verified figures above and never recalculates them.'
    );
    assert.equal(
      getGroundTruthGuardrailText(resolveAdvisorProvider({ is_fallback: false, model_used: 'gemini-3.8-flash' })),
      'Gemini AI strictly references verified figures above and never recalculates them.'
    );
  });
});

describe('AI Advisor UI provider label consistency', () => {
  let viteServer;
  let AuthContext;
  let AdvisorStatusProvider;
  let Sidebar;
  let navigationItems;
  let ChatBubble;
  let VerifiedSnapshotSidebar;
  let AIAdvisorPage;

  const sampleSnapshot = {
    monthly_net_income: 120000,
    monthly_living_expenses: 40000,
    existing_monthly_emi: 15000,
    disposable_monthly_cash_flow: 65000,
    emergency_savings_total: 400000,
    emergency_fund_months: 7.2,
    total_active_loans: 1,
    current_foir_percentage: 12.5,
    foir_status: 'Optimal',
    overall_health_score: 84.5,
    letter_grade: 'A',
    overall_risk_category: 'LOW',
    is_borrowing_eligible: true,
    prudent_max_monthly_emi: 35000,
  };

  before(async () => {
    viteServer = await createServer({
      appType: 'custom',
      logLevel: 'silent',
      server: { middlewareMode: true, watch: null },
    });

    const [authCtxMod, ctxMod, sidebarMod, bubbleMod, snapshotMod, pageMod] = await Promise.all([
      viteServer.ssrLoadModule('/src/context/AuthContext.jsx'),
      viteServer.ssrLoadModule('/src/context/AdvisorStatusContext.jsx'),
      viteServer.ssrLoadModule('/src/components/layout/Sidebar.jsx'),
      viteServer.ssrLoadModule('/src/components/advisor/ChatBubble.jsx'),
      viteServer.ssrLoadModule('/src/components/advisor/VerifiedSnapshotSidebar.jsx'),
      viteServer.ssrLoadModule('/src/pages/AIAdvisorPage.jsx'),
    ]);

    AuthContext = authCtxMod.AuthContext;
    AdvisorStatusProvider = ctxMod.AdvisorStatusProvider;
    Sidebar = sidebarMod.Sidebar;
    navigationItems = sidebarMod.navigationItems;
    ChatBubble = bubbleMod.ChatBubble;
    VerifiedSnapshotSidebar = snapshotMod.VerifiedSnapshotSidebar;
    AIAdvisorPage = pageMod.AIAdvisorPage;
  });

  after(async () => {
    if (viteServer) {
      await viteServer.close();
    }
  });

  test('Sidebar navigation item no longer hardcodes Gemini and renders Rule-Based AI Advisor by default', () => {
    const advisorNavItem = navigationItems.find((item) => item.to === '/ai-advisor');
    assert.ok(advisorNavItem);
    assert.equal(advisorNavItem.badge, null);

    const html = renderToStaticMarkup(
      React.createElement(
        StaticRouter,
        { location: '/ai-advisor' },
        React.createElement(
          AdvisorStatusProvider,
          null,
          React.createElement(Sidebar, { isOpen: false, onClose: () => {} })
        )
      )
    );

    assert.match(html, /Rule-Based AI Advisor/);
    assert.doesNotMatch(html, /Gemini/i);
  });

  test('Sidebar displays Gemini AI when actual Gemini API response is active', () => {
    const geminiProvider = resolveAdvisorProvider({
      is_fallback: false,
      model_used: 'gemini-3.8-flash',
    });

    const html = renderToStaticMarkup(
      React.createElement(
        StaticRouter,
        { location: '/ai-advisor' },
        React.createElement(
          AdvisorStatusProvider,
          { initialProvider: geminiProvider },
          React.createElement(Sidebar, { isOpen: false, onClose: () => {} })
        )
      )
    );

    assert.match(html, /Gemini AI/);
    assert.doesNotMatch(html, /Rule-Based/);
  });

  test('ChatBubble renders Rule-Based AI Advisor for fallback and Gemini AI only for real Gemini responses', () => {
    const fallbackHtml = renderToStaticMarkup(
      React.createElement(ChatBubble, {
        message: {
          role: 'model',
          content: 'Deterministic explanation.',
          is_fallback: true,
          model_used: 'finadvisor-deterministic-fallback',
        },
      })
    );

    assert.match(fallbackHtml, /Rule-Based AI Advisor/);
    assert.doesNotMatch(fallbackHtml, /Rule-Based Fallback/);
    assert.doesNotMatch(fallbackHtml, /Deterministic Fallback/);
    assert.doesNotMatch(fallbackHtml, /Gemini/i);

    const geminiHtml = renderToStaticMarkup(
      React.createElement(ChatBubble, {
        message: {
          role: 'model',
          content: 'Gemini response.',
          is_fallback: false,
          model_used: 'gemini-3.8-flash',
        },
      })
    );

    assert.match(geminiHtml, /Gemini AI/);
    assert.doesNotMatch(geminiHtml, /Rule-Based AI Advisor/);
    assert.doesNotMatch(geminiHtml, /gemini-3\.8-flash/);
  });

  test('Financial Ground Truth panel reflects Rule-Based AI Advisor by default and Gemini AI only when active', () => {
    const fallbackSnapshotHtml = renderToStaticMarkup(
      React.createElement(
        StaticRouter,
        { location: '/ai-advisor' },
        React.createElement(
          AdvisorStatusProvider,
          null,
          React.createElement(VerifiedSnapshotSidebar, { snapshot: sampleSnapshot })
        )
      )
    );

    assert.match(fallbackSnapshotHtml, /Financial Ground Truth/);
    assert.match(fallbackSnapshotHtml, /Rule-Based AI Advisor/);
    assert.match(
      fallbackSnapshotHtml,
      /Rule-Based AI Advisor strictly references verified figures above and never recalculates them\./
    );
    assert.doesNotMatch(fallbackSnapshotHtml, /Gemini/i);

    const uninitializedHtml = renderToStaticMarkup(
      React.createElement(
        StaticRouter,
        { location: '/ai-advisor' },
        React.createElement(
          AdvisorStatusProvider,
          null,
          React.createElement(VerifiedSnapshotSidebar, { snapshot: null })
        )
      )
    );
    assert.match(uninitializedHtml, /Rule-Based AI Advisor/);
    assert.doesNotMatch(uninitializedHtml, /Gemini/i);

    const geminiProvider = resolveAdvisorProvider({
      is_fallback: false,
      model_used: 'gemini-3.8-flash',
    });

    const geminiSnapshotHtml = renderToStaticMarkup(
      React.createElement(
        StaticRouter,
        { location: '/ai-advisor' },
        React.createElement(
          AdvisorStatusProvider,
          { initialProvider: geminiProvider },
          React.createElement(VerifiedSnapshotSidebar, { snapshot: sampleSnapshot })
        )
      )
    );

    assert.match(geminiSnapshotHtml, /Gemini AI/);
    assert.match(
      geminiSnapshotHtml,
      /Gemini AI strictly references verified figures above and never recalculates them\./
    );
    assert.doesNotMatch(geminiSnapshotHtml, /Rule-Based AI Advisor/);
  });

  const renderWithProviders = (node, initialProvider) =>
    renderToStaticMarkup(
      React.createElement(
        StaticRouter,
        { location: '/ai-advisor' },
        React.createElement(
          AuthContext.Provider,
          { value: { user: { full_name: 'Test User', email: 'test@example.com' }, loading: false } },
          React.createElement(
            AdvisorStatusProvider,
            initialProvider ? { initialProvider } : null,
            node
          )
        )
      )
    );

  test('AIAdvisorPage consistently renders Rule-Based AI Advisor across sidebar, chat header, welcome bubble, and Ground Truth panel on load', () => {
    const combinedHtml = renderWithProviders(
      React.createElement(
        React.Fragment,
        null,
        React.createElement(Sidebar, { isOpen: false, onClose: () => {} }),
        React.createElement(AIAdvisorPage),
        React.createElement(VerifiedSnapshotSidebar, { snapshot: sampleSnapshot })
      )
    );

    const ruleBasedMatches = combinedHtml.match(/Rule-Based AI Advisor/g) || [];
    // Sidebar badge + Chat header badge + Welcome ChatBubble + AIAdvisorPage uninitialized card
    // + VerifiedSnapshotSidebar Ground Truth Active Provider badge & guardrail copy
    assert.ok(ruleBasedMatches.length >= 5);
    assert.doesNotMatch(combinedHtml, /Gemini/i);
    assert.doesNotMatch(combinedHtml, /Rule-Based Fallback/);
    assert.doesNotMatch(combinedHtml, /Deterministic Fallback/);
    assert.doesNotMatch(combinedHtml, /finadvisor-copilot/);
  });

  test('Sidebar, AIAdvisorPage chat header, ChatBubble, and Ground Truth panel all display Gemini AI when Gemini API succeeds', () => {
    const geminiProvider = resolveAdvisorProvider({
      is_fallback: false,
      model_used: 'gemini-3.8-flash',
    });

    const combinedHtml = renderWithProviders(
      React.createElement(
        React.Fragment,
        null,
        React.createElement(Sidebar, { isOpen: false, onClose: () => {} }),
        React.createElement(AIAdvisorPage),
        React.createElement(ChatBubble, {
          message: {
            role: 'model',
            content: 'Gemini guidance.',
            is_fallback: false,
            model_used: 'gemini-3.8-flash',
          },
        }),
        React.createElement(VerifiedSnapshotSidebar, { snapshot: sampleSnapshot })
      ),
      geminiProvider
    );

    const geminiMatches = combinedHtml.match(/Gemini AI/g) || [];
    // Sidebar badge + Chat header badge + Gemini ChatBubble + Ground Truth badge & guardrail copy
    assert.ok(geminiMatches.length >= 5);
    assert.doesNotMatch(combinedHtml, /Rule-Based Fallback/);
    assert.doesNotMatch(combinedHtml, /Deterministic Fallback/);
  });
});
