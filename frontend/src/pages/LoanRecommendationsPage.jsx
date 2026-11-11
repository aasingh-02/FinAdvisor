/**
 * frontend/src/pages/LoanRecommendationsPage.jsx
 * ──────────────────────────────────────────────
 * Personalized Loan Recommendations Dashboard.
 *
 * Guarantees:
 * - 100% powered by FastAPI deterministic loan recommendation engine.
 * - Displays 4 benchmark categories: Personal, Home, Vehicle, Education.
 * - Displays sustainable loan principal, EMI, tenure, interest rate, projected FOIR.
 * - Supports custom loan sizing simulation (category, desired amount, custom tenure).
 * - Handles loading, 401 unauthenticated, 404 missing profile, and network retry states.
 * - Provides access to reducing-balance amortization schedules.
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { EligibilityBanner } from '../components/recommendations/EligibilityBanner';
import { RecommendationCard } from '../components/recommendations/RecommendationCard';
import { CustomLoanForm } from '../components/recommendations/CustomLoanForm';
import { AmortizationModal } from '../components/recommendations/AmortizationModal';
import { recommendationService } from '../services/recommendationService';
import {
  Sparkles,
  RefreshCw,
  SlidersHorizontal,
  UserPlus,
  AlertCircle,
  HelpCircle,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  FileText,
  Building,
} from 'lucide-react';

export const LoanRecommendationsPage = () => {
  // Recommendation request parameters
  const [params, setParams] = useState({
    foirThreshold: 40.0,
    preferredCategory: null,
    desiredAmount: null,
    preferredTenure: null,
  });

  // UI state
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isMissingProfile, setIsMissingProfile] = useState(false);
  const [isUnauthenticated, setIsUnauthenticated] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [showCustomForm, setShowCustomForm] = useState(false);
  const [selectedScheduleItem, setSelectedScheduleItem] = useState(null);

  // Prevent duplicate in-flight requests
  const lastQueryRef = useRef('');

  const fetchRecommendations = useCallback(async (currentParams, isManualRefresh = false) => {
    const queryKey = JSON.stringify(currentParams);
    if (!isManualRefresh && queryKey === lastQueryRef.current) return;
    lastQueryRef.current = queryKey;

    try {
      if (isManualRefresh) {
        setIsRefreshing(true);
      } else {
        setIsLoading(true);
      }
      setErrorMessage('');
      setIsMissingProfile(false);
      setIsUnauthenticated(false);

      const result = await recommendationService.generateRecommendations(currentParams);
      setData(result);
    } catch (err) {
      if (err.status === 401) {
        setIsUnauthenticated(true);
      } else if (
        err.status === 404 ||
        (err.message && err.message.toLowerCase().includes('profile not found'))
      ) {
        setIsMissingProfile(true);
      } else {
        setErrorMessage(
          err.message || 'Failed to fetch loan recommendations from FinAdvisor server.'
        );
      }
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  // Initial load and params update
  useEffect(() => {
    fetchRecommendations(params);
  }, [params, fetchRecommendations]);

  const handleCustomSubmit = (newParams) => {
    setParams(newParams);
  };

  const handleCustomReset = () => {
    setParams({
      foirThreshold: 40.0,
      preferredCategory: null,
      desiredAmount: null,
      preferredTenure: null,
    });
  };

  const handleManualRefresh = () => {
    fetchRecommendations(params, true);
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              Personalized Loan Recommendations
            </h1>
            <Badge variant="primary" size="sm">
              Phase 2 Engine
            </Badge>
          </div>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Prudent borrowing capacity and loan principal recommendations calculated deterministically from your financial profile and FOIR limits.
          </p>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowCustomForm(!showCustomForm)}
            className="flex items-center gap-1.5 text-xs text-slate-700"
          >
            <SlidersHorizontal className="w-3.5 h-3.5 text-slate-500" />
            {showCustomForm ? 'Hide Sizing Controls' : 'Custom Sizing & Filters'}
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={handleManualRefresh}
            disabled={isLoading || isRefreshing}
            className="flex items-center gap-1.5 text-xs text-slate-700"
          >
            <RefreshCw
              className={`w-3.5 h-3.5 text-slate-500 ${isRefreshing ? 'animate-spin' : ''}`}
            />
            Refresh
          </Button>
        </div>
      </div>

      {/* State: 401 Unauthenticated */}
      {isUnauthenticated && (
        <Card>
          <div className="p-8 text-center max-w-md mx-auto space-y-4">
            <div className="w-14 h-14 rounded-2xl bg-amber-50 text-amber-600 flex items-center justify-center mx-auto border border-amber-200">
              <AlertCircle className="w-7 h-7" />
            </div>
            <h3 className="text-lg font-bold text-slate-900">
              Authentication Required
            </h3>
            <p className="text-sm text-slate-500 leading-relaxed">
              Your session has expired or you are not signed in. Please log in to view your personalized loan recommendations.
            </p>
            <Link to="/login">
              <Button variant="primary" size="md" className="mt-2">
                Log In to Continue
              </Button>
            </Link>
          </div>
        </Card>
      )}

      {/* State: 404 Missing Financial Profile */}
      {isMissingProfile && (
        <Card>
          <div className="p-8 text-center max-w-lg mx-auto space-y-4">
            <div className="w-14 h-14 rounded-2xl bg-brand-50 text-brand-600 flex items-center justify-center mx-auto border border-brand-100">
              <UserPlus className="w-7 h-7" />
            </div>
            <h3 className="text-lg font-bold text-slate-900">
              Financial Profile Required
            </h3>
            <p className="text-sm text-slate-500 leading-relaxed">
              To calculate sustainable loan recommendations, FinAdvisor needs your income, existing EMI obligations, and emergency savings details.
            </p>
            <div className="pt-2">
              <Link to="/profile">
                <Button variant="primary" size="md" className="inline-flex items-center gap-2">
                  Create Your Financial Profile
                  <ArrowRight className="w-4 h-4" />
                </Button>
              </Link>
            </div>
          </div>
        </Card>
      )}

      {/* State: General / Network Error */}
      {errorMessage && !isMissingProfile && !isUnauthenticated && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 flex items-center justify-between gap-3 text-sm">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />
            <span>{errorMessage}</span>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleManualRefresh}
            className="text-xs bg-white text-rose-700 border-rose-300 hover:bg-rose-100"
          >
            Retry
          </Button>
        </div>
      )}

      {/* Custom Loan Simulator & Filter Box */}
      {showCustomForm && !isMissingProfile && !isUnauthenticated && (
        <CustomLoanForm
          initialValues={params}
          onSubmit={handleCustomSubmit}
          onReset={handleCustomReset}
          isLoading={isLoading}
        />
      )}

      {/* Loading Skeletons */}
      {isLoading && !data && (
        <div className="space-y-6">
          <div className="h-44 rounded-2xl bg-slate-100 animate-pulse" />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-96 rounded-2xl bg-slate-100 animate-pulse" />
            ))}
          </div>
        </div>
      )}

      {/* Main Content (When Data Available) */}
      {data && !isMissingProfile && !isUnauthenticated && (
        <div className="space-y-6">
          {/* Eligibility & Risk Snapshot */}
          <EligibilityBanner
            isEligible={data.is_eligible}
            summary={data.eligibility_summary}
            financialSnapshot={data.financial_snapshot}
            riskConsiderations={data.risk_considerations}
            warnings={data.reasons_and_warnings}
          />

          {/* Active Custom Filter Tag Pill */}
          {(params.desiredAmount || params.preferredCategory || params.preferredTenure) && (
            <div className="p-3 bg-brand-50/50 rounded-xl border border-brand-200 flex flex-wrap items-center justify-between gap-2 text-xs">
              <div className="flex items-center gap-2 text-brand-900 font-medium">
                <Sparkles className="w-4 h-4 text-brand-600 shrink-0" />
                <span>Custom simulation active:</span>
                {params.preferredCategory && (
                  <Badge variant="primary" size="sm">
                    {params.preferredCategory.replace('_', ' ')}
                  </Badge>
                )}
                {params.desiredAmount && (
                  <span className="font-bold">
                    Target: ₹{Number(params.desiredAmount).toLocaleString('en-IN')}
                  </span>
                )}
                {params.preferredTenure && (
                  <span>Tenure: {params.preferredTenure} months</span>
                )}
              </div>
              <button
                type="button"
                onClick={handleCustomReset}
                className="text-xs font-semibold text-brand-700 hover:text-brand-900 underline"
              >
                Clear Custom Filters
              </button>
            </div>
          )}

          {/* Recommendation Scenario Cards */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-lg font-bold text-slate-900">
                  {data.recommendations.length > 0
                    ? `Recommended Loan Scenarios (${data.recommendations.length})`
                    : 'Borrowing Recommendations'}
                </h2>
                <p className="text-xs text-slate-500">
                  Calculated using reducing-balance monthly amortization to fit your verified disposable cash flow
                </p>
              </div>
            </div>

            {data.recommendations.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
                {data.recommendations.map((rec) => (
                  <RecommendationCard
                    key={rec.loan_category}
                    recommendation={rec}
                    onOpenSchedule={(item) => setSelectedScheduleItem(item)}
                  />
                ))}
              </div>
            ) : (
              <Card>
                <div className="p-8 text-center max-w-lg mx-auto space-y-3">
                  <div className="w-12 h-12 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center mx-auto border border-amber-200">
                    <AlertCircle className="w-6 h-6" />
                  </div>
                  <h3 className="text-base font-bold text-slate-900">
                    No Additional Borrowing Currently Recommended
                  </h3>
                  <p className="text-xs text-slate-500 leading-relaxed">
                    Based on your financial profile, your existing fixed obligations or living expenses consume your available income headroom under your configured {params.foirThreshold}% FOIR policy benchmark.
                  </p>
                  <p className="text-xs text-slate-600 font-medium pt-1">
                    Please review the advisory warnings above or consider debt consolidation before taking on new loan obligations.
                  </p>
                </div>
              </Card>
            )}
          </div>

          {/* Mandatory Underwriting Disclaimers & Rate Assumptions */}
          {data.assumptions_and_disclaimers && (
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 text-xs text-slate-500 space-y-1">
              <div className="flex items-center gap-1.5 font-semibold text-slate-700">
                <HelpCircle className="w-3.5 h-3.5 text-slate-400" />
                Underwriting Disclaimers & Assumptions
              </div>
              <p className="leading-relaxed text-[11px]">
                {data.assumptions_and_disclaimers}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Amortization Detail Modal */}
      {selectedScheduleItem && (
        <AmortizationModal
          recommendation={selectedScheduleItem}
          onClose={() => setSelectedScheduleItem(null)}
        />
      )}
    </div>
  );
};

export default LoanRecommendationsPage;
