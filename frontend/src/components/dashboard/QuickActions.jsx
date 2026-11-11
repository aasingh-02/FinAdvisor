import React from 'react';
import { Link } from 'react-router-dom';
import { Card } from '../common/Card';
import { Calculator, Percent, GitCompare, Bot, ArrowRight, Sparkles } from 'lucide-react';

const actions = [
  {
    title: 'Calculate Affordability',
    description: 'Determine your maximum safe borrowing capacity based on FOIR',
    to: '/loan-calculator',
    icon: Calculator,
    iconColor: 'bg-brand-50 text-brand-600',
  },
  {
    title: 'Personalized Recommendations',
    description: 'Prudent loan sizing across 4 categories based on your cash flow',
    to: '/loan-recommendations',
    icon: Sparkles,
    iconColor: 'bg-indigo-50 text-indigo-600',
  },
  {
    title: 'EMI Simulator',
    description: 'Simulate monthly payments and total interest across custom tenures',
    to: '/emi-calculator',
    icon: Percent,
    iconColor: 'bg-emerald-50 text-emerald-600',
  },
  {
    title: 'Ask AI Advisor',
    description: 'Get plain-English explanations of your financial risk ratios',
    to: '/ai-advisor',
    icon: Bot,
    iconColor: 'bg-purple-50 text-purple-600',
  },
];

export const QuickActions = () => {
  return (
    <Card
      title="Quick Actions"
      subtitle="Launch financial calculation engines and advisory tools"
    >
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
        {actions.map((act) => {
          const Icon = act.icon;
          return (
            <Link
              key={act.to}
              to={act.to}
              className="p-4 rounded-xl border border-slate-200/80 hover:border-brand-300 hover:shadow-subtle transition-all bg-white hover:bg-brand-50/20 group flex flex-col justify-between"
            >
              <div className="flex items-start gap-3">
                <div className={`p-2 rounded-lg ${act.iconColor} shrink-0`}>
                  <Icon className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-slate-900 group-hover:text-brand-700 transition-colors">
                    {act.title}
                  </h4>
                  <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                    {act.description}
                  </p>
                </div>
              </div>
              <div className="mt-3 pt-2 border-t border-slate-100 flex items-center justify-end text-xs font-semibold text-brand-600 group-hover:translate-x-0.5 transition-transform">
                <span>Open Tool</span>
                <ArrowRight className="w-3.5 h-3.5 ml-1" />
              </div>
            </Link>
          );
        })}
      </div>
    </Card>
  );
};
