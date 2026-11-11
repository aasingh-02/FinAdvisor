import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '../common/Card';
import { Badge } from '../common/Badge';
import { Button } from '../common/Button';
import { useAdvisorStatus } from '../../context/AdvisorStatusContext';
import { getGroundTruthGuardrailText } from '../../utils/advisorProvider';
import { formatINR } from '../../utils/formatCurrency';
import {
  ShieldCheck,
  ShieldAlert,
  Wallet,
  PiggyBank,
  Percent,
  TrendingUp,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Lock,
} from 'lucide-react';

const ProviderStatusFooter = ({ provider, includeGuardrailCopy = false }) => (
  <div className="text-[11px] text-slate-600 bg-slate-50 p-2.5 rounded-lg border border-slate-100 space-y-1.5">
    <div className="flex items-center justify-between gap-2">
      <span className="font-semibold text-slate-700">Active Provider</span>
      <Badge
        variant={provider.isGemini ? 'primary' : 'default'}
        size="sm"
        className="text-[10px]"
      >
        {provider.label}
      </Badge>
    </div>
    {includeGuardrailCopy && (
      <div className="text-[10px] text-slate-500 flex items-center gap-1.5">
        <ShieldCheck className="w-3.5 h-3.5 text-brand-600 shrink-0" />
        <span>{getGroundTruthGuardrailText(provider)}</span>
      </div>
    )}
  </div>
);

export const VerifiedSnapshotSidebar = ({ snapshot, providerStatus }) => {
  const navigate = useNavigate();
  const { advisorProvider } = useAdvisorStatus();
  const provider = providerStatus || advisorProvider;

  if (!snapshot) {
    return (
      <Card
        title="Verified Financial Snapshot"
        subtitle="Deterministic backend figures"
        className="h-fit sticky top-6"
      >
        <div className="space-y-4">
          <div className="text-center py-6 px-2 space-y-3">
            <div className="w-12 h-12 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center mx-auto border border-amber-100">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <h4 className="text-sm font-semibold text-slate-900">
              Profile Not Initialized
            </h4>
            <p className="text-xs text-slate-500 leading-relaxed">
              Complete your financial profile to ground the AI Advisor on your verified income, FOIR, and borrowing limits.
            </p>
            <Button
              size="sm"
              variant="primary"
              className="w-full"
              icon={ArrowRight}
              onClick={() => navigate('/profile')}
            >
              Setup Profile
            </Button>
          </div>
          <ProviderStatusFooter provider={provider} />
        </div>
      </Card>
    );
  }

  const income = parseFloat(snapshot.monthly_net_income || 0);
  const emi = parseFloat(snapshot.existing_monthly_emi || 0);
  const expenses = parseFloat(snapshot.monthly_living_expenses || 0);
  const disposable = parseFloat(snapshot.disposable_monthly_cash_flow || 0);
  const emergencyTotal = parseFloat(snapshot.emergency_savings_total || 0);
  const emergencyMonths = parseFloat(snapshot.emergency_fund_months || 0);
  const foirPct = parseFloat(snapshot.current_foir_percentage || 0);
  const healthScore = snapshot.overall_health_score !== null ? parseFloat(snapshot.overall_health_score) : null;
  const grade = snapshot.letter_grade || 'N/A';
  const isEligible = Boolean(snapshot.is_borrowing_eligible);
  const prudentMaxEmi = parseFloat(snapshot.prudent_max_monthly_emi || 0);

  // Grade color
  const getGradeBadge = (g) => {
    switch (g) {
      case 'A+':
      case 'A':
        return <Badge variant="success" size="sm">{g} Rating</Badge>;
      case 'B':
        return <Badge variant="primary" size="sm">{g} Rating</Badge>;
      case 'C':
        return <Badge variant="warning" size="sm">{g} Rating</Badge>;
      default:
        return <Badge variant="danger" size="sm">{g} Rating</Badge>;
    }
  };

  return (
    <Card
      title="Financial Ground Truth"
      subtitle="Deterministically verified by backend"
      headerAction={
        <div className="flex items-center gap-1 text-[11px] font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-200">
          <Lock className="w-3 h-3 text-emerald-600" />
          <span>Verified Data</span>
        </div>
      }
      className="h-fit sticky top-6"
    >
      <div className="space-y-4">
        {/* Health Score Overview */}
        {healthScore !== null && (
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 flex items-center justify-between">
            <div>
              <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">Health Score</p>
              <p className="text-xl font-bold text-slate-900 mt-0.5">{healthScore.toFixed(1)}<span className="text-xs font-normal text-slate-500"> / 100</span></p>
            </div>
            <div>{getGradeBadge(grade)}</div>
          </div>
        )}

        {/* Core Financial Metrics */}
        <div className="space-y-2.5 text-xs">
          <div className="flex items-center justify-between py-1 border-b border-slate-100">
            <span className="text-slate-500 flex items-center gap-1.5">
              <Wallet className="w-3.5 h-3.5 text-slate-400" />
              Net Income
            </span>
            <span className="font-semibold text-slate-900">{formatINR(income)}</span>
          </div>

          <div className="flex items-center justify-between py-1 border-b border-slate-100">
            <span className="text-slate-500 flex items-center gap-1.5">
              <Percent className="w-3.5 h-3.5 text-slate-400" />
              Current EMIs
            </span>
            <span className="font-semibold text-slate-900">{formatINR(emi)}</span>
          </div>

          <div className="flex items-center justify-between py-1 border-b border-slate-100">
            <span className="text-slate-500 flex items-center gap-1.5">
              <TrendingUp className="w-3.5 h-3.5 text-slate-400" />
              FOIR Ratio
            </span>
            <div className="text-right">
              <span className="font-semibold text-slate-900">{foirPct.toFixed(1)}%</span>
              <span className="text-[10px] text-slate-500 ml-1.5">({snapshot.foir_status})</span>
            </div>
          </div>

          <div className="flex items-center justify-between py-1 border-b border-slate-100">
            <span className="text-slate-500 flex items-center gap-1.5">
              <Wallet className="w-3.5 h-3.5 text-slate-400" />
              Cash Flow
            </span>
            <span className={`font-semibold ${disposable >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
              {disposable >= 0 ? `+${formatINR(disposable)}` : `-${formatINR(Math.abs(disposable))}`}
            </span>
          </div>

          <div className="flex items-center justify-between py-1 border-b border-slate-100">
            <span className="text-slate-500 flex items-center gap-1.5">
              <PiggyBank className="w-3.5 h-3.5 text-slate-400" />
              Emergency Fund
            </span>
            <span className="font-semibold text-slate-900">
              {emergencyMonths.toFixed(1)} mos ({formatINR(emergencyTotal)})
            </span>
          </div>
        </div>

        {/* Borrowing Capacity verdict */}
        <div className={`p-3 rounded-xl border ${isEligible ? 'bg-emerald-50/60 border-emerald-200' : 'bg-rose-50/60 border-rose-200'}`}>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-800">Borrowing Capacity</span>
            <Badge variant={isEligible ? 'success' : 'danger'} size="sm">
              {isEligible ? 'Eligible' : 'Inadvisable'}
            </Badge>
          </div>
          <p className="text-xs text-slate-600 mt-1">
            Prudent Max EMI: <strong className="text-slate-900">{formatINR(prudentMaxEmi)}/mo</strong>
          </p>
        </div>

        {/* AI Guardrail Transparency */}
        <ProviderStatusFooter provider={provider} includeGuardrailCopy />
      </div>
    </Card>
  );
};

export default VerifiedSnapshotSidebar;
