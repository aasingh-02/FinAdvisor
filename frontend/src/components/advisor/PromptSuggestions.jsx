import React from 'react';
import { Sparkles, HelpCircle } from 'lucide-react';
import { ADVISOR_CONTEXTS } from '../../services/advisorService';

const SUGGESTIONS_BY_CONTEXT = {
  [ADVISOR_CONTEXTS.GENERAL]: [
    'Can I comfortably afford a new loan of ₹3,00,000?',
    'What should my financial priority be over the next 6 months?',
    'How do lenders evaluate my repayment sustainability?',
  ],
  [ADVISOR_CONTEXTS.HEALTH_SCORE]: [
    'How can I improve my Financial Health letter grade?',
    'Which sub-score is dragging down my overall score?',
    'What steps will take my score to an A+ rating?',
  ],
  [ADVISOR_CONTEXTS.FOIR_AFFORDABILITY]: [
    'Is my current FOIR ratio considered safe by commercial banks?',
    'How much additional monthly EMI can I prudently afford?',
    'Should I prepay existing loans or invest surplus cash?',
  ],
  [ADVISOR_CONTEXTS.RISK_ASSESSMENT]: [
    'What are the primary financial risk flags in my profile?',
    'Am I carrying too many fragmented active loans?',
    'How can I build stronger debt shock resilience?',
  ],
  [ADVISOR_CONTEXTS.LOAN_RECOMMENDATIONS]: [
    'Which loan type best matches my borrowing headroom?',
    'How does loan tenure impact my total interest outgo?',
    'Should I choose a personal loan or secure borrowing?',
  ],
  [ADVISOR_CONTEXTS.EMI_SIMULATION]: [
    'What happens to my disposable cash flow with a new ₹10,000 EMI?',
    'How much does loan tenure extension lower my monthly outgo?',
  ],
};

export const PromptSuggestions = ({ context = ADVISOR_CONTEXTS.GENERAL, onSelectPrompt, disabled = false }) => {
  const suggestions = SUGGESTIONS_BY_CONTEXT[context] || SUGGESTIONS_BY_CONTEXT[ADVISOR_CONTEXTS.GENERAL];

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
        <Sparkles className="w-3.5 h-3.5 text-brand-500" />
        <span>Suggested Questions ({context.replace('_', ' ').toLowerCase()}):</span>
      </div>
      <div className="flex flex-wrap gap-2">
        {suggestions.map((prompt, idx) => (
          <button
            key={idx}
            type="button"
            disabled={disabled}
            onClick={() => onSelectPrompt(prompt)}
            className="text-xs px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-brand-50 hover:text-brand-700 hover:border-brand-200 border border-slate-200 text-slate-700 transition-colors duration-150 text-left disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5 group"
          >
            <HelpCircle className="w-3 h-3 text-slate-400 group-hover:text-brand-500 shrink-0" />
            <span>{prompt}</span>
          </button>
        ))}
      </div>
    </div>
  );
};

export default PromptSuggestions;
