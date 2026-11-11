import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import dashboardService from '../services/dashboardService';
import { FinancialHealthCard } from '../components/dashboard/FinancialHealthCard';
import { DashboardMetricCards } from '../components/dashboard/DashboardMetricCards';
import { ExecutiveSummarySection } from '../components/dashboard/ExecutiveSummarySection';
import { ProfileIncompleteBanner } from '../components/dashboard/ProfileIncompleteBanner';
import { DashboardSkeleton } from '../components/dashboard/DashboardSkeleton';
import { QuickActions } from '../components/dashboard/QuickActions';
import { RecentActivity } from '../components/dashboard/RecentActivity';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import {
  Sparkles,
  RefreshCw,
  Sliders,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';

export const DashboardPage = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [threshold, setThreshold] = useState(40.0);

  const fetchDashboardData = useCallback(async (isRefresh = false) => {
    try {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);

      const data = await dashboardService.getDashboardSummary({ threshold });
      setDashboardData(data);
    } catch (err) {
      if (err.status === 401) {
        // Session expired or unauthenticated
        try {
          await logout();
        } catch {
          // ignore logout error
        }
        navigate('/login', { replace: true });
        return;
      }
      setError(err.message || 'Failed to load financial dashboard. Please try again.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [threshold, logout, navigate]);

  useEffect(() => {
    fetchDashboardData(false);
  }, [fetchDashboardData]);

  if (loading && !dashboardData) {
    return <DashboardSkeleton />;
  }

  const isProfileComplete = dashboardData?.profile_complete === true;

  return (
    <div className="space-y-6">
      {/* Welcome & System Banner */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 p-6 bg-gradient-to-r from-brand-900 via-brand-800 to-slate-900 rounded-2xl text-white shadow-card">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight">
              Hello, {user?.full_name || 'Valued User'}
            </h1>
            <Badge
              variant={isProfileComplete ? 'success' : 'warning'}
              size="sm"
              className={
                isProfileComplete
                  ? 'bg-emerald-500/20 text-emerald-300 border-emerald-400/30'
                  : 'bg-amber-500/20 text-amber-300 border-amber-400/30'
              }
            >
              {isProfileComplete ? 'Profile Complete' : 'Profile Incomplete'}
            </Badge>
          </div>
          <p className="text-xs sm:text-sm text-brand-100/80 mt-1 max-w-2xl leading-relaxed">
            {isProfileComplete
              ? 'Your unified financial health overview is live. Monitor debt exposure, liquid emergency buffers, and calculated borrowing capacity.'
              : 'Welcome to FinAdvisor. Complete your profile to unlock deterministic health scoring, FOIR ratio, and personalized loan recommendations.'}
          </p>
        </div>

        {/* Right-side controls */}
        <div className="flex items-center gap-2.5 self-start md:self-auto flex-wrap">
          {/* Policy FOIR Threshold Selector */}
          {isProfileComplete && (
            <div className="flex items-center gap-1.5 bg-white/10 backdrop-blur-md px-3 py-1.5 rounded-xl border border-white/10 text-xs">
              <Sliders className="w-3.5 h-3.5 text-brand-300" />
              <span className="text-brand-200 hidden sm:inline">FOIR Benchmark:</span>
              <select
                aria-label="FOIR policy threshold"
                value={threshold}
                onChange={(e) => setThreshold(parseFloat(e.target.value))}
                className="bg-transparent text-white font-bold cursor-pointer focus:outline-hidden"
              >
                <option value={30.0} className="text-slate-900 bg-white">30% (Conservative)</option>
                <option value={40.0} className="text-slate-900 bg-white">40% (Standard Benchmark)</option>
                <option value={50.0} className="text-slate-900 bg-white">50% (Flexible)</option>
              </select>
            </div>
          )}

          {/* Refresh Button */}
          <button
            type="button"
            onClick={() => fetchDashboardData(true)}
            disabled={refreshing}
            className="p-2 rounded-xl bg-white/10 hover:bg-white/20 border border-white/10 text-white transition-colors disabled:opacity-50"
            title="Refresh dashboard data"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Error Alert with Retry */}
      {error && (
        <div className="space-y-2">
          <ErrorAlert message={error} onClose={() => setError(null)} />
          <div className="flex justify-end">
            <Button
              variant="outline"
              size="sm"
              onClick={() => fetchDashboardData(false)}
              className="text-xs font-semibold"
            >
              Retry Connection
            </Button>
          </div>
        </div>
      )}

      {/* Case A: Profile Incomplete */}
      {!isProfileComplete && (
        <div className="space-y-6">
          <ProfileIncompleteBanner
            warningMessage={dashboardData?.active_warnings?.[0]}
          />
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <QuickActions />
            <RecentActivity />
          </div>
        </div>
      )}

      {/* Case B: Profile Complete */}
      {isProfileComplete && (
        <div className="space-y-6">
          {/* 1. Core Dynamic Metric Cards */}
          <DashboardMetricCards
            metrics={dashboardData.metrics}
            currentFoir={dashboardData.current_foir_percentage}
          />

          {/* 2. Comprehensive Financial Health Score Card */}
          <FinancialHealthCard healthScore={dashboardData.health_score} />

          {/* 3. Executive Affordability & Risk Diagnostics */}
          <ExecutiveSummarySection dashboardData={dashboardData} />

          {/* 4. Quick Actions & Recent Activity Tools */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <QuickActions />
            <RecentActivity />
          </div>
        </div>
      )}
    </div>
  );
};

export default DashboardPage;
