import React from 'react';
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
} from 'recharts';
import { formatINR } from '../../utils/formatCurrency';

const COLORS = {
  principal: '#0c87eb', // Brand Blue
  interest: '#f59e0b',  // Warm Amber
};

export const EMIBreakdownChart = ({
  principalAmount = 0,
  totalInterest = 0,
  principalPercentage = 100,
  interestPercentage = 0,
  totalRepayment = 0,
}) => {
  const pVal = parseFloat(principalAmount) || 0;
  const iVal = parseFloat(totalInterest) || 0;

  // Chart data: if interest is 0, chart only renders the principal slice
  const chartData = [
    { name: 'Principal Amount', value: pVal, color: COLORS.principal },
    ...(iVal > 0 ? [{ name: 'Total Interest', value: iVal, color: COLORS.interest }] : []),
  ];

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0];
      const isPrincipal = data.name === 'Principal Amount';
      const pct = isPrincipal ? principalPercentage : interestPercentage;
      return (
        <div className="bg-slate-900 text-white px-3.5 py-2.5 rounded-xl shadow-xl text-xs space-y-1 border border-slate-700">
          <div className="flex items-center gap-2 font-medium">
            <span
              className="w-2.5 h-2.5 rounded-full"
              style={{ backgroundColor: data.payload.color }}
            />
            <span>{data.name}</span>
          </div>
          <div className="text-base font-bold text-white tracking-tight">
            {formatINR(data.value, true)}
          </div>
          <div className="text-[11px] text-slate-400">
            {pct}% of Total Repayment
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="flex flex-col items-center justify-center w-full">
      {/* Donut Chart Container */}
      <div className="relative w-full h-64 sm:h-72">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius="65%"
              outerRadius="88%"
              paddingAngle={iVal > 0 ? 3 : 0}
              dataKey="value"
              stroke="none"
              animationDuration={600}
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
          </PieChart>
        </ResponsiveContainer>

        {/* Center Donut Metrics */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none text-center px-4">
          <span className="text-[11px] font-semibold tracking-wider uppercase text-slate-400">
            Total Repayment
          </span>
          <span className="text-lg sm:text-xl font-extrabold text-slate-900 tracking-tight mt-0.5">
            {formatINR(totalRepayment, false)}
          </span>
          <span className="text-[11px] text-slate-500 font-medium mt-0.5">
            Principal + Interest
          </span>
        </div>
      </div>

      {/* Custom Legend */}
      <div className="grid grid-cols-2 gap-4 w-full pt-4 border-t border-slate-100 text-xs">
        <div className="flex items-center gap-2.5 p-2.5 rounded-xl bg-slate-50 border border-slate-200/80">
          <span className="w-3 h-3 rounded-full bg-brand-500 shrink-0" />
          <div className="min-w-0 flex-1">
            <div className="text-slate-500 font-medium">Principal</div>
            <div className="font-bold text-slate-900 text-sm truncate">
              {formatINR(pVal, false)}
            </div>
            <div className="text-[10px] text-brand-600 font-semibold">
              {principalPercentage}%
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5 p-2.5 rounded-xl bg-slate-50 border border-slate-200/80">
          <span className="w-3 h-3 rounded-full bg-amber-500 shrink-0" />
          <div className="min-w-0 flex-1">
            <div className="text-slate-500 font-medium">Interest</div>
            <div className="font-bold text-slate-900 text-sm truncate">
              {formatINR(iVal, false)}
            </div>
            <div className="text-[10px] text-amber-600 font-semibold">
              {interestPercentage}%
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EMIBreakdownChart;
