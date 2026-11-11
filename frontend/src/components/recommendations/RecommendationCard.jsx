import React from 'react';
import { Card } from '../common/Card';
import { Badge } from '../common/Badge';
import { formatINR } from '../../utils/formatCurrency';
import {
  Home,
  Car,
  GraduationCap,
  Briefcase,
  Percent,
  Calendar,
  Layers,
  Sparkles,
  ArrowRight,
  TrendingUp,
  CreditCard,
  FileText,
} from 'lucide-react';

const CATEGORY_ICONS = {
  PERSONAL_LOAN: Briefcase,
  HOME_LOAN: Home,
  VEHICLE_LOAN: Car,
  EDUCATION_LOAN: GraduationCap,
};

const CATEGORY_COLORS = {
  PERSONAL_LOAN: {
    bg: 'bg-indigo-50',
    text: 'text-indigo-600',
    border: 'border-indigo-100',
    badge: 'info',
  },
  HOME_LOAN: {
    bg: 'bg-emerald-50',
    text: 'text-emerald-600',
    border: 'border-emerald-100',
    badge: 'success',
  },
  VEHICLE_LOAN: {
    bg: 'bg-amber-50',
    text: 'text-amber-600',
    border: 'border-amber-100',
    badge: 'warning',
  },
  EDUCATION_LOAN: {
    bg: 'bg-sky-50',
    text: 'text-sky-600',
    border: 'border-sky-100',
    badge: 'info',
  },
};

const AFFORDABILITY_BADGES = {
  Optimal: 'success',
  Manageable: 'info',
  Stretched: 'warning',
  High: 'danger',
};

export const RecommendationCard = ({ recommendation, onOpenSchedule }) => {
  if (!recommendation) return null;

  const {
    loan_category,
    category_display_name,
    recommended_principal,
    assumed_annual_interest_rate,
    suggested_tenure_months,
    estimated_monthly_emi,
    total_interest_payable,
    total_repayment,
    projected_foir_percentage,
    affordability_classification,
    suitability_reason,
  } = recommendation;

  const Icon = CATEGORY_ICONS[loan_category] || CreditCard;
  const colors = CATEGORY_COLORS[loan_category] || {
    bg: 'bg-slate-50',
    text: 'text-slate-600',
    border: 'border-slate-100',
    badge: 'neutral',
  };

  const tenureYears = (suggested_tenure_months / 12).toFixed(suggested_tenure_months % 12 === 0 ? 0 : 1);
  const affordBadge = AFFORDABILITY_BADGES[affordability_classification] || 'neutral';
  const foirNum = parseFloat(projected_foir_percentage);

  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 hover:border-brand-300 hover:shadow-subtle transition-all overflow-hidden flex flex-col justify-between group">
      {/* Top Header */}
      <div>
        <div className="p-5 border-b border-slate-100 flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div
              className={`w-11 h-11 rounded-xl flex items-center justify-center shrink-0 border ${colors.bg} ${colors.text} ${colors.border}`}
            >
              <Icon className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900 group-hover:text-brand-600 transition-colors">
                {category_display_name}
              </h3>
              <div className="text-xs text-slate-500 flex items-center gap-2 mt-0.5">
                <span>{assumed_annual_interest_rate}% p.a.</span>
                <span>•</span>
                <span>{suggested_tenure_months} mos ({tenureYears} yrs)</span>
              </div>
            </div>
          </div>

          <Badge variant={affordBadge} size="sm">
            {affordability_classification}
          </Badge>
        </div>

        {/* Body Metrics */}
        <div className="p-5 space-y-4">
          {/* Recommended Principal (Hero figure) */}
          <div className="p-4 rounded-xl bg-slate-50/80 border border-slate-200/70">
            <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
              Recommended Sustainable Principal
            </div>
            <div className="text-2xl sm:text-3xl font-extrabold text-slate-900 mt-1">
              {formatINR(recommended_principal)}
            </div>
          </div>

          {/* Key Loan Specifications Grid */}
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="p-3 bg-slate-50/50 rounded-lg border border-slate-100">
              <span className="text-slate-500 font-medium block">Monthly EMI</span>
              <span className="text-base font-bold text-brand-600 block mt-0.5">
                {formatINR(estimated_monthly_emi, true)}
              </span>
            </div>

            <div className="p-3 bg-slate-50/50 rounded-lg border border-slate-100">
              <span className="text-slate-500 font-medium block">Total Interest</span>
              <span className="text-sm font-bold text-slate-700 block mt-0.5">
                {formatINR(total_interest_payable, true)}
              </span>
            </div>

            <div className="p-3 bg-slate-50/50 rounded-lg border border-slate-100 col-span-2 flex items-center justify-between">
              <span className="text-slate-500 font-medium">Total Repayment:</span>
              <span className="text-sm font-extrabold text-slate-900">
                {formatINR(total_repayment, true)}
              </span>
            </div>
          </div>

          {/* Projected FOIR Bar */}
          <div className="space-y-1.5 pt-1">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-500 font-medium">Projected Total FOIR:</span>
              <span
                className={`font-bold ${
                  foirNum <= 40 ? 'text-emerald-600' : foirNum <= 50 ? 'text-amber-600' : 'text-rose-600'
                }`}
              >
                {foirNum.toFixed(2)}%
              </span>
            </div>
            <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-500 ${
                  foirNum <= 40
                    ? 'bg-emerald-500'
                    : foirNum <= 50
                    ? 'bg-amber-500'
                    : 'bg-rose-500'
                }`}
                style={{ width: `${Math.min(foirNum, 100)}%` }}
              />
            </div>
          </div>

          {/* Contextual Suitability Reason */}
          <div className="p-3 bg-brand-50/30 rounded-xl border border-brand-100 text-xs text-slate-600 leading-relaxed">
            <div className="font-semibold text-brand-900 flex items-center gap-1.5 mb-1">
              <Sparkles className="w-3.5 h-3.5 text-brand-600 shrink-0" />
              Affordability Context
            </div>
            {suitability_reason}
          </div>
        </div>
      </div>

      {/* Footer Actions */}
      <div className="p-4 bg-slate-50/70 border-t border-slate-100 flex items-center justify-between gap-2">
        <button
          type="button"
          onClick={() => onOpenSchedule && onOpenSchedule(recommendation)}
          className="w-full inline-flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-semibold text-brand-700 bg-white hover:bg-brand-50 border border-brand-200 rounded-lg shadow-sm transition-all"
        >
          <FileText className="w-3.5 h-3.5" />
          View Amortization Schedule
        </button>
      </div>
    </div>
  );
};

export default RecommendationCard;
