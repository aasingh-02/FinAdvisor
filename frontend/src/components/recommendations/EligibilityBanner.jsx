import React from 'react';
import { Card } from '../common/Card';
import { Badge } from '../common/Badge';
import { formatINR } from '../../utils/formatCurrency';
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  TrendingUp,
  ShieldAlert,
  ShieldCheck,
  Wallet,
  Clock,
  ArrowUpRight,
  Info,
} from 'lucide-react';

const RISK_BADGE_VARIANTS = {
  LOW: 'success',
  MODERATE: 'info',
  HIGH: 'warning',
  CRITICAL: 'danger',
};

export const EligibilityBanner = ({
  isEligible,
  summary,
  financialSnapshot,
  riskConsiderations,
  warnings = [],
}) => {
  if (!financialSnapshot) return null;

  const {
    monthly_net_income,
    existing_monthly_emi,
    monthly_expenses,
    emergency_savings,
    current_foir_percentage,
    configured_foir_threshold,
    disposable_monthly_income,
    prudent_max_monthly_emi,
    employment_type,
  } = financialSnapshot;

  const {
    overall_risk_category,
    overall_risk_score,
    emergency_fund_coverage_months,
    has_sufficient_emergency_fund,
    has_cash_deficit,
  } = riskConsiderations || {};

  const riskBadgeVariant = RISK_BADGE_VARIANTS[overall_risk_category] || 'neutral';

  return (
    <div className="space-y-4">
      {/* Primary Borrowing Capacity Banner */}
      <div
        className={`rounded-2xl border p-5 sm:p-6 transition-all ${
          isEligible
            ? 'bg-gradient-to-br from-emerald-500/10 via-emerald-50/50 to-white border-emerald-200/80 shadow-subtle'
            : 'bg-gradient-to-br from-amber-500/10 via-rose-50/40 to-white border-amber-200/80 shadow-subtle'
        }`}
      >
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-start gap-3.5">
            <div
              className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 shadow-sm ${
                isEligible
                  ? 'bg-emerald-600 text-white shadow-emerald-500/20'
                  : 'bg-amber-600 text-white shadow-amber-500/20'
              }`}
            >
              {isEligible ? (
                <CheckCircle2 className="w-6 h-6" />
              ) : (
                <AlertTriangle className="w-6 h-6" />
              )}
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-lg font-bold text-slate-900">
                  {isEligible
                    ? 'Eligible for Borrowing'
                    : 'Borrowing Caution / Limited Headroom'}
                </h2>
                <Badge variant={isEligible ? 'success' : 'warning'} size="sm">
                  {isEligible ? 'Approved Headroom' : 'Constrained'}
                </Badge>
                {employment_type && (
                  <Badge variant="neutral" size="sm">
                    {employment_type}
                  </Badge>
                )}
              </div>
              <p className="text-sm text-slate-600 mt-1 leading-relaxed max-w-2xl">
                {summary}
              </p>
            </div>
          </div>

          {/* Prudent Max EMI Highlight */}
          <div className="bg-white/80 backdrop-blur rounded-xl border border-slate-200/80 p-4 shrink-0 text-left md:text-right min-w-[220px]">
            <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Prudent Monthly EMI Capacity
            </div>
            <div className="text-2xl font-extrabold text-slate-900 mt-1">
              {formatINR(prudent_max_monthly_emi, true)}
              <span className="text-xs font-normal text-slate-500 ml-1">/ month</span>
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">
              Under {configured_foir_threshold}% FOIR benchmark with cash buffer
            </div>
          </div>
        </div>

        {/* Snapshot Metrics Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-5 pt-4 border-t border-slate-200/60">
          <div className="p-3 bg-white/70 rounded-xl border border-slate-200/60">
            <div className="text-[11px] font-medium text-slate-500 flex items-center gap-1">
              <Wallet className="w-3.5 h-3.5 text-slate-400" />
              Net Income
            </div>
            <div className="text-sm font-bold text-slate-900 mt-0.5">
              {formatINR(monthly_net_income)}
            </div>
            <div className="text-[10px] text-slate-500">Per month</div>
          </div>

          <div className="p-3 bg-white/70 rounded-xl border border-slate-200/60">
            <div className="text-[11px] font-medium text-slate-500 flex items-center gap-1">
              <TrendingUp className="w-3.5 h-3.5 text-slate-400" />
              Current FOIR
            </div>
            <div className="text-sm font-bold text-slate-900 mt-0.5">
              {parseFloat(current_foir_percentage).toFixed(1)}%
            </div>
            <div className="text-[10px] text-slate-500">
              Existing EMIs: {formatINR(existing_monthly_emi)}
            </div>
          </div>

          <div className="p-3 bg-white/70 rounded-xl border border-slate-200/60">
            <div className="text-[11px] font-medium text-slate-500 flex items-center gap-1">
              <ArrowUpRight className="w-3.5 h-3.5 text-slate-400" />
              Disposable Cash Flow
            </div>
            <div
              className={`text-sm font-bold mt-0.5 ${
                has_cash_deficit ? 'text-rose-600' : 'text-slate-900'
              }`}
            >
              {formatINR(disposable_monthly_income)}
            </div>
            <div className="text-[10px] text-slate-500">
              Living costs: {formatINR(monthly_expenses)}
            </div>
          </div>

          <div className="p-3 bg-white/70 rounded-xl border border-slate-200/60">
            <div className="text-[11px] font-medium text-slate-500 flex items-center gap-1">
              <Clock className="w-3.5 h-3.5 text-slate-400" />
              Emergency Fund
            </div>
            <div className="text-sm font-bold text-slate-900 mt-0.5">
              {emergency_fund_coverage_months
                ? `${parseFloat(emergency_fund_coverage_months).toFixed(1)} mos`
                : '0.0 mos'}
            </div>
            <div className="text-[10px] text-slate-500">
              Reserves: {formatINR(emergency_savings)}
            </div>
          </div>
        </div>

        {/* Risk Assessment Tier Pill */}
        {riskConsiderations && (
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2 px-3 py-2 bg-slate-100/70 rounded-lg text-xs text-slate-600">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-700">Financial Risk Profile:</span>
              <Badge variant={riskBadgeVariant} size="sm">
                {overall_risk_category} RISK
              </Badge>
              {overall_risk_score !== undefined && (
                <span className="text-slate-500">
                  (Risk Score: {parseFloat(overall_risk_score).toFixed(0)}/100)
                </span>
              )}
            </div>
            {!has_sufficient_emergency_fund && (
              <span className="text-amber-700 flex items-center gap-1 font-medium">
                <AlertTriangle className="w-3.5 h-3.5" />
                Emergency liquidity &lt; 3 months buffer applied
              </span>
            )}
          </div>
        )}
      </div>

      {/* Advisory Warnings / Considerations */}
      {warnings && warnings.length > 0 && (
        <div className="p-4 rounded-xl bg-amber-50/70 border border-amber-200/90 text-amber-900 space-y-2">
          <div className="flex items-center gap-2 font-semibold text-xs uppercase tracking-wider text-amber-800">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
            Advisory Considerations & Warnings ({warnings.length})
          </div>
          <ul className="space-y-1.5 pl-6 text-xs text-amber-900/90 list-disc">
            {warnings.map((warn, index) => (
              <li key={index} className="leading-relaxed">
                {warn}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default EligibilityBanner;
