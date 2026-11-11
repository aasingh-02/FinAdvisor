import React from 'react';
import { Link } from 'react-router-dom';
import { Card } from '../common/Card';
import { Button } from '../common/Button';
import {
  UserCheck,
  ShieldCheck,
  ArrowRight,
  Sparkles,
  PieChart,
  Wallet,
  Calculator,
} from 'lucide-react';

export const ProfileIncompleteBanner = ({ warningMessage }) => {
  return (
    <Card className="border-brand-200 bg-gradient-to-br from-brand-50/50 via-white to-slate-50 overflow-hidden shadow-card">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="flex items-start gap-4">
          <div className="p-3.5 rounded-2xl bg-brand-600 text-white shadow-md shrink-0">
            <UserCheck className="w-7 h-7" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-slate-900 tracking-tight">
                Complete Your Financial Profile
              </h2>
              <span className="text-[11px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-brand-100 text-brand-800">
                Action Required
              </span>
            </div>
            <p className="text-xs sm:text-sm text-slate-600 mt-1.5 max-w-2xl leading-relaxed">
              {warningMessage ||
                'Financial profile not yet initialized. Please complete your profile to unlock personalized health scoring, risk metrics, and loan recommendations.'}
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-4 pt-3 border-t border-brand-100/80 text-xs text-slate-600">
              <div className="flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>Deterministic Financial Health Score (0–100)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <PieChart className="w-4 h-4 text-brand-600 shrink-0" />
                <span>Fixed Obligation to Income Ratio (FOIR)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Wallet className="w-4 h-4 text-purple-600 shrink-0" />
                <span>Multi-factor debt and liquidity diagnostics</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Sparkles className="w-4 h-4 text-amber-600 shrink-0" />
                <span>Tailored 4-category loan sizing recommendations</span>
              </div>
            </div>
          </div>
        </div>

        <div className="shrink-0 self-stretch md:self-auto flex flex-col items-center gap-2">
          <Link to="/profile" className="w-full md:w-auto">
            <Button
              variant="primary"
              size="md"
              className="w-full justify-center shadow-sm font-semibold"
            >
              <span>Initialize Profile</span>
              <ArrowRight className="w-4 h-4 ml-1.5" />
            </Button>
          </Link>
          <span className="text-[11px] text-slate-400">Takes less than 2 minutes</span>
        </div>
      </div>
    </Card>
  );
};

export default ProfileIncompleteBanner;
