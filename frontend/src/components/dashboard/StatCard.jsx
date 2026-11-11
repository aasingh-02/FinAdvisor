import React from 'react';
import { Card } from '../common/Card';

export const StatCard = ({
  title,
  value,
  subtext,
  icon: Icon,
  iconColor = 'text-brand-600 bg-brand-50 border-brand-100',
  changeText,
  changeType = 'neutral', // 'positive' | 'negative' | 'neutral'
}) => {
  return (
    <Card className="hover:border-slate-300 transition-all">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            {title}
          </p>
          <h3 className="text-2xl font-bold text-slate-900 mt-1.5 tracking-tight">
            {value}
          </h3>
        </div>
        {Icon && (
          <div className={`p-2.5 rounded-xl border ${iconColor} shrink-0`}>
            <Icon className="w-5 h-5" />
          </div>
        )}
      </div>

      {(subtext || changeText) && (
        <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
          {subtext && <span className="text-slate-500">{subtext}</span>}
          {changeText && (
            <span
              className={`font-semibold ${
                changeType === 'positive'
                  ? 'text-emerald-600'
                  : changeType === 'negative'
                  ? 'text-rose-600'
                  : 'text-slate-600'
              }`}
            >
              {changeText}
            </span>
          )}
        </div>
      )}
    </Card>
  );
};
