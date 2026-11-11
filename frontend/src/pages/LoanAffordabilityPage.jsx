/**
 * frontend/src/pages/LoanAffordabilityPage.jsx
 * ─────────────────────────────────────────────
 * Interactive FOIR (Fixed Obligation to Income Ratio) and Loan Affordability Dashboard.
 *
 * Guarantees:
 * - All calculations are strictly retrieved from the deterministic FastAPI backend.
 * - Supports configurable FOIR threshold (default: 40%).
 * - Interactive proposed EMI simulation with 300ms debounce and duplicate call prevention.
 * - Indian Rupee formatting (₹ INR) throughout.
 * - Handles loading, network retry, unauthenticated 401, missing profile 404, and error states.
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { FOIRGauge } from '../components/charts/FOIRGauge';
import { FOIRBreakdown } from '../components/calculator/FOIRBreakdown';
import { foirService } from '../services/foirService';
import { formatINR } from '../utils/formatCurrency';
import {
  Calculator,
  Sliders,
  Sparkles,
  AlertCircle,
  ShieldCheck,
  TrendingUp,
  RefreshCw,
  UserPlus,
  ArrowRight,
  Info,
  CheckCircle2,
  XCircle,
} from 'lucide-react';

const THRESHOLD_PRESETS = [
  { label: '30% (Conservative)', value: 30 },
  { label: '35% (Moderate)', value: 35 },
  { label: '40% (Standard Benchmark)', value: 40 },
  { label: '45% (Flexible)', value: 45 },
  { label: '50% (High Leeway)', value: 50 },
];

const PROPOSED_EMI_PRESETS = [
  { label: '+₹5,000', value: 5000 },
  { label: '+₹10,000', value: 10000 },
  { label: '+₹15,000', value: 15000 },
  { label: '+₹25,000', value: 25000 },
  { label: '+₹50,000', value: 50000 },
];

export const LoanAffordabilityPage = () => {
  // Configurable policy threshold (default 40.0%)
  const [threshold, setThreshold] = useState(40.0);

  // Proposed EMI simulation input (empty string or number)
  const [proposedEmiInput, setProposedEmiInput] = useState('');

  // API State
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isMissingProfile, setIsMissingProfile] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  // Ref to track last requested parameters to avoid duplicate roundtrips
  const lastRequestedRef = useRef('');

  // Debounced API fetcher
  const fetchFOIR = useCallback(async (t, pEmi) => {
    const validEmi = pEmi !== '' && !isNaN(pEmi) && parseFloat(pEmi) >= 0 ? parseFloat(pEmi) : null;
    const requestKey = `${t}-${validEmi ?? 'none'}`;

    if (requestKey === lastRequestedRef.current) return;
    lastRequestedRef.current = requestKey;

    try {
      setIsLoading(true);
      setErrorMessage('');
      setIsMissingProfile(false);

      const result = await foirService.calculateFOIR({
        threshold: t,
        proposedEmi: validEmi,
      });

      setData(result);
    } catch (err) {
      if (
        err.status === 404 ||
        (err.message && err.message.toLowerCase().includes('not found'))
      ) {
        setIsMissingProfile(true);
      } else {
        setErrorMessage(err.message || 'Failed to calculate FOIR from server.');
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  // 300 ms Debounce effect on threshold or proposed EMI change
  useEffect(() => {
    const timer = setTimeout(() => {
      fetchFOIR(threshold, proposedEmiInput);
    }, 300);

    return () => clearTimeout(timer);
  }, [threshold, proposedEmiInput, fetchFOIR]);

  // Handler for manual retry
  const handleRetry = () => {
    lastRequestedRef.current = '';
    fetchFOIR(threshold, proposedEmiInput);
  };

  const parsedProposedEmi =
    proposedEmiInput !== '' && !isNaN(proposedEmiInput) ? parseFloat(proposedEmiInput) : 0;
  const additionalCapacity = data ? parseFloat(data.additional_emi_capacity) : 0;
  const isProposedExceeding =
    parsedProposedEmi > 0 && data && parsedProposedEmi > additionalCapacity;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              Loan Affordability & FOIR Calculator
            </h1>
            <Badge variant="success" size="sm" className="bg-emerald-50 text-emerald-700 border-emerald-200">
              Deterministic Engine
            </Badge>
          </div>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Evaluate your debt-to-income affordability, maximum borrowing capacity, and simulate new loan EMIs.
          </p>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto text-xs text-slate-500 font-medium bg-white px-3 py-1.5 rounded-lg border border-slate-200/80 shadow-subtle">
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
          <span>FastAPI Underwriting Service</span>
        </div>
      </div>

      {/* Error Alert with Retry */}
      {errorMessage && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-sm flex items-start justify-between gap-3 shadow-subtle">
          <div className="flex items-start gap-2.5">
            <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-rose-900">Unable to load affordability calculation</p>
              <p className="text-xs text-rose-700 mt-0.5">{errorMessage}</p>
            </div>
          </div>
          <Button variant="secondary" size="sm" onClick={handleRetry} className="shrink-0">
            <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
            Retry
          </Button>
        </div>
      )}

      {/* Missing Financial Profile State (HTTP 404) */}
      {isMissingProfile && (
        <Card>
          <div className="py-12 px-4 max-w-lg mx-auto text-center space-y-4">
            <div className="w-16 h-16 rounded-2xl bg-amber-50 text-amber-600 flex items-center justify-center mx-auto border border-amber-200">
              <UserPlus className="w-8 h-8" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-slate-900">
                Financial Profile Required
              </h3>
              <p className="text-xs sm:text-sm text-slate-500 mt-1.5 leading-relaxed">
                To evaluate your Fixed Obligation to Income Ratio (FOIR) and safe borrowing capacity, FinAdvisor needs your monthly take-home income and existing loan EMI details.
              </p>
            </div>
            <div className="pt-2">
              <Link to="/profile">
                <Button variant="primary" size="md">
                  Complete Financial Profile
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </Link>
            </div>
          </div>
        </Card>
      )}

      {/* Main Calculator Content */}
      {!isMissingProfile && (
        <>
          {/* Top Interactive Grid: Left Controls (7 cols) + Right Gauge (5 cols) */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* ── Left Column: Configurable Policy & Proposed EMI Simulator (7 cols) ── */}
            <div className="lg:col-span-7 space-y-5">
              {/* 1. Proposed EMI Simulator Card */}
              <Card
                title="Proposed Loan EMI Simulation"
                subtitle="Simulate adding a new monthly installment to assess your projected FOIR"
                headerAction={
                  parsedProposedEmi > 0 ? (
                    <button
                      type="button"
                      onClick={() => setProposedEmiInput('')}
                      className="text-xs text-slate-500 hover:text-slate-900 font-medium underline"
                    >
                      Reset Simulation
                    </button>
                  ) : null
                }
              >
                <div className="space-y-4">
                  {/* Proposed EMI Input Box & Slider */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <label
                        htmlFor="proposed-emi-input"
                        className="text-xs font-semibold uppercase tracking-wider text-slate-700"
                      >
                        Proposed Monthly EMI
                      </label>
                      <div className="relative rounded-lg shadow-subtle max-w-[200px]">
                        <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400 font-medium text-sm">
                          ₹
                        </span>
                        <input
                          id="proposed-emi-input"
                          type="number"
                          min="0"
                          max="500000"
                          step="1000"
                          placeholder="e.g. 15000"
                          value={proposedEmiInput}
                          onChange={(e) => setProposedEmiInput(e.target.value)}
                          className="block w-full rounded-lg border border-slate-300 pl-8 pr-3 py-1.5 text-sm font-bold text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-100 focus:border-brand-500 text-right"
                        />
                      </div>
                    </div>

                    <input
                      type="range"
                      min="0"
                      max="100000"
                      step="1000"
                      value={parsedProposedEmi}
                      onChange={(e) => setProposedEmiInput(e.target.value)}
                      className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-brand-600"
                    />

                    {/* Quick Add Presets */}
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {PROPOSED_EMI_PRESETS.map((p) => {
                        const isSelected = parsedProposedEmi === p.value;
                        return (
                          <button
                            key={p.label}
                            type="button"
                            onClick={() => setProposedEmiInput(p.value.toString())}
                            className={`text-[11px] px-2.5 py-1 rounded-md font-medium border transition-colors ${
                              isSelected
                                ? 'bg-brand-50 border-brand-300 text-brand-700 font-bold'
                                : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                            }`}
                          >
                            {p.label}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Proposed Simulation Warning / Confirmation Box */}
                  {parsedProposedEmi > 0 && data && (
                    <div
                      className={`p-3.5 rounded-xl border text-xs space-y-1.5 transition-all ${
                        isProposedExceeding
                          ? 'bg-rose-50/80 border-rose-200 text-rose-900'
                          : 'bg-emerald-50/80 border-emerald-200 text-emerald-900'
                      }`}
                    >
                      <div className="flex items-center gap-2 font-bold">
                        {isProposedExceeding ? (
                          <XCircle className="w-4 h-4 text-rose-600 shrink-0" />
                        ) : (
                          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                        )}
                        <span>
                          {isProposedExceeding
                            ? 'Proposed EMI Exceeds Safe Capacity'
                            : 'Proposed EMI Within Policy Capacity'}
                        </span>
                      </div>
                      <p className="text-[11px] leading-relaxed">
                        {isProposedExceeding
                          ? `This proposed EMI of ${formatINR(
                              parsedProposedEmi,
                              true
                            )} exceeds your available headroom of ${formatINR(
                              additionalCapacity,
                              true
                            )}. Your projected FOIR increases to ${data.projected_foir_percentage}%.`
                          : `This installment fits safely within your ${threshold}% policy headroom. Remaining additional capacity after this loan will be ${formatINR(
                              Math.max(0, additionalCapacity - parsedProposedEmi),
                              true
                            )}.`}
                      </p>
                    </div>
                  )}
                </div>
              </Card>

              {/* 2. Configurable FOIR Policy Benchmark Card */}
              <Card
                title="Configurable FOIR Policy Benchmark"
                subtitle="Adjust the policy threshold to evaluate lender limits"
              >
                <div className="space-y-4">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <label
                        htmlFor="threshold-slider"
                        className="text-xs font-semibold uppercase tracking-wider text-slate-700"
                      >
                        Policy Threshold Percentage
                      </label>
                      <span className="text-base font-extrabold text-brand-600 bg-brand-50 px-2.5 py-0.5 rounded-lg border border-brand-100">
                        {threshold.toFixed(1)}%
                      </span>
                    </div>

                    <input
                      id="threshold-slider"
                      type="range"
                      min="10"
                      max="60"
                      step="1"
                      value={threshold}
                      onChange={(e) => setThreshold(parseFloat(e.target.value))}
                      className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-brand-600"
                    />

                    {/* Presets */}
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {THRESHOLD_PRESETS.map((t) => {
                        const isSelected = Math.abs(threshold - t.value) < 0.1;
                        return (
                          <button
                            key={t.label}
                            type="button"
                            onClick={() => setThreshold(t.value)}
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

                  {/* Benchmark Context Note */}
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200/80 text-[11px] text-slate-600 flex items-start gap-2">
                    <Info className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
                    <span>
                      <strong>Illustrative Planning Benchmark:</strong> Most commercial Indian lenders
                      cap total monthly obligations between 40% and 50% of net in-hand income. Actual
                      approval depends on your CIBIL score, employer tier, and loan collateral.
                    </span>
                  </div>
                </div>
              </Card>
            </div>

            {/* ── Right Column: Visual FOIR Gauge (5 cols) ── */}
            <div className="lg:col-span-5 space-y-5">
              <Card
                title="Debt-to-Income Gauge"
                subtitle="Real-time ratio analysis from FastAPI engine"
                headerAction={
                  isLoading ? (
                    <div className="flex items-center gap-1.5 text-xs text-brand-600 font-medium">
                      <LoadingSpinner size="sm" />
                      <span>Evaluating...</span>
                    </div>
                  ) : (
                    <span className="text-[11px] text-slate-400 font-mono">
                      Threshold: {threshold}%
                    </span>
                  )
                }
              >
                {isLoading && !data ? (
                  <div className="py-16 flex flex-col items-center justify-center space-y-3">
                    <LoadingSpinner size="lg" />
                    <p className="text-xs text-slate-500 font-medium">
                      Computing financial ratios...
                    </p>
                  </div>
                ) : (
                  <FOIRGauge
                    currentFoir={data?.current_foir_percentage || 0}
                    configuredThreshold={data?.configured_foir_threshold || threshold}
                    affordabilityStatus={data?.affordability_status || 'Optimal'}
                    projectedFoir={data?.projected_foir_percentage ?? null}
                    proposedEmi={data?.proposed_emi ?? null}
                    monthlyIncome={data?.monthly_net_income || 0}
                  />
                )}
              </Card>
            </div>
          </div>

          {/* ── Lower Section: Comprehensive Metrics Breakdown & Allocation ── */}
          {data && <FOIRBreakdown data={data} />}
        </>
      )}
    </div>
  );
};

export default LoanAffordabilityPage;
