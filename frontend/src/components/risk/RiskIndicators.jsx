/**
 * frontend/src/components/risk/RiskIndicators.jsx
 * ───────────────────────────────────────────────
 * Displays individual diagnostic financial risk indicators and triggered active warnings
 * evaluated by the FastAPI underwriting engine.
 */

import React from 'react';
import { Card } from '../common/Card';
import { Badge } from '../common/Badge';
import {
  ShieldCheck,
  AlertTriangle,
  AlertOctagon,
  Info,
  CheckCircle2,
  Percent,
  PiggyBank,
  Wallet,
  AlertCircle,
  Scale,
} from 'lucide-react';

const LEVEL_CONFIG = {
  LOW: {
    badgeVariant: 'success',
    colorText: 'text-emerald-700',
    colorBg: 'bg-emerald-50',
    borderColor: 'border-emerald-200',
    barColor: 'bg-emerald-500',
    icon: CheckCircle2,
    tag: 'Healthy / Low Risk',
  },
  MODERATE: {
    badgeVariant: 'info',
    colorText: 'text-sky-700',
    colorBg: 'bg-sky-50',
    borderColor: 'border-sky-200',
    barColor: 'bg-sky-500',
    icon: Info,
    tag: 'Moderate / Watch',
  },
  HIGH: {
    badgeVariant: 'warning',
    colorText: 'text-amber-700',
    colorBg: 'bg-amber-50',
    borderColor: 'border-amber-200',
    barColor: 'bg-amber-500',
    icon: AlertTriangle,
    tag: 'High Risk / Elevated',
  },
  CRITICAL: {
    badgeVariant: 'danger',
    colorText: 'text-rose-700',
    colorBg: 'bg-rose-50',
    borderColor: 'border-rose-200',
    barColor: 'bg-rose-500',
    icon: AlertOctagon,
    tag: 'Critical / Action Required',
  },
};

const INDICATOR_ICONS = {
  FOIR: Scale,
  EMERGENCY_FUND: PiggyBank,
  DISPOSABLE_INCOME: Wallet,
  OVERLEVERAGING: Percent,
};

export const RiskIndicators = ({ indicators = [], warnings = [] }) => {
  return (
    <div className="space-y-5">
      {/* Active Triggered Warnings Banner (if any) */}
      {warnings && warnings.length > 0 && (
        <div className="p-4 rounded-2xl bg-rose-50/90 border border-rose-200/90 shadow-subtle space-y-2.5">
          <div className="flex items-center gap-2 text-rose-900 font-bold text-sm">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>Active Financial Risk Warnings ({warnings.length})</span>
          </div>

          <div className="space-y-1.5 pl-6">
            {warnings.map((warning, idx) => (
              <div key={idx} className="flex items-start gap-2 text-xs text-rose-800 leading-relaxed">
                <span className="w-1.5 h-1.5 rounded-full bg-rose-500 shrink-0 mt-1.5" />
                <span>{warning}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Grid of 4 Diagnostic Indicators */}
      <Card
        title="Diagnostic Risk Indicators"
        subtitle="Multi-factor evaluation breakdown across debt ratios, liquidity, and cash flow"
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {indicators.map((ind) => {
            const level = ind.risk_level || 'LOW';
            const config = LEVEL_CONFIG[level] || LEVEL_CONFIG.LOW;
            const LevelIcon = config.icon;
            const IndicatorIcon = INDICATOR_ICONS[ind.indicator_key] || Info;
            const scoreVal = parseFloat(ind.score) || 0;

            return (
              <div
                key={ind.indicator_key}
                className="p-4 rounded-xl border border-slate-200/80 bg-white hover:border-slate-300 transition-colors shadow-subtle flex flex-col justify-between space-y-3"
              >
                {/* Header: Title, Icon, Value & Level Badge */}
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2.5">
                    <div className="p-2 rounded-lg bg-slate-50 text-slate-700 border border-slate-200/60">
                      <IndicatorIcon className="w-4 h-4 text-brand-600" />
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-slate-900 tracking-tight">
                        {ind.indicator_name}
                      </h4>
                      <span className="text-[11px] font-mono font-bold text-slate-500">
                        {ind.value_display}
                      </span>
                    </div>
                  </div>

                  <span
                    className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold border ${config.colorBg} ${config.colorText} ${config.borderColor}`}
                  >
                    <LevelIcon className="w-3 h-3" />
                    <span>{level}</span>
                  </span>
                </div>

                {/* Score Bar */}
                <div className="space-y-1">
                  <div className="flex justify-between text-[10px] font-semibold text-slate-500">
                    <span>Risk Severity</span>
                    <span>{scoreVal.toFixed(1)} / 100</span>
                  </div>
                  <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                    <div
                      style={{ width: `${Math.min(100, scoreVal)}%` }}
                      className={`h-full ${config.barColor} transition-all duration-500 rounded-full`}
                    />
                  </div>
                </div>

                {/* Contextual Narrative */}
                <p className="text-[11px] text-slate-600 leading-relaxed bg-slate-50/70 p-2.5 rounded-lg border border-slate-100">
                  {ind.explanation}
                </p>
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
};

export default RiskIndicators;
