/**
 * frontend/src/components/calculator/FOIRBreakdown.jsx
 * ────────────────────────────────────────────────────
 * Detailed financial metrics breakdown component for FOIR & borrowing capacity.
 *
 * Displays:
 * - Summary metric cards (Monthly Net Income, Existing EMI, Max Permissible EMI, Additional Capacity)
 * - Remaining income after expenses and EMIs (with cash-deficit indicator if negative)
 * - Proportional allocation progress bar (Existing EMI, Expenses, Remaining Disposable)
 * - Explanatory message from backend distinguishing policy threshold from lender underwriting
 */

import React from 'react';
import { Card } from '../common/Card';
import { Badge } from '../common/Badge';
import { formatINR } from '../../utils/formatCurrency';
import {
  IndianRupee,
  ShieldCheck,
  TrendingUp,
  Wallet,
  CreditCard,
  PiggyBank,
  AlertTriangle,
  Info,
} from 'lucide-react';

export const FOIRBreakdown = ({ data }) => {
  if (!data) return null;

  const income = parseFloat(data.monthly_net_income) || 0;
  const existingEmi = parseFloat(data.existing_monthly_emi) || 0;
  const expenses = parseFloat(data.monthly_expenses) || 0;
  const savings = parseFloat(data.emergency_savings) || 0;
  const maxEmi = parseFloat(data.maximum_permissible_emi) || 0;
  const additionalCapacity = parseFloat(data.additional_emi_capacity) || 0;
  const remainingIncome = parseFloat(data.remaining_income_after_expenses_and_emi) || 0;
  const currentFoir = parseFloat(data.current_foir_percentage) || 0;
  const threshold = parseFloat(data.configured_foir_threshold) || 40;

  // Calculate proportional percentages of net income for the visual distribution bar
  const emiPct = income > 0 ? Math.min(100, (existingEmi / income) * 100) : 0;
  const expPct = income > 0 ? Math.min(100 - emiPct, (expenses / income) * 100) : 0;
  const remPct = Math.max(0, 100 - emiPct - expPct);

  const isDeficit = remainingIncome < 0;

  return (
    <div className="space-y-5">
      {/* 4 Core Financial Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* 1. Monthly Net Income */}
        <div className="p-4 rounded-xl bg-white border border-slate-200/90 shadow-subtle relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">
              Monthly Net Income
            </span>
            <div className="p-1.5 rounded-lg bg-slate-50 text-slate-600">
              <Wallet className="w-4 h-4" />
            </div>
          </div>
          <div className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight">
            {formatINR(income, true)}
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Verified take-home earnings</p>
        </div>

        {/* 2. Existing Monthly EMI Obligations */}
        <div className="p-4 rounded-xl bg-white border border-slate-200/90 shadow-subtle relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">
              Existing Monthly EMI
            </span>
            <div className="p-1.5 rounded-lg bg-amber-50 text-amber-600">
              <CreditCard className="w-4 h-4" />
            </div>
          </div>
          <div className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight">
            {formatINR(existingEmi, true)}
          </div>
          <p className="text-[11px] text-amber-700 font-medium mt-1">
            Consumes {currentFoir.toFixed(1)}% of net income
          </p>
        </div>

        {/* 3. Maximum Permissible EMI */}
        <div className="p-4 rounded-xl bg-white border border-slate-200/90 shadow-subtle relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">
              Max Permissible EMI
            </span>
            <div className="p-1.5 rounded-lg bg-brand-50 text-brand-600">
              <ShieldCheck className="w-4 h-4" />
            </div>
          </div>
          <div className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight">
            {formatINR(maxEmi, true)}
          </div>
          <p className="text-[11px] text-slate-500 mt-1">
            Capped at {threshold}% policy threshold
          </p>
        </div>

        {/* 4. Additional EMI Headroom */}
        <div
          className={`p-4 rounded-xl border shadow-subtle relative overflow-hidden ${
            additionalCapacity > 0
              ? 'bg-emerald-50/60 border-emerald-200/80 text-emerald-950'
              : 'bg-rose-50/60 border-rose-200/80 text-rose-950'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">
              Additional EMI Capacity
            </span>
            <div
              className={`p-1.5 rounded-lg ${
                additionalCapacity > 0 ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'
              }`}
            >
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <div className="text-xl sm:text-2xl font-extrabold tracking-tight">
            {formatINR(additionalCapacity, true)}
          </div>
          <p
            className={`text-[11px] font-medium mt-1 ${
              additionalCapacity > 0 ? 'text-emerald-700' : 'text-rose-700'
            }`}
          >
            {additionalCapacity > 0
              ? 'Safe headroom for new borrowing'
              : 'Exceeds configured policy capacity'}
          </p>
        </div>
      </div>

      {/* Income Allocation Distribution Bar */}
      <Card
        title="Monthly Cash Flow Allocation"
        subtitle="Distribution of net income across existing EMIs, household expenses, and remaining disposable cash"
      >
        <div className="space-y-4">
          {/* Multi-segment Progress Bar */}
          <div className="h-4 w-full bg-slate-100 rounded-full overflow-hidden flex shadow-inner">
            {emiPct > 0 && (
              <div
                style={{ width: `${emiPct}%` }}
                className="bg-amber-500 transition-all duration-500"
                title={`Existing EMIs: ${emiPct.toFixed(1)}%`}
              />
            )}
            {expPct > 0 && (
              <div
                style={{ width: `${expPct}%` }}
                className="bg-slate-400 transition-all duration-500"
                title={`Household Expenses: ${expPct.toFixed(1)}%`}
              />
            )}
            {remPct > 0 && (
              <div
                style={{ width: `${remPct}%` }}
                className="bg-emerald-500 transition-all duration-500"
                title={`Remaining Disposable: ${remPct.toFixed(1)}%`}
              />
            )}
          </div>

          {/* Allocation Legend */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1 text-xs">
            <div className="flex items-center justify-between p-2.5 rounded-lg bg-amber-50/70 border border-amber-200/60">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500 shrink-0" />
                <span className="font-medium text-amber-900">Existing EMIs</span>
              </div>
              <span className="font-bold text-amber-950">{formatINR(existingEmi, true)}</span>
            </div>

            <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-50 border border-slate-200/80">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-slate-400 shrink-0" />
                <span className="font-medium text-slate-700">Living Expenses</span>
              </div>
              <span className="font-bold text-slate-900">{formatINR(expenses, true)}</span>
            </div>

            <div
              className={`flex items-center justify-between p-2.5 rounded-lg border ${
                isDeficit
                  ? 'bg-rose-50 border-rose-200 text-rose-950'
                  : 'bg-emerald-50/70 border-emerald-200/60 text-emerald-950'
              }`}
            >
              <div className="flex items-center gap-2">
                <span
                  className={`w-2.5 h-2.5 rounded-full shrink-0 ${
                    isDeficit ? 'bg-rose-500' : 'bg-emerald-500'
                  }`}
                />
                <span className="font-medium">
                  {isDeficit ? 'Monthly Cash Deficit' : 'Remaining Disposable'}
                </span>
              </div>
              <span className="font-bold">{formatINR(remainingIncome, true)}</span>
            </div>
          </div>

          {/* Emergency Savings Notice */}
          <div className="flex items-center justify-between text-xs p-3 rounded-lg bg-blue-50/50 border border-blue-100 text-blue-900">
            <div className="flex items-center gap-2">
              <PiggyBank className="w-4 h-4 text-blue-600 shrink-0" />
              <span>
                Reported Liquid Emergency Reserve: <strong>{formatINR(savings, true)}</strong>
              </span>
            </div>
            <span className="text-[11px] text-blue-700 font-medium">
              {income > 0 ? `${(savings / income).toFixed(1)} months income reserve` : ''}
            </span>
          </div>
        </div>
      </Card>

      {/* Backend Explanatory Message Banner */}
      {data.explanatory_message && (
        <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/90 text-xs text-slate-700 space-y-1.5">
          <div className="flex items-center gap-1.5 font-bold text-slate-900">
            <Info className="w-4 h-4 text-brand-600 shrink-0" />
            <span>Advisory Analysis & Underwriting Context</span>
          </div>
          <p className="leading-relaxed text-slate-600">{data.explanatory_message}</p>
        </div>
      )}
    </div>
  );
};

export default FOIRBreakdown;
