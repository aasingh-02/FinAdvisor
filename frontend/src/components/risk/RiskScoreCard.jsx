/**
 * frontend/src/components/risk/RiskScoreCard.jsx
 * ──────────────────────────────────────────────
 * Executive risk summary component displaying overall risk score,
 * classification tier, summary narrative, and statutory compliance disclaimer.
 */

import React from 'react';
import { Card } from '../common/Card';
import { Badge } from '../common/Badge';
import { formatINR } from '../../utils/formatCurrency';
import {
  ShieldCheck,
  AlertTriangle,
  AlertOctagon,
  Info,
  TrendingDown,
  TrendingUp,
  CreditCard,
  PiggyBank,
  Wallet,
  Scale,
} from 'lucide-react';

const CATEGORY_STYLES = {
  LOW: {
    label: 'Low Risk',
    badgeVariant: 'success',
    colorText: 'text-emerald-700',
    colorBg: 'bg-emerald-50',
    borderColor: 'border-emerald-200',
    accentBar: 'bg-emerald-500',
    icon: ShieldCheck,
    description: 'Conservative debt ratio, sound emergency reserves, and reliable cash buffer.',
  },
  MODERATE: {
    label: 'Moderate Risk',
    badgeVariant: 'info',
    colorText: 'text-sky-700',
    colorBg: 'bg-sky-50',
    borderColor: 'border-sky-200',
    accentBar: 'bg-sky-500',
    icon: Info,
    description: 'Balanced financial commitments; emergency cushion or disposable margin warrant attention.',
  },
  HIGH: {
    label: 'High Risk',
    badgeVariant: 'warning',
    colorText: 'text-amber-700',
    colorBg: 'bg-amber-50',
    borderColor: 'border-amber-200',
    accentBar: 'bg-amber-500',
    icon: AlertTriangle,
    description: 'Elevated debt obligations relative to policy limits or constrained liquidity.',
  },
  CRITICAL: {
    label: 'Critical Risk',
    badgeVariant: 'danger',
    colorText: 'text-rose-700',
    colorBg: 'bg-rose-50',
    borderColor: 'border-rose-200',
    accentBar: 'bg-rose-500',
    icon: AlertOctagon,
    description: 'Severe strain: active cash flow deficit, extreme FOIR, or depleted emergency savings.',
  },
};

