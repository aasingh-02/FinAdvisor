import React from 'react';
import { Link } from 'react-router-dom';
import { Card } from '../common/Card';
import { Badge } from '../common/Badge';
import {
  ShieldAlert,
  ShieldCheck,
  Percent,
  Sparkles,
  ArrowRight,
  AlertTriangle,
  CheckCircle2,
  ListChecks,
  Bot,
} from 'lucide-react';
import { formatINR } from '../../utils/formatCurrency';

export const ExecutiveSummarySection = ({ dashboardData }) => {
  if (!dashboardData) return null;

  const {
    current_foir_percentage,
    foir_status,
    overall_risk_category,
    overall_risk_score,
    is_borrowing_eligible,
    prudent_max_borrowing_emi,
    top_recommendation_summary,
    active_warnings = [],
    actionable_highlights = [],
  } = dashboardData;

  const foirNum = parseFloat(current_foir_percentage || 0);
  const riskScoreNum = parseFloat(overall_risk_score || 0);
  const maxEmiNum = parseFloat(prudent_max_borrowing_emi || 0);

  const getRiskBadgeVariant = (cat) => {
    switch ((cat || '').toUpperCase()) {
      case 'LOW':
        return 'success';
      case 'MODERATE':
        return 'warning';
      case 'HIGH':
      case 'CRITICAL':
        return 'danger';
      default:
        return 'default';
    }
  };

  const getFoirBadgeVariant = (status) => {
    switch ((status || '').toLowerCase()) {
      case 'optimal':
        return 'success';
      case 'manageable':
        return 'primary';
      case 'stretched':
        return 'warning';
      case 'critical':
        return 'danger';
      default:
        return 'default';
    }
  };

  return (
    <div className="space-y-6">
      {/* Affordability & Risk Executive Banner */}
      <Card
        title="Executive Affordability & Borrowing Snapshot"
        subtitle="Key diagnostic indicators evaluating borrowing headroom and debt safety margins"
        headerAction={
          <div className="flex items-center gap-2">
            <Link
              to="/ai-advisor?context=RISK_ASSESSMENT"
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-purple-700 bg-purple-50 hover:bg-purple-100 border border-purple-200 px-2.5 py-1 rounded-lg transition-colors"
            >
              <Bot className="w-3.5 h-3.5 text-purple-600" />
              <span>Ask Copilot</span>
            </Link>
            <Badge
              variant={is_borrowing_eligible ? 'success' : 'danger'}
              size="md"
              className="font-semibold"
            >
              {is_borrowing_eligible ? 'Borrowing Feasible' : 'Borrowing Inadvisable'}
            </Badge>
          </div>
        }
      >
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pb-4 border-b border-slate-100">
          {/* Diagnostic 1: FOIR */}
          <div className="p-4 rounded-xl bg-slate-50/70 border border-slate-200/80 flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Current FOIR
              </span>
              <Badge variant={getFoirBadgeVariant(foir_status)} size="sm">
                {foir_status || 'Evaluated'}
              </Badge>
            </div>
            <div className="mt-2">
              <div className="text-2xl font-black text-slate-900 tracking-tight flex items-baseline gap-1">
                <Percent className="w-4 h-4 text-slate-400" />
                <span>{foirNum.toFixed(1)}%</span>
              </div>
              <p className="text-[11px] text-slate-500 mt-1">
                Fixed obligations vs take-home income
              </p>
            </div>
            <Link
              to="/loan-calculator"
              className="mt-3 pt-2 border-t border-slate-200/70 flex items-center justify-between text-xs font-semibold text-brand-600 hover:text-brand-700 transition-colors"
            >
              <span>FOIR Calculator</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {/* Diagnostic 2: Risk Category */}
          <div className="p-4 rounded-xl bg-slate-50/70 border border-slate-200/80 flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Overall Risk
              </span>
              <Badge variant={getRiskBadgeVariant(overall_risk_category)} size="sm">
                {overall_risk_category || 'Assessed'}
              </Badge>
            </div>
            <div className="mt-2">
              <div className="text-2xl font-black text-slate-900 tracking-tight flex items-baseline gap-1">
                <ShieldAlert className="w-5 h-5 text-slate-400" />
                <span>{riskScoreNum.toFixed(1)}</span>
                <span className="text-xs text-slate-400 font-medium">/100 risk</span>
              </div>
              <p className="text-[11px] text-slate-500 mt-1">
                Multi-dimensional risk assessment score
              </p>
            </div>
            <Link
              to="/risk-assessment"
              className="mt-3 pt-2 border-t border-slate-200/70 flex items-center justify-between text-xs font-semibold text-brand-600 hover:text-brand-700 transition-colors"
            >
              <span>Risk Diagnostics</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {/* Diagnostic 3: Prudent Max EMI */}
          <div className="p-4 rounded-xl bg-slate-50/70 border border-slate-200/80 flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Safe Borrowing Limit
              </span>
              <Badge variant={is_borrowing_eligible ? 'success' : 'danger'} size="sm">
                {is_borrowing_eligible ? 'Safe Capacity' : 'Zero Capacity'}
              </Badge>
            </div>
            <div className="mt-2">
              <div className="text-2xl font-black text-slate-900 tracking-tight">
                {formatINR(maxEmiNum, false)}
                <span className="text-xs text-slate-400 font-medium">/month</span>
              </div>
              <p className="text-[11px] text-slate-500 mt-1">
                Prudent maximum new loan EMI headroom
              </p>
            </div>
            <Link
              to="/loan-recommendations"
              className="mt-3 pt-2 border-t border-slate-200/70 flex items-center justify-between text-xs font-semibold text-brand-600 hover:text-brand-700 transition-colors"
            >
              <span>View Recommendations</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>

        {/* Top Recommendation Summary */}
        {top_recommendation_summary && (
          <div className="mt-4 p-4 rounded-xl bg-brand-50/60 border border-brand-100 flex items-start gap-3">
            <Sparkles className="w-5 h-5 text-brand-600 shrink-0 mt-0.5" />
            <div className="flex-1">
              <h4 className="text-xs font-bold uppercase tracking-wider text-brand-900">
                Personalized Recommendation Summary
              </h4>
              <p className="text-xs text-brand-950 mt-1 leading-relaxed">
                {top_recommendation_summary}
              </p>
            </div>
            <Link
              to="/loan-recommendations"
              className="hidden sm:inline-flex items-center gap-1 text-xs font-bold text-brand-700 hover:text-brand-800 bg-white px-3 py-1.5 rounded-lg border border-brand-200 shadow-xs shrink-0 hover:bg-brand-50 transition-colors"
            >
              <span>Explore Loans</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        )}
      </Card>

      {/* Cautionary Warnings & Actionable Next Steps */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Active Alerts */}
        <Card
          title="Active Financial Cautionary Notes"
          subtitle="Alerts triggered by FOIR threshold, emergency funds, or cash deficit"
          headerAction={
            <Badge variant={active_warnings.length > 0 ? 'warning' : 'success'} size="sm">
              {active_warnings.length} {active_warnings.length === 1 ? 'Alert' : 'Alerts'}
            </Badge>
          }
        >
          {active_warnings.length === 0 ? (
            <div className="py-6 text-center text-slate-500 flex flex-col items-center">
              <CheckCircle2 className="w-8 h-8 text-emerald-500 mb-2" />
              <p className="text-xs font-medium text-slate-700">No critical alerts detected.</p>
              <p className="text-[11px] text-slate-400 mt-0.5">Your financial profile is within safe parameters.</p>
            </div>
          ) : (
            <div className="space-y-2.5">
              {active_warnings.map((warn, i) => (
                <div
                  key={i}
                  className="p-3 rounded-xl bg-amber-50/70 border border-amber-200/80 text-amber-900 text-xs flex items-start gap-2.5 leading-relaxed"
                >
                  <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                  <span>{warn}</span>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Actionable Next Steps */}
        <Card
          title="Prioritized Next Financial Steps"
          subtitle="Concrete actions derived from your actual debt and savings profile"
          headerAction={
            <Badge variant="primary" size="sm">
              {actionable_highlights.length} {actionable_highlights.length === 1 ? 'Action' : 'Actions'}
            </Badge>
          }
        >
          {actionable_highlights.length === 0 ? (
            <div className="py-6 text-center text-slate-500 flex flex-col items-center">
              <CheckCircle2 className="w-8 h-8 text-emerald-500 mb-2" />
              <p className="text-xs font-medium text-slate-700">Financial plan is balanced.</p>
              <p className="text-[11px] text-slate-400 mt-0.5">Maintain current debt obligations and emergency reserves.</p>
            </div>
          ) : (
            <div className="space-y-2.5">
              {actionable_highlights.map((act, i) => (
                <div
                  key={i}
                  className="p-3 rounded-xl bg-slate-50/90 border border-slate-200/80 text-slate-800 text-xs flex items-start gap-2.5 leading-relaxed"
                >
                  <ListChecks className="w-4 h-4 text-brand-600 shrink-0 mt-0.5" />
                  <span>{act}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
};

export default ExecutiveSummarySection;
