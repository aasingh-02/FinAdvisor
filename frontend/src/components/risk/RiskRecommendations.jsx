/**
 * frontend/src/components/risk/RiskRecommendations.jsx
 * ────────────────────────────────────────────────────
 * Actionable advisory recommendations component rendering suggestions
 * produced exclusively by the FastAPI backend advisory engine.
 */

import React from 'react';
import { Card } from '../common/Card';
import { Badge } from '../common/Badge';
import {
  Lightbulb,
  ArrowRight,
  AlertTriangle,
  AlertOctagon,
  Info,
  CheckCircle2,
  Sparkles,
} from 'lucide-react';

const PRIORITY_CONFIG = {
  CRITICAL: {
    badgeVariant: 'danger',
    colorBg: 'bg-rose-50',
    colorText: 'text-rose-700',
    borderColor: 'border-rose-200',
    actionBg: 'bg-rose-50/70',
    actionBorder: 'border-rose-200',
    icon: AlertOctagon,
  },
  HIGH: {
    badgeVariant: 'warning',
    colorBg: 'bg-amber-50',
    colorText: 'text-amber-700',
    borderColor: 'border-amber-200',
    actionBg: 'bg-amber-50/70',
    actionBorder: 'border-amber-200',
    icon: AlertTriangle,
  },
  MEDIUM: {
    badgeVariant: 'info',
    colorBg: 'bg-sky-50',
    colorText: 'text-sky-700',
    borderColor: 'border-sky-200',
    actionBg: 'bg-sky-50/70',
    actionBorder: 'border-sky-200',
    icon: Info,
  },
  LOW: {
    badgeVariant: 'success',
    colorBg: 'bg-emerald-50',
    colorText: 'text-emerald-700',
    borderColor: 'border-emerald-200',
    actionBg: 'bg-emerald-50/70',
    actionBorder: 'border-emerald-200',
    icon: CheckCircle2,
  },
};

export const RiskRecommendations = ({ recommendations = [] }) => {
  if (!recommendations || recommendations.length === 0) {
    return (
      <Card
        title="Personalized Advisory Recommendations"
        subtitle="Data-driven suggestions to optimize your debt ratio and borrowing capacity"
      >
        <div className="py-8 text-center text-slate-500 text-xs">
          No active financial alerts. Your current obligations and reserves reflect a balanced profile.
        </div>
      </Card>
    );
  }

  return (
    <Card
      title="Personalized Advisory Recommendations"
      subtitle="Data-driven guidance derived from your verified debt obligations and liquidity"
      headerAction={
        <div className="flex items-center gap-1.5 text-xs text-brand-600 font-semibold bg-brand-50 px-2.5 py-1 rounded-lg border border-brand-100">
          <Sparkles className="w-3.5 h-3.5" />
          <span>{recommendations.length} Action Items</span>
        </div>
      }
    >
      <div className="space-y-4">
        {recommendations.map((rec, idx) => {
          const priority = rec.priority || 'MEDIUM';
          const config = PRIORITY_CONFIG[priority] || PRIORITY_CONFIG.MEDIUM;
          const PriorityIcon = config.icon;

          return (
            <div
              key={idx}
              className="p-4 rounded-xl border border-slate-200/90 bg-white hover:border-slate-300 transition-all shadow-subtle space-y-3"
            >
              {/* Header: Title, Priority Badge & Related Category */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded-lg bg-brand-50 text-brand-700">
                    <Lightbulb className="w-4 h-4" />
                  </div>
                  <h4 className="text-sm font-bold text-slate-900 tracking-tight">
                    {rec.title}
                  </h4>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono uppercase font-semibold text-slate-400 bg-slate-100 px-2 py-0.5 rounded">
                    {rec.related_indicator}
                  </span>
                  <span
                    className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold border ${config.colorBg} ${config.colorText} ${config.borderColor}`}
                  >
                    <PriorityIcon className="w-3 h-3" />
                    <span>{priority} Priority</span>
                  </span>
                </div>
              </div>

              {/* Context Explanation */}
              <p className="text-xs text-slate-600 leading-relaxed pl-1">
                {rec.explanation}
              </p>

              {/* Actionable Recommendation Box */}
              <div
                className={`p-3 rounded-lg border text-xs text-slate-800 space-y-1 ${config.actionBg} ${config.actionBorder}`}
              >
                <div className="flex items-center gap-1.5 font-bold text-slate-900">
                  <ArrowRight className="w-3.5 h-3.5 text-brand-600 shrink-0" />
                  <span>Suggested Action:</span>
                </div>
                <p className="leading-relaxed pl-5 text-slate-700">
                  {rec.suggested_action}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
};

export default RiskRecommendations;
