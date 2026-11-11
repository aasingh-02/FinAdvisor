import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { EMIBreakdownChart } from '../components/charts/EMIBreakdownChart';
import { AmortizationTable } from '../components/calculator/AmortizationTable';
import { emiService } from '../services/emiService';
import { formatINR } from '../utils/formatCurrency';
import {
  Percent,
  IndianRupee,
  Clock,
  PieChart,
  ShieldCheck,
  CheckCircle2,
  RefreshCw,
} from 'lucide-react';

// Preset options for quick clicks
const PRINCIPAL_PRESETS = [
  { label: '₹5 Lakh', value: 500000 },
  { label: '₹10 Lakh', value: 1000000 },
  { label: '₹25 Lakh', value: 2500000 },
  { label: '₹50 Lakh', value: 5000000 },
  { label: '₹1 Crore', value: 10000000 },
];

const RATE_PRESETS = [
  { label: '0% (Zero Interest)', value: 0.0 },
  { label: '8.5% (Home)', value: 8.5 },
  { label: '9.0% (Standard)', value: 9.0 },
  { label: '11.0% (Auto)', value: 11.0 },
  { label: '14.0% (Personal)', value: 14.0 },
];

const TENURE_PRESETS = [
  { label: '1 Year', months: 12 },
  { label: '3 Years', months: 36 },
  { label: '5 Years', months: 60 },
  { label: '10 Years', months: 120 },
  { label: '20 Years', months: 240 },
];

