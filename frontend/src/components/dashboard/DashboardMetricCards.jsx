import React from 'react';
import { StatCard } from './StatCard';
import {
  IndianRupee,
  CreditCard,
  PieChart,
  Wallet,
  TrendingUp,
  TrendingDown,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import { formatINR } from '../../utils/formatCurrency';

export const DashboardMetricCards = ({ metrics, currentFoir }) => {
  if (!metrics) return null;

  const income = parseFloat(metrics.monthly_net_income || 0);
  const loansCount = parseInt(metrics.total_active_loans || 0, 10);
  const emiBurden = parseFloat(metrics.monthly_emi_burden || 0);
  const expenses = parseFloat(metrics.monthly_living_expenses || 0);
  const disposable = parseFloat(metrics.disposable_monthly_cash_flow || 0);
  const emergencyMonths = parseFloat(metrics.emergency_fund_months || 0);
  const emergencyTotal = parseFloat(metrics.emergency_savings_total || 0);
  const prudentEmi = parseFloat(metrics.prudent_max_monthly_emi || 0);
  const foirNum = parseFloat(currentFoir || 0);

  const isSurplus = disposable >= 0;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
      {/* 1. Monthly Net Income */}
      <StatCard
        title="Monthly Net Income"
        value={formatINR(income, false)}
        subtext="Take-home earnings after deductions"
        icon={IndianRupee}
        iconColor="text-brand-600 bg-brand-50 border-brand-100"
      />

      {/* 2. Total Active Loans */}
      <StatCard
        title="Total Active Loans"
        value={`${loansCount} Active Loan${loansCount === 1 ? '' : 's'}`}
        subtext={loansCount === 0 ? 'Zero active debt accounts' : 'Existing credit accounts'}
        icon={CreditCard}
        iconColor="text-indigo-600 bg-indigo-50 border-indigo-100"
      />

      {/* 3. Monthly EMI Burden */}
      <StatCard
        title="Monthly EMI Burden"
        value={formatINR(emiBurden, false)}
        subtext={`${foirNum.toFixed(1)}% FOIR fixed obligation ratio`}
        icon={PieChart}
        iconColor={
          foirNum <= 30
            ? 'text-emerald-600 bg-emerald-50 border-emerald-100'
            : foirNum <= 50
            ? 'text-amber-600 bg-amber-50 border-amber-100'
            : 'text-rose-600 bg-rose-50 border-rose-100'
        }
        changeText={foirNum <= 40 ? 'Within Safe Limits' : 'Above Benchmark'}
        changeType={foirNum <= 40 ? 'positive' : 'negative'}
      />

      {/* 4. Essential Living Expenses */}
      <StatCard
        title="Monthly Living Expenses"
        value={formatINR(expenses, false)}
        subtext="Regular essential household costs"
        icon={Wallet}
        iconColor="text-slate-600 bg-slate-100 border-slate-200"
      />

      {/* 5. Disposable Monthly Cash Flow */}
      <StatCard
        title="Disposable Cash Flow"
        value={formatINR(disposable, false)}
        subtext={isSurplus ? 'Monthly uncommitted surplus cash' : 'Monthly cash flow deficit'}
        icon={isSurplus ? TrendingUp : TrendingDown}
        iconColor={
          isSurplus
            ? 'text-emerald-600 bg-emerald-50 border-emerald-100'
            : 'text-rose-600 bg-rose-50 border-rose-100'
        }
        changeText={isSurplus ? 'Positive Cash Flow' : 'Deficit Detected'}
        changeType={isSurplus ? 'positive' : 'negative'}
      />

      {/* 6. Emergency Fund Coverage */}
      <StatCard
        title="Emergency Fund Coverage"
        value={`${emergencyMonths.toFixed(1)} Months`}
        subtext={`Total savings: ${formatINR(emergencyTotal, false)}`}
        icon={ShieldCheck}
        iconColor={
          emergencyMonths >= 6
            ? 'text-emerald-600 bg-emerald-50 border-emerald-100'
            : emergencyMonths >= 3
            ? 'text-blue-600 bg-blue-50 border-blue-100'
            : 'text-amber-600 bg-amber-50 border-amber-100'
        }
        changeText={emergencyMonths >= 3 ? 'Adequate Buffer' : 'Build to 6 Months'}
        changeType={emergencyMonths >= 3 ? 'positive' : 'neutral'}
      />

      {/* 7. Prudent Max Borrowing EMI */}
      <div className="sm:col-span-2">
        <StatCard
          title="Prudent Max Borrowing EMI"
          value={formatINR(prudentEmi, false)}
          subtext="Recommended ceiling for new monthly loan repayments after safety buffers"
          icon={Sparkles}
          iconColor="text-brand-600 bg-brand-50 border-brand-100"
          changeText={prudentEmi > 0 ? 'Borrowing Capacity Available' : 'Zero Capacity Available'}
          changeType={prudentEmi > 0 ? 'positive' : 'negative'}
        />
      </div>
    </div>
  );
};

export default DashboardMetricCards;
