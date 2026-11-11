import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '../common/Card';
import { Badge } from '../common/Badge';
import { Button } from '../common/Button';
import {
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  Info,
  TrendingUp,
  Percent,
  Wallet,
  PiggyBank,
  Sparkles,
} from 'lucide-react';

export const FinancialHealthCard = ({ healthScore }) => {
  const navigate = useNavigate();
  if (!healthScore) return null;

  const scoreNum = parseFloat(healthScore.overall_score || 0);
  const letterGrade = healthScore.letter_grade || 'N/A';
  const statusLabel = healthScore.status_label || 'Calculated Health Score';
  const summary = healthScore.summary || '';
  const subScores = healthScore.sub_scores || [];

  // Determine styling palette based on letter grade & score
  const getGradeTheme = (grade) => {
    switch (grade) {
      case 'A+':
      case 'A':
        return {
          textColor: 'text-emerald-600',
          badgeVariant: 'success',
          barColor: 'bg-emerald-500',
          ringBg: 'from-emerald-50/60 to-white',
          borderColor: 'border-emerald-200/80',
          icon: ShieldCheck,
          iconColor: 'text-emerald-600',
        };
      case 'B':
        return {
          textColor: 'text-blue-600',
          badgeVariant: 'primary',
          barColor: 'bg-blue-500',
          ringBg: 'from-blue-50/60 to-white',
          borderColor: 'border-blue-200/80',
          icon: ShieldCheck,
          iconColor: 'text-blue-600',
        };
      case 'C':
        return {
          textColor: 'text-amber-600',
          badgeVariant: 'warning',
          barColor: 'bg-amber-500',
          ringBg: 'from-amber-50/60 to-white',
          borderColor: 'border-amber-200/80',
          icon: AlertTriangle,
          iconColor: 'text-amber-600',
        };
      case 'D':
        return {
          textColor: 'text-orange-600',
          badgeVariant: 'warning',
          barColor: 'bg-orange-500',
          ringBg: 'from-orange-50/60 to-white',
          borderColor: 'border-orange-200/80',
          icon: AlertTriangle,
          iconColor: 'text-orange-600',
        };
      case 'F':
      default:
        return {
          textColor: 'text-rose-600',
          badgeVariant: 'danger',
          barColor: 'bg-rose-500',
          ringBg: 'from-rose-50/60 to-white',
          borderColor: 'border-rose-200/80',
          icon: ShieldAlert,
          iconColor: 'text-rose-600',
        };
    }
  };

  const theme = getGradeTheme(letterGrade);
  const StatusIcon = theme.icon;

  const getSubScoreIcon = (name) => {
    if (name.includes('FOIR')) return Percent;
    if (name.includes('Debt Burden')) return Wallet;
    if (name.includes('Emergency')) return ShieldCheck;
    if (name.includes('Savings')) return PiggyBank;
    return TrendingUp;
  };

  const getSubScoreBadgeVariant = (status) => {
    const s = (status || '').toLowerCase();
    if (s.includes('optimal') || s.includes('healthy') || s.includes('no debt')) return 'success';
    if (s.includes('adequate') || s.includes('moderate')) return 'warning';
    if (s.includes('stretched') || s.includes('low') || s.includes('vulnerable')) return 'warning';
    if (s.includes('critical') || s.includes('distress')) return 'danger';
    return 'default';
  };

  return (
    <Card
      title="Financial Health Score"
      subtitle="Deterministic composite index across debt servicing, liquidity, and obligations"
      headerAction={
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            icon={Sparkles}
            onClick={() => navigate('/ai-advisor?context=HEALTH_SCORE')}
            className="text-purple-700 border-purple-200 hover:bg-purple-50 text-xs py-1 px-2.5 h-8 font-medium"
          >
            Explain with AI
          </Button>
          <Badge variant={theme.badgeVariant} size="md" className="font-bold">
            Grade {letterGrade}
          </Badge>
          <span className="text-xs font-semibold text-slate-600 hidden sm:inline">
            {statusLabel}
          </span>
        </div>
      }
    >
      <div className="flex flex-col lg:flex-row items-stretch gap-6 py-2">
        {/* Score Ring / Numerical Gauge */}
        <div
          className={`flex flex-col items-center justify-center p-6 rounded-2xl bg-gradient-to-b ${theme.ringBg} border ${theme.borderColor} shadow-subtle w-full lg:w-56 text-center shrink-0`}
        >
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">
            Overall Health Index
          </div>
          <div className="text-5xl font-black tracking-tight text-slate-900 flex items-baseline justify-center">
            <span className={theme.textColor}>{scoreNum.toFixed(1)}</span>
            <span className="text-base font-semibold text-slate-400 ml-1">/100</span>
          </div>

          <div className="flex items-center gap-1.5 mt-2.5 px-3 py-1 rounded-full bg-white/90 border border-slate-200/80 shadow-xs">
            <StatusIcon className={`w-4 h-4 ${theme.iconColor}`} />
            <span className="text-xs font-bold text-slate-800">
              Grade {letterGrade} · {statusLabel}
            </span>
          </div>

          {/* Linear Meter Gauge */}
          <div className="w-full bg-slate-200/80 h-2 rounded-full mt-4 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-700 ease-out ${theme.barColor}`}
              style={{ width: `${Math.min(100, Math.max(0, scoreNum))}%` }}
            />
          </div>

          <p className="text-[11px] text-slate-500 mt-2.5 leading-snug">
            {summary}
          </p>
        </div>

        {/* 4-Factor Weighted Sub-scores Grid */}
        <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-3.5">
          {subScores.map((sub, idx) => {
            const SubIcon = getSubScoreIcon(sub.name);
            const subScoreNum = parseFloat(sub.score || 0);
            const weightNum = parseFloat(sub.weight_percentage || 0);
            const weightedNum = parseFloat(sub.weighted_score || 0);
            const badgeVariant = getSubScoreBadgeVariant(sub.status);

            return (
              <div
                key={sub.name || idx}
                className="p-4 rounded-xl bg-slate-50/70 border border-slate-200/70 hover:border-slate-300 transition-colors flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <div className="p-1.5 rounded-lg bg-white border border-slate-200 text-slate-600">
                        <SubIcon className="w-3.5 h-3.5" />
                      </div>
                      <h4 className="text-xs font-bold text-slate-800 tracking-tight">
                        {sub.name}
                      </h4>
                    </div>
                    <Badge variant={badgeVariant} size="sm">
                      {sub.status}
                    </Badge>
                  </div>

                  <div className="flex items-baseline justify-between mt-3">
                    <div className="text-xl font-extrabold text-slate-900 tracking-tight">
                      {subScoreNum.toFixed(1)}
                      <span className="text-xs font-medium text-slate-400 ml-1">/100</span>
                    </div>
                    <div className="text-[11px] font-semibold text-slate-500">
                      Contribution: <span className="text-slate-800">{weightedNum.toFixed(1)} pts</span>
                      <span className="text-slate-400 font-normal"> ({weightNum.toFixed(0)}% weight)</span>
                    </div>
                  </div>

                  {/* Sub-score progress mini-bar */}
                  <div className="w-full bg-slate-200/70 h-1.5 rounded-full mt-2 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        subScoreNum >= 75
                          ? 'bg-emerald-500'
                          : subScoreNum >= 50
                          ? 'bg-amber-500'
                          : 'bg-rose-500'
                      }`}
                      style={{ width: `${Math.min(100, Math.max(0, subScoreNum))}%` }}
                    />
                  </div>
                </div>

                <div className="text-[11px] text-slate-500 mt-2.5 pt-2 border-t border-slate-200/60 leading-relaxed">
                  {sub.detail}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="mt-4 pt-3.5 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500 flex-wrap gap-2">
        <div className="flex items-center gap-1.5">
          <Info className="w-4 h-4 text-brand-600 shrink-0" />
          <span>
            Computed with 100% deterministic Decimal precision: <code className="text-slate-700 bg-slate-100 px-1 py-0.5 rounded text-[11px]">Score = (0.35 × FOIR) + (0.30 × Debt) + (0.20 × Emergency) + (0.15 × Reserve)</code>
          </span>
        </div>
      </div>
    </Card>
  );
};

export default FinancialHealthCard;
