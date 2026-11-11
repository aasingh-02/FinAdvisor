import React from 'react';
import { Card } from '../common/Card';
import { Badge } from '../common/Badge';
import { CheckCircle2, AlertTriangle, Clock, ArrowUpRight } from 'lucide-react';
import { Link } from 'react-router-dom';

const sampleActivities = [
  {
    id: 'act-1',
    title: 'Pre-Approved Home Loan Evaluation',
    type: 'Affordability',
    amount: '₹35,00,000 at 8.5%',
    date: '2 hours ago',
    status: 'Safe',
    statusVariant: 'success',
  },
  {
    id: 'act-2',
    title: 'Auto Loan Refinance Scenario',
    type: 'EMI Check',
    amount: '₹8,50,000 at 9.2%',
    date: 'Yesterday',
    status: 'Moderate',
    statusVariant: 'warning',
  },
  {
    id: 'act-3',
    title: 'Personal Loan Affordability Simulation',
    type: 'FOIR Alert',
    amount: '₹2,50,000 at 13.5%',
    date: '3 days ago',
    status: 'Overleveraged',
    statusVariant: 'danger',
  },
];

export const RecentActivity = () => {
  return (
    <Card
      title="Recent Financial Evaluations"
      subtitle="History of your loan scenarios and affordability simulations"
      headerAction={
        <Link
          to="/loan-comparison"
          className="text-xs font-semibold text-brand-600 hover:text-brand-700 flex items-center gap-1 hover:underline"
        >
          View All <ArrowUpRight className="w-3.5 h-3.5" />
        </Link>
      }
      noPadding
    >
      <div className="divide-y divide-slate-100">
        {sampleActivities.map((act) => (
          <div
            key={act.id}
            className="px-6 py-4 flex items-center justify-between hover:bg-slate-50/60 transition-colors"
          >
            <div className="flex items-center gap-3.5">
              <div
                className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${
                  act.statusVariant === 'success'
                    ? 'bg-emerald-50 text-emerald-600'
                    : act.statusVariant === 'warning'
                    ? 'bg-amber-50 text-amber-600'
                    : 'bg-rose-50 text-rose-600'
                }`}
              >
                {act.statusVariant === 'success' ? (
                  <CheckCircle2 className="w-4 h-4" />
                ) : act.statusVariant === 'warning' ? (
                  <Clock className="w-4 h-4" />
                ) : (
                  <AlertTriangle className="w-4 h-4" />
                )}
              </div>
              <div>
                <div className="text-sm font-semibold text-slate-800">
                  {act.title}
                </div>
                <div className="text-xs text-slate-500 mt-0.5 flex items-center gap-2">
                  <span>{act.amount}</span>
                  <span className="text-slate-300">•</span>
                  <span>{act.date}</span>
                </div>
              </div>
            </div>

            <div className="text-right">
              <Badge variant={act.statusVariant} size="sm">
                {act.status}
              </Badge>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
};
