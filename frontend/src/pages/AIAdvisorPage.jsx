import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useAdvisorStatus } from '../context/AdvisorStatusContext';
import advisorService, { ADVISOR_CONTEXTS } from '../services/advisorService';
import dashboardService from '../services/dashboardService';

import { ChatBubble } from '../components/advisor/ChatBubble';
import { PromptSuggestions } from '../components/advisor/PromptSuggestions';
import { VerifiedSnapshotSidebar } from '../components/advisor/VerifiedSnapshotSidebar';
import { AdvisorDisclaimerBanner } from '../components/advisor/AdvisorDisclaimerBanner';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { LoadingSpinner } from '../components/common/LoadingSpinner';

import {
  Bot,
  Send,
  Sparkles,
  RefreshCw,
  Trash2,
  Sliders,
  ShieldCheck,
  ChevronDown,
  RotateCcw,
} from 'lucide-react';

const CONTEXT_OPTIONS = [
  { value: ADVISOR_CONTEXTS.GENERAL, label: 'General Advisory' },
  { value: ADVISOR_CONTEXTS.HEALTH_SCORE, label: 'Health Score Breakdown' },
  { value: ADVISOR_CONTEXTS.FOIR_AFFORDABILITY, label: 'FOIR & Affordability' },
  { value: ADVISOR_CONTEXTS.RISK_ASSESSMENT, label: 'Risk Assessment' },
  { value: ADVISOR_CONTEXTS.LOAN_RECOMMENDATIONS, label: 'Loan Recommendations' },
  { value: ADVISOR_CONTEXTS.EMI_SIMULATION, label: 'EMI & Debt Simulation' },
];

const createSystemGreeting = (content) => ({
  role: 'model',
  content,
  model_used: 'finadvisor-deterministic-fallback',
  is_fallback: true,
});

const INITIAL_WELCOME_CONTENT =
  '### Welcome to FinAdvisor Copilot!\n\n' +
  'I am your AI financial planning copilot. I can help explain your Financial Health Score, ' +
  'evaluate debt burden sustainability, and explain prudent borrowing limits.\n\n' +
  '- **Strictly Grounded in Verified Figures:** All loan figures, FOIR percentages, and health scores are computed by deterministic backend services.\n' +
  '- **Select a Context Area:** Choose a specific financial topic above or pick a suggested question below to start.';