export const EMICalculatorPage = () => {
  // Input parameters (defaulting to the reference case)
  const [principal, setPrincipal] = useState(1000000);
  const [annualRate, setAnnualRate] = useState(9.0);
  const [tenureValue, setTenureValue] = useState(5);
  const [tenureUnit, setTenureUnit] = useState('years'); // 'years' | 'months'

  // Actual months used for backend calculation
  const tenureMonths = tenureUnit === 'years' ? tenureValue * 12 : tenureValue;

  // Calculation state (FastAPI backend is the single source of truth)
  const [result, setResult] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');

  // Keep track of last requested params to avoid duplicate calls
  const lastRequestedRef = useRef('');

  // Debounced calculation function
  const fetchCalculation = useCallback(async (p, r, m) => {
    // Validate bounds locally before making API call
    if (p <= 0 || r < 0 || m <= 0) return;

    const requestKey = `${p}-${r}-${m}`;
    if (requestKey === lastRequestedRef.current) return;
    lastRequestedRef.current = requestKey;

    try {
      setIsLoading(true);
      setErrorMessage('');
      const data = await emiService.calculateEMI({
        principalAmount: p,
        annualInterestRate: r,
        tenureMonths: m,
      });
      setResult(data);
    } catch (err) {
      setErrorMessage(err.message || 'Failed to calculate EMI from server.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Debounce API requests by 300 ms on input change
  useEffect(() => {
    const timer = setTimeout(() => {
      fetchCalculation(principal, annualRate, tenureMonths);
    }, 300);

    return () => clearTimeout(timer);
  }, [principal, annualRate, tenureMonths, fetchCalculation]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              EMI & Amortization Calculator
            </h1>
            <Badge variant="success" size="sm" className="bg-emerald-50 text-emerald-700 border-emerald-200">
              Deterministic Engine
            </Badge>
          </div>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Simulate monthly repayment, total interest payout, and loan amortization using standard reducing-balance math.
          </p>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto text-xs text-slate-500 font-medium bg-white px-3 py-1.5 rounded-lg border border-slate-200/80 shadow-subtle">
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
          <span>FastAPI Verified (Zero Hallucinations)</span>
        </div>
      </div>

      <ErrorAlert message={errorMessage} onClose={() => setErrorMessage('')} />

      {/* Main Interactive Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* ── Left Column: Interactive Inputs & Sliders (7 cols) ── */}
        <div className="lg:col-span-7 space-y-5">
          <Card
            title="Loan Parameters"
            subtitle="Adjust loan principal, interest rate, and repayment tenure"
          >
            <div className="space-y-6">
              {/* 1. Principal Amount */}
              <div className="space-y-2.5">
                <div className="flex items-center justify-between">
                  <label htmlFor="principal-input" className="text-xs font-semibold uppercase tracking-wider text-slate-700">
                    Loan Amount (Principal)
                  </label>
                  <div className="relative rounded-lg shadow-subtle max-w-[200px]">
                    <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400 font-medium text-sm">
                      ₹
                    </span>
                    <input
                      id="principal-input"
                      type="number"
                      min="10000"
                      max="100000000"
                      step="10000"
                      value={principal}
                      onChange={(e) => {
                        const val = parseFloat(e.target.value) || 0;
                        setPrincipal(val);
                      }}
                      className="block w-full rounded-lg border border-slate-300 pl-8 pr-3 py-1.5 text-sm font-bold text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-100 focus:border-brand-500 text-right"
                    />
                  </div>
                </div>

                <input
                  type="range"
                  min="10000"
                  max="10000000"
                  step="10000"
                  value={principal}
                  onChange={(e) => setPrincipal(parseFloat(e.target.value))}
                  className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-brand-600"
                />

                <div className="flex flex-wrap gap-1.5 pt-1">
                  {PRINCIPAL_PRESETS.map((p) => (
                    <button
                      key={p.label}
                      type="button"
                      onClick={() => setPrincipal(p.value)}
                      className={`text-[11px] px-2.5 py-1 rounded-md font-medium border transition-colors ${
                        principal === p.value
                          ? 'bg-brand-50 border-brand-300 text-brand-700 font-bold'
                          : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                      }`}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* 2. Annual Interest Rate */}
              <div className="space-y-2.5 pt-4 border-t border-slate-100">
                <div className="flex items-center justify-between">
                  <label htmlFor="rate-input" className="text-xs font-semibold uppercase tracking-wider text-slate-700">
                    Annual Interest Rate (% p.a.)
                  </label>
                  <div className="relative rounded-lg shadow-subtle max-w-[140px]">
                    <input
                      id="rate-input"
                      type="number"
                      min="0"
                      max="30"
                      step="0.1"
                      value={annualRate}
                      onChange={(e) => {
                        const val = parseFloat(e.target.value);
                        setAnnualRate(isNaN(val) ? 0 : val);
                      }}
                      className="block w-full rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-bold text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-100 focus:border-brand-500 text-right pr-7"
                    />
                    <span className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none text-slate-400 font-medium text-sm">
                      %
                    </span>
                  </div>
                </div>

                <input
                  type="range"
                  min="0"
                  max="25"
                  step="0.1"
                  value={annualRate}
                  onChange={(e) => setAnnualRate(parseFloat(e.target.value))}
                  className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-brand-600"
                />

                <div className="flex flex-wrap gap-1.5 pt-1">
                  {RATE_PRESETS.map((r) => (
                    <button
                      key={r.label}
                      type="button"
                      onClick={() => setAnnualRate(r.value)}
                      className={`text-[11px] px-2.5 py-1 rounded-md font-medium border transition-colors ${
                        annualRate === r.value
                          ? 'bg-brand-50 border-brand-300 text-brand-700 font-bold'
                          : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                      }`}
                    >
                      {r.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* 3. Loan Tenure */}
              <div className="space-y-2.5 pt-4 border-t border-slate-100">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <label htmlFor="tenure-input" className="text-xs font-semibold uppercase tracking-wider text-slate-700">
                      Loan Tenure
                    </label>
                    <div className="flex items-center bg-slate-100 p-0.5 rounded-md text-[10px] font-semibold">
                      <button
                        type="button"
                        onClick={() => {
                          if (tenureUnit !== 'years') {
                            setTenureUnit('years');
                            setTenureValue(Math.max(1, Math.round(tenureValue / 12)));
                          }
                        }}
                        className={`px-2 py-0.5 rounded ${
                          tenureUnit === 'years'
                            ? 'bg-white text-slate-900 shadow-subtle'
                            : 'text-slate-500 hover:text-slate-900'
                        }`}
                      >
                        Years
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          if (tenureUnit !== 'months') {
                            setTenureUnit('months');
                            setTenureValue(tenureValue * 12);
                          }
                        }}
                        className={`px-2 py-0.5 rounded ${
                          tenureUnit === 'months'
                            ? 'bg-white text-slate-900 shadow-subtle'
                            : 'text-slate-500 hover:text-slate-900'
                        }`}
                      >
                        Months
                      </button>
                    </div>
                  </div>

                  <div className="relative rounded-lg shadow-subtle max-w-[140px]">
                    <input
                      id="tenure-input"
                      type="number"
                      min="1"
                      max={tenureUnit === 'years' ? 30 : 360}
                      step="1"
                      value={tenureValue}
                      onChange={(e) => {
                        const val = parseInt(e.target.value, 10) || 1;
                        setTenureValue(val);
                      }}
                      className="block w-full rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-bold text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-100 focus:border-brand-500 text-right pr-14"
                    />
                    <span className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none text-slate-400 font-medium text-xs">
                      {tenureUnit}
                    </span>
                  </div>
                </div>

                <input
                  type="range"
                  min="1"
                  max={tenureUnit === 'years' ? 30 : 360}
                  step="1"
                  value={tenureValue}
                  onChange={(e) => setTenureValue(parseInt(e.target.value, 10))}
                  className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-brand-600"
                />

                <div className="flex flex-wrap gap-1.5 pt-1">
                  {TENURE_PRESETS.map((t) => {
                    const isSelected = tenureMonths === t.months;
                    return (
                      <button
                        key={t.label}
                        type="button"
                        onClick={() => {
                          if (tenureUnit === 'years') {
                            setTenureValue(t.months / 12);
                          } else {
                            setTenureValue(t.months);
                          }
                        }}
                        className={`text-[11px] px-2.5 py-1 rounded-md font-medium border transition-colors ${
                          isSelected
                            ? 'bg-brand-50 border-brand-300 text-brand-700 font-bold'
                            : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                        }`}
                      >
                        {t.label}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          </Card>
        </div>

        {/* ── Right Column: EMI Summary Cards & Recharts Donut (5 cols) ── */}
        <div className="lg:col-span-5 space-y-5">
          <Card
            title="Repayment Summary"
            subtitle="Verified reducing-balance figures from FastAPI"
            headerAction={
              isLoading ? (
                <div className="flex items-center gap-1.5 text-xs text-brand-600 font-medium">
                  <LoadingSpinner size="sm" />
                  <span>Computing...</span>
                </div>
              ) : (
                <span className="text-[11px] text-slate-400 font-mono">
                  {tenureMonths} Payments
                </span>
              )
            }
          >
            {/* Primary Monthly EMI Banner */}
            <div className="p-5 rounded-2xl bg-gradient-to-br from-brand-900 to-slate-900 text-white shadow-card relative overflow-hidden">
              <div className="absolute top-0 right-0 p-4 opacity-10">
                <Percent className="w-24 h-24" />
              </div>
              <div className="relative z-10">
                <span className="text-xs font-semibold uppercase tracking-wider text-brand-200">
                  Monthly EMI Payable
                </span>
                <div className="text-3xl sm:text-4xl font-extrabold tracking-tight mt-1">
                  {result?.monthly_emi ? formatINR(parseFloat(result.monthly_emi), true) : '₹0.00'}
                </div>
                <div className="text-xs text-brand-200/80 mt-1 flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5" />
                  <span>Due monthly for {tenureMonths} installments</span>
                </div>
              </div>
            </div>

            {/* Total Interest & Total Repayment Row */}
            <div className="grid grid-cols-2 gap-3 mt-4">
              <div className="p-3.5 rounded-xl bg-amber-50/70 border border-amber-200/60">
                <div className="text-[11px] font-semibold uppercase tracking-wider text-amber-800">
                  Total Interest
                </div>
                <div className="text-lg sm:text-xl font-bold text-amber-950 mt-0.5">
                  {result?.total_interest ? formatINR(parseFloat(result.total_interest), true) : '₹0.00'}
                </div>
                <div className="text-[11px] text-amber-700 font-medium mt-0.5">
                  {result?.interest_percentage || '0'}% of payout
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80">
                <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                  Total Repayment
                </div>
                <div className="text-lg sm:text-xl font-bold text-slate-900 mt-0.5">
                  {result?.total_repayment ? formatINR(parseFloat(result.total_repayment), true) : '₹0.00'}
                </div>
                <div className="text-[11px] text-slate-500 font-medium mt-0.5">
                  Principal + Interest
                </div>
              </div>
            </div>

            {/* Recharts Donut Pie Chart */}
            <div className="mt-4 pt-3 border-t border-slate-100">
              <EMIBreakdownChart
                principalAmount={result?.principal_amount || principal}
                totalInterest={result?.total_interest || 0}
                principalPercentage={parseFloat(result?.principal_percentage || 100)}
                interestPercentage={parseFloat(result?.interest_percentage || 0)}
                totalRepayment={parseFloat(result?.total_repayment || principal)}
              />
            </div>
          </Card>
        </div>
      </div>

      {/* ── Lower Section: Full Amortization Schedule Table ── */}
      <AmortizationTable schedule={result?.amortization_schedule || []} />
    </div>
  );
};

export default EMICalculatorPage;
