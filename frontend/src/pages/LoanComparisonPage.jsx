import React from 'react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { GitCompare, CheckCircle2, ArrowRight } from 'lucide-react';

export const LoanComparisonPage = () => {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Multi-Loan Offer Comparison
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Compare up to 4 loan offers side-by-side to minimize interest and optimize repayment.
          </p>
        </div>
        <Badge variant="warning" size="md">
          Phase 6 Module
        </Badge>
      </div>

      <Card
        title="Side-by-Side Financial Evaluation"
        subtitle="Compare processing fees, APRs, and monthly burdens across lenders"
      >
        <div className="p-8 text-center max-w-xl mx-auto space-y-4">
          <div className="w-16 h-16 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center mx-auto border border-indigo-100">
            <GitCompare className="w-8 h-8" />
          </div>
          <h3 className="text-lg font-bold text-slate-900">
            Loan Comparison Module
          </h3>
          <p className="text-sm text-slate-500 leading-relaxed">
            Will feature interactive multi-column comparisons and Recharts stacked bar charts comparing total interest payout versus upfront fees across banks.
          </p>

          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200/80 text-left text-xs space-y-2">
            <div className="font-semibold text-slate-700">Planned Capabilities:</div>
            <div className="flex items-center gap-2 text-slate-600">
              <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
              <span>Side-by-side scenario modeling with save & export to PostgreSQL</span>
            </div>
            <div className="flex items-center gap-2 text-slate-600">
              <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
              <span>Net interest savings highlighting best recommendation</span>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
};
