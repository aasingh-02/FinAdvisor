/**
 * frontend/src/pages/RiskDashboardPage.jsx
 * ─────────────────────────────────────────
 * Financial Risk Assessment & Advisory Dashboard.
 *
 * Guarantees:
 * - Powered exclusively by FastAPI deterministic risk scoring engine.
 * - Displays overall composite score, diagnostic indicators, and actionable guidance.
 * - Supports configurable FOIR benchmark threshold (default: 40%).
 * - Handles loading skeletons, network retry, unauthenticated 401, and missing profile 404 with CTA.
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { RiskScoreCard } from '../components/risk/RiskScoreCard';
import { RiskIndicators } from '../components/risk/RiskIndicators';
import { RiskRecommendations } from '../components/risk/RiskRecommendations';
import { riskService } from '../services/riskService';
import {
  ShieldAlert,
  ShieldCheck,
  RefreshCw,
  UserPlus,
  ArrowRight,
  AlertCircle,
  Sliders,
  SlidersHorizontal,
} from 'lucide-react';

const THRESHOLD_PRESETS = [
  { label: '30% (Conservative)', value: 30 },
  { label: '35% (Moderate)', value: 35 },
  { label: '40% (Standard Benchmark)', value: 40 },
  { label: '45% (Flexible)', value: 45 },
  { label: '50% (High Leeway)', value: 50 },
];

export const RiskDashboardPage = () => {
  // Configurable policy threshold
  const [threshold, setThreshold] = useState(40.0);

  // API State
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isMissingProfile, setIsMissingProfile] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  // Track last requested parameter to eliminate duplicate network calls
  const lastRequestedRef = useRef('');

  const fetchAssessment = useCallback(async (t, isManualRefresh = false) => {
    const key = `${t}`;
    if (!isManualRefresh && key === lastRequestedRef.current) return;
    lastRequestedRef.current = key;

    try {
      if (isManualRefresh) {
        setIsRefreshing(true);
      } else {
        setIsLoading(true);
      }
      setErrorMessage('');
      setIsMissingProfile(false);

      const result = await riskService.getRiskAssessment({ threshold: t });
      setData(result);
    } catch (err) {
      if (
        err.status === 404 ||
        (err.message && err.message.toLowerCase().includes('not found'))
      ) {
        setIsMissingProfile(true);
      } else {
        setErrorMessage(err.message || 'Failed to retrieve risk assessment from server.');
      }
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  // Debounced fetch on threshold change
  useEffect(() => {
    const timer = setTimeout(() => {
      fetchAssessment(threshold);
    }, 300);

    return () => clearTimeout(timer);
  }, [threshold, fetchAssessment]);

  const handleManualRefresh = () => {
    fetchAssessment(threshold, true);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              Financial Risk & Advisory Engine
            </h1>
            <Badge variant="success" size="sm" className="bg-emerald-50 text-emerald-700 border-emerald-200">
              Deterministic AI Engine
            </Badge>
          </div>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Comprehensive evaluation of debt burden, liquidity reserves, and cash flow resilience.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2 self-start sm:self-auto">
          <Button
            variant="secondary"
            size="sm"
            onClick={handleManualRefresh}
            disabled={isLoading || isRefreshing}
            className="text-xs"
          >
            <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${isRefreshing ? 'animate-spin' : ''}`} />
            Refresh Analysis
          </Button>

          <div className="flex items-center gap-1.5 text-xs text-slate-500 font-medium bg-white px-3 py-1.5 rounded-lg border border-slate-200/80 shadow-subtle">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            <span>FastAPI Verified</span>
          </div>
        </div>
      </div>

      {/* Error Alert with Retry */}
      {errorMessage && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-sm flex items-start justify-between gap-3 shadow-subtle">
          <div className="flex items-start gap-2.5">
            <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-rose-900">Unable to load risk assessment</p>
              <p className="text-xs text-rose-700 mt-0.5">{errorMessage}</p>
            </div>
          </div>
          <Button variant="secondary" size="sm" onClick={() => fetchAssessment(threshold, true)} className="shrink-0">
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
                Financial Profile Required for Risk Assessment
              </h3>
              <p className="text-xs sm:text-sm text-slate-500 mt-1.5 leading-relaxed">
                The Risk & Advisory Engine requires your net income, living costs, existing EMIs, and emergency savings to calculate risk ratios and generate personalized guidance.
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

      {/* Main Dashboard Content */}
      {!isMissingProfile && (
        <>
          {/* Policy Benchmark Slider Strip */}
          <div className="p-4 rounded-xl bg-white border border-slate-200/90 shadow-subtle flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <SlidersHorizontal className="w-4 h-4 text-brand-600" />
              <div>
                <span className="text-xs font-bold text-slate-900 block">
                  Configured FOIR Benchmark Threshold: {threshold.toFixed(1)}%
                </span>
                <span className="text-[11px] text-slate-500">
                  Assess how underwriting policy tightness affects your risk rating
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <div className="flex flex-wrap gap-1.5">
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
          </div>

          {/* Loading Skeletons */}
          {isLoading && !data ? (
            <div className="space-y-6 animate-pulse">
              <div className="h-64 bg-slate-100 rounded-2xl" />
              <div className="h-72 bg-slate-100 rounded-2xl" />
              <div className="h-64 bg-slate-100 rounded-2xl" />
            </div>
          ) : data ? (
            <div className="space-y-6">
              {/* 1. Overall Executive Risk Score Card */}
              <RiskScoreCard data={data} />

              {/* 2. Diagnostic Risk Indicators Grid & Active Warnings */}
              <RiskIndicators
                indicators={data.indicators || []}
                warnings={data.triggered_warnings || []}
              />

              {/* 3. Actionable Advisory Recommendations */}
              <RiskRecommendations
                recommendations={data.recommendations || []}
              />
            </div>
          ) : null}
        </>
      )}
    </div>
  );
};

export default RiskDashboardPage;