export const RiskScoreCard = ({ data }) => {
  if (!data) return null;

  const score = parseFloat(data.overall_risk_score) || 0;
  const category = data.overall_risk_category || 'LOW';
  const style = CATEGORY_STYLES[category] || CATEGORY_STYLES.LOW;
  const CategoryIcon = style.icon;

  const income = parseFloat(data.monthly_net_income) || 0;
  const emi = parseFloat(data.existing_monthly_emi) || 0;
  const foir = parseFloat(data.foir_percentage || data.current_foir_percentage) || 0;
  const coverage = parseFloat(data.emergency_fund_coverage_months) || 0;
  const disposable = parseFloat(data.disposable_monthly_income) || 0;

  return (
    <Card className="overflow-hidden border border-slate-200/90 shadow-card">
      <div className="space-y-6">
        {/* Top Header & Main Score Section */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 pb-6 border-b border-slate-100">
          {/* Left: Category & Explanation */}
          <div className="space-y-2 max-w-xl">
            <div className="flex items-center gap-2.5">
              <span
                className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold border ${style.colorBg} ${style.colorText} ${style.borderColor}`}
              >
                <CategoryIcon className="w-4 h-4" />
                <span>{style.label}</span>
              </span>
              <span className="text-xs text-slate-400 font-medium">
                Deterministic Underwriting Score
              </span>
            </div>

            <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900">
              Personal Financial Health Assessment
            </h2>

            <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
              {data.summary_message || style.description}
            </p>
          </div>

          {/* Right: Circular Score Gauge / Metric Banner */}
          <div className="flex items-center gap-4 p-4 rounded-2xl bg-slate-50 border border-slate-200/80 self-start md:self-auto min-w-[210px] justify-between">
            <div>
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 block">
                Composite Risk Score
              </span>
              <div className="flex items-baseline gap-1 mt-0.5">
                <span className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
                  {score.toFixed(1)}
                </span>
                <span className="text-xs font-bold text-slate-400">/ 100</span>
              </div>
              <span className="text-[10px] text-slate-400 font-medium">
                0 = Safe | 100 = Critical
              </span>
            </div>

            {/* Visual Risk Level Icon Pod */}
            <div
              className={`w-14 h-14 rounded-2xl flex items-center justify-center border shadow-subtle ${style.colorBg} ${style.borderColor} ${style.colorText}`}
            >
              <CategoryIcon className="w-7 h-7" />
            </div>
          </div>
        </div>

        {/* Linear Score Bar with Zone Dividers */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-[11px] text-slate-500 font-semibold">
            <span>Risk Continuum</span>
            <span>Current Position: {score.toFixed(1)}%</span>
          </div>

          <div className="relative h-3 w-full bg-slate-100 rounded-full overflow-hidden flex shadow-inner">
            <div className="w-[25%] bg-emerald-500/20 border-r border-white/60" title="Low: 0-25" />
            <div className="w-[25%] bg-sky-500/20 border-r border-white/60" title="Moderate: 26-50" />
            <div className="w-[25%] bg-amber-500/20 border-r border-white/60" title="High: 51-75" />
            <div className="w-[25%] bg-rose-500/20" title="Critical: 76-100" />

            {/* Filled Progress Indicator up to score */}
            <div
              style={{ width: `${Math.min(100, score)}%` }}
              className={`absolute inset-y-0 left-0 transition-all duration-700 ease-out ${style.accentBar} opacity-90`}
            />
          </div>

          <div className="flex justify-between text-[10px] font-medium text-slate-400 pt-0.5 px-0.5">
            <span>Low (0 - 25)</span>
            <span>Moderate (26 - 50)</span>
            <span>High (51 - 75)</span>
            <span>Critical (&gt; 75)</span>
          </div>
        </div>

        {/* 5 Core Metric Cards Quick Row */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 pt-2">
          {/* 1. Monthly Net Income */}
          <div className="p-3 rounded-xl bg-white border border-slate-200/80 shadow-subtle">
            <div className="flex items-center justify-between text-slate-400 mb-1">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                Income
              </span>
              <Wallet className="w-3.5 h-3.5 text-slate-400" />
            </div>
            <div className="text-sm font-bold text-slate-900">
              {formatINR(income, true)}
            </div>
            <span className="text-[10px] text-slate-400">Net monthly</span>
          </div>

          {/* 2. Existing EMI */}
          <div className="p-3 rounded-xl bg-white border border-slate-200/80 shadow-subtle">
            <div className="flex items-center justify-between text-slate-400 mb-1">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                Fixed EMI
              </span>
              <CreditCard className="w-3.5 h-3.5 text-slate-400" />
            </div>
            <div className="text-sm font-bold text-slate-900">
              {formatINR(emi, true)}
            </div>
            <span className="text-[10px] text-slate-400">Monthly debt</span>
          </div>

          {/* 3. Current FOIR */}
          <div className="p-3 rounded-xl bg-white border border-slate-200/80 shadow-subtle">
            <div className="flex items-center justify-between text-slate-400 mb-1">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                FOIR Ratio
              </span>
              <Scale className="w-3.5 h-3.5 text-slate-400" />
            </div>
            <div className="text-sm font-bold text-slate-900">
              {foir.toFixed(1)}%
            </div>
            <span className="text-[10px] text-slate-400">
              Limit: {parseFloat(data.configured_foir_threshold || 40)}%
            </span>
          </div>

          {/* 4. Emergency Reserve */}
          <div className="p-3 rounded-xl bg-white border border-slate-200/80 shadow-subtle">
            <div className="flex items-center justify-between text-slate-400 mb-1">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                Emergency Buffer
              </span>
              <PiggyBank className="w-3.5 h-3.5 text-slate-400" />
            </div>
            <div className="text-sm font-bold text-slate-900">
              {coverage.toFixed(1)} mos
            </div>
            <span className="text-[10px] text-slate-400">Target: 3–6 mos</span>
          </div>

          {/* 5. Disposable Income */}
          <div
            className={`p-3 rounded-xl border shadow-subtle col-span-2 sm:col-span-1 ${
              disposable < 0
                ? 'bg-rose-50/70 border-rose-200 text-rose-950'
                : 'bg-white border-slate-200/80 text-slate-900'
            }`}
          >
            <div className="flex items-center justify-between text-slate-400 mb-1">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                Disposable
              </span>
              {disposable < 0 ? (
                <TrendingDown className="w-3.5 h-3.5 text-rose-600" />
              ) : (
                <TrendingUp className="w-3.5 h-3.5 text-emerald-600" />
              )}
            </div>
            <div className={`text-sm font-bold ${disposable < 0 ? 'text-rose-700' : 'text-slate-900'}`}>
              {formatINR(disposable, true)}
            </div>
            <span className={`text-[10px] ${disposable < 0 ? 'text-rose-600 font-semibold' : 'text-slate-400'}`}>
              {disposable < 0 ? 'Cash Deficit' : 'Monthly buffer'}
            </span>
          </div>
        </div>

        {/* Disclaimer Banner */}
        {data.assessment_disclaimer && (
          <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/70 text-[11px] text-slate-500 leading-relaxed flex items-start gap-2">
            <Info className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
            <span>{data.assessment_disclaimer}</span>
          </div>
        )}
      </div>
    </Card>
  );
};

export default RiskScoreCard;