export const AIAdvisorPage = () => {
  const { user } = useAuth();
  const {
    advisorProvider,
    updateAdvisorProviderFromResponse,
    resetAdvisorProvider,
  } = useAdvisorStatus();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // URL Query Sync for deep-linking
  const initialContextParam = searchParams.get('context');
  const validInitialContext = Object.values(ADVISOR_CONTEXTS).includes(initialContextParam)
    ? initialContextParam
    : ADVISOR_CONTEXTS.GENERAL;

  const [selectedContext, setSelectedContext] = useState(validInitialContext);
  const [messages, setMessages] = useState([createSystemGreeting(INITIAL_WELCOME_CONTENT)]);

  const [input, setInput] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [lastError, setLastError] = useState(null);
  const [failedQuery, setFailedQuery] = useState(null);
  const [latestSnapshot, setLatestSnapshot] = useState(null);
  const [disclaimer, setDisclaimer] = useState('');

  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom of conversation
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isSubmitting]);

  // Synchronize context changes with URL query parameter
  const handleContextChange = (newContext) => {
    setSelectedContext(newContext);
    setSearchParams({ context: newContext });
  };

  // Pre-load dashboard snapshot on page load so sidebar is populated immediately
  useEffect(() => {
    let isMounted = true;
    const loadInitialSnapshot = async () => {
      try {
        const data = await dashboardService.getDashboardSummary();
        if (isMounted && data.profile_complete && data.metrics) {
          // Construct snapshot summary shape matching backend schema
          setLatestSnapshot({
            monthly_net_income: data.metrics.monthly_net_income,
            monthly_living_expenses: data.metrics.monthly_living_expenses,
            existing_monthly_emi: data.metrics.monthly_emi_burden,
            disposable_monthly_cash_flow: data.metrics.disposable_monthly_cash_flow,
            emergency_savings_total: data.metrics.emergency_savings_total,
            emergency_fund_months: data.metrics.emergency_fund_months,
            total_active_loans: data.metrics.total_active_loans,
            current_foir_percentage: data.current_foir_percentage,
            foir_status: data.foir_status,
            overall_health_score: data.health_score?.overall_score || null,
            letter_grade: data.health_score?.letter_grade || null,
            overall_risk_category: data.overall_risk_category || 'LOW',
            is_borrowing_eligible: data.is_borrowing_eligible,
            prudent_max_monthly_emi: data.prudent_max_borrowing_emi,
          });
        }
      } catch (err) {
        // Fallback silently if unprofiled or network issue
      }
    };

    loadInitialSnapshot();
    return () => {
      isMounted = false;
    };
  }, []);

  const applyAdvisorResponse = useCallback(
    (response) => {
      const modelMsg = {
        role: 'model',
        content: response.reply,
        model_used: response.model_used,
        is_fallback: response.is_fallback,
      };

      setMessages((prev) => [...prev, modelMsg]);

      if (response.financial_snapshot) {
        setLatestSnapshot(response.financial_snapshot);
      }
      if (response.disclaimer) {
        setDisclaimer(response.disclaimer);
      }
      updateAdvisorProviderFromResponse(response);
    },
    [updateAdvisorProviderFromResponse]
  );

  // Send query to backend chat endpoint
  const handleSendMessage = async (textToSend) => {
    const query = (textToSend || input).trim();
    if (!query || query.length < 2 || isSubmitting) return;

    // Optimistically record user message
    const userMsg = { role: 'user', content: query };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsSubmitting(true);
    setLastError(null);
    setFailedQuery(null);

    try {
      const response = await advisorService.chat({
        message: query,
        context: selectedContext,
        history: messages,
      });

      applyAdvisorResponse(response);
    } catch (err) {
      setLastError(err.message || 'Failed to receive advice from FinAdvisor Copilot. Please try again.');
      setFailedQuery(query);
      resetAdvisorProvider();
    } finally {
      setIsSubmitting(false);
    }
  };

  // Safe retry of the failed message without duplicate user messages
  const handleRetry = async () => {
    if (!failedQuery || isSubmitting) return;

    setIsSubmitting(true);
    setLastError(null);

    try {
      // Send history excluding the last failed message
      const historyToSend = messages.slice(0, -1);
      const response = await advisorService.chat({
        message: failedQuery,
        context: selectedContext,
        history: historyToSend,
      });

      applyAdvisorResponse(response);
      setFailedQuery(null);
    } catch (err) {
      setLastError(err.message || 'Retry attempt failed. Please check your connection.');
      resetAdvisorProvider();
    } finally {
      setIsSubmitting(false);
    }
  };

  // Clear chat thread
  const handleClearHistory = () => {
    setMessages([
      createSystemGreeting(
        '### Conversation Cleared\n\n' +
          'How can I help you today? Ask any financial query or choose a suggestion below.'
      ),
    ]);
    resetAdvisorProvider();
    setLastError(null);
    setFailedQuery(null);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Title & Context Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200/80">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              AI Financial Advisor & Copilot
            </h1>
            <Badge variant="primary" size="sm" className="hidden sm:inline-flex">
              Phase 5
            </Badge>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Personalized, plain-English guidance grounded in your verified financial metrics.
          </p>
        </div>

        {/* Provider status badge & Clear thread action */}
        <div className="flex items-center gap-2.5">
          <Badge
            variant={advisorProvider.isGemini ? 'primary' : 'default'}
            size="md"
            className="text-xs"
          >
            {advisorProvider.label}
          </Badge>
          <Button
            size="sm"
            variant="ghost"
            icon={Trash2}
            onClick={handleClearHistory}
            className="text-slate-500 hover:text-slate-800"
            title="Clear conversation history"
          >
            Clear Chat
          </Button>
        </div>
      </div>

      {/* Main 2-Column Responsive Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Interactive Chat (8 cols on desktop) */}
        <div className="lg:col-span-8 flex flex-col h-[740px] bg-white rounded-2xl border border-slate-200/80 shadow-card overflow-hidden">
          {/* Top Context Toolbar */}
          <div className="px-5 py-3.5 bg-slate-50/80 border-b border-slate-200/80 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Sliders className="w-4 h-4 text-brand-600" />
              <label htmlFor="context-select" className="text-xs font-semibold text-slate-700">
                Advisory Focus:
              </label>
              <select
                id="context-select"
                value={selectedContext}
                onChange={(e) => handleContextChange(e.target.value)}
                className="text-xs font-medium bg-white border border-slate-300 rounded-lg px-2.5 py-1 text-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition-colors"
              >
                {CONTEXT_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
              <span>Zero PII sent to AI</span>
            </div>
          </div>

          {/* Conversation Thread Area */}
          <div className="flex-1 p-5 overflow-y-auto space-y-2">
            {messages.map((msg, index) => (
              <ChatBubble
                key={index}
                message={msg}
                isLatest={index === messages.length - 1}
              />
            ))}

            {/* Typing / Loading Indicator */}
            {isSubmitting && (
              <div className="flex items-center gap-3 mb-4 text-slate-500 text-xs">
                <div className="w-8 h-8 rounded-full bg-purple-100 text-purple-700 border border-purple-200 flex items-center justify-center shrink-0">
                  <Bot className="w-4 h-4 animate-pulse" />
                </div>
                <div className="bg-slate-100 rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-2">
                  <LoadingSpinner size="sm" className="text-brand-600" />
                  <span className="font-medium text-slate-600">FinAdvisor Copilot is analyzing your request...</span>
                </div>
              </div>
            )}

            {/* Inline Error and Retry */}
            {lastError && (
              <div className="my-3 p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-800 flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <span className="font-semibold">Error:</span>
                  <span>{lastError}</span>
                </div>
                {failedQuery && (
                  <Button
                    size="sm"
                    variant="outline"
                    icon={RotateCcw}
                    onClick={handleRetry}
                    isLoading={isSubmitting}
                    className="shrink-0 bg-white"
                  >
                    Retry
                  </Button>
                )}
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Prompt Suggestions Bar */}
          <div className="px-5 pt-3 pb-2 border-t border-slate-100 bg-slate-50/50">
            <PromptSuggestions
              context={selectedContext}
              disabled={isSubmitting}
              onSelectPrompt={(text) => handleSendMessage(text)}
            />
          </div>

          {/* User Input Form */}
          <div className="p-4 border-t border-slate-200/80 bg-white">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage();
              }}
              className="flex items-end gap-2.5"
            >
              <div className="flex-1 relative">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={`Ask a question about ${CONTEXT_OPTIONS.find((c) => c.value === selectedContext)?.label.toLowerCase()}... (Press Enter to send)`}
                  rows={2}
                  maxLength={1000}
                  disabled={isSubmitting}
                  className="w-full text-sm resize-none rounded-xl border border-slate-300 p-3 pr-16 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 text-slate-800 placeholder-slate-400 transition-colors"
                />
                <span className="absolute bottom-2 right-3 text-[10px] text-slate-400 select-none">
                  {input.length}/1000
                </span>
              </div>

              <Button
                type="submit"
                variant="primary"
                size="md"
                disabled={!input.trim() || input.trim().length < 2 || isSubmitting}
                isLoading={isSubmitting}
                icon={Send}
                className="h-[58px] px-5 rounded-xl shrink-0"
              >
                Send
              </Button>
            </form>
          </div>

          {/* Compliance Disclaimer Footer */}
          <div className="px-5 py-2.5 bg-slate-50 border-t border-slate-100">
            <AdvisorDisclaimerBanner disclaimer={disclaimer} />
          </div>
        </div>

        {/* Right Column: Verified Financial Snapshot Sidebar (4 cols on desktop) */}
        <div className="lg:col-span-4 space-y-4">
          <VerifiedSnapshotSidebar
            snapshot={latestSnapshot}
            providerStatus={advisorProvider}
          />
        </div>
      </div>
    </div>
  );
};

export default AIAdvisorPage;
