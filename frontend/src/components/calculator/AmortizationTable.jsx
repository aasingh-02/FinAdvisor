import React, { useState, useMemo } from 'react';
import { Card } from '../common/Card';
import { Badge } from '../common/Badge';
import { formatINR } from '../../utils/formatCurrency';
import { ChevronLeft, ChevronRight, Calendar, Layers, CheckCircle2 } from 'lucide-react';

export const AmortizationTable = ({ schedule = [] }) => {
  const [viewMode, setViewMode] = useState('yearly'); // 'yearly' | 'monthly'
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 12;

  // Build aggregated yearly summaries strictly from backend monthly data
  const yearlySchedule = useMemo(() => {
    if (!schedule || schedule.length === 0) return [];

    const years = [];
    const totalMonths = schedule.length;
    const totalYears = Math.ceil(totalMonths / 12);

    for (let y = 1; y <= totalYears; y++) {
      const startIdx = (y - 1) * 12;
      const endIdx = Math.min(y * 12, totalMonths);
      const yearMonths = schedule.slice(startIdx, endIdx);

      if (yearMonths.length === 0) continue;

      const openingBalance = parseFloat(yearMonths[0].opening_balance);
      const closingBalance = parseFloat(yearMonths[yearMonths.length - 1].closing_balance);
      const totalInstallment = yearMonths.reduce((sum, m) => sum + parseFloat(m.emi_amount), 0);
      const principalPaid = yearMonths.reduce((sum, m) => sum + parseFloat(m.principal_component), 0);
      const interestPaid = yearMonths.reduce((sum, m) => sum + parseFloat(m.interest_component), 0);

      years.push({
        year: y,
        monthRange: `${startIdx + 1} - ${endIdx}`,
        openingBalance,
        totalInstallment,
        principalPaid,
        interestPaid,
        closingBalance,
        isFinal: y === totalYears,
      });
    }

    return years;
  }, [schedule]);

  // Pagination for monthly view
  const totalMonthlyPages = Math.ceil((schedule?.length || 0) / itemsPerPage);
  const paginatedMonthly = useMemo(() => {
    if (!schedule) return [];
    const start = (currentPage - 1) * itemsPerPage;
    return schedule.slice(start, start + itemsPerPage);
  }, [schedule, currentPage]);

  if (!schedule || schedule.length === 0) {
    return (
      <Card title="Amortization Schedule">
        <div className="py-12 text-center text-slate-400 text-sm">
          No amortization schedule available. Enter loan parameters to calculate.
        </div>
      </Card>
    );
  }

  return (
    <Card
      title="Amortization Schedule"
      subtitle="Complete month-by-month and year-by-year repayment schedule"
      headerAction={
        <div className="flex items-center gap-1.5 p-1 bg-slate-100 rounded-lg">
          <button
            type="button"
            onClick={() => setViewMode('yearly')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors flex items-center gap-1.5 ${
              viewMode === 'yearly'
                ? 'bg-white text-slate-900 shadow-subtle'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Calendar className="w-3.5 h-3.5" />
            <span>Yearly Summary</span>
          </button>
          <button
            type="button"
            onClick={() => {
              setViewMode('monthly');
              setCurrentPage(1);
            }}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors flex items-center gap-1.5 ${
              viewMode === 'monthly'
                ? 'bg-white text-slate-900 shadow-subtle'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Monthly View ({schedule.length} mos)</span>
          </button>
        </div>
      }
      noPadding
    >
      <div className="overflow-x-auto">
        {viewMode === 'yearly' ? (
          /* ── Yearly View ── */
          <table className="w-full text-left text-xs text-slate-600 border-collapse">
            <thead className="bg-slate-50/80 border-b border-slate-200/80 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              <tr>
                <th className="py-3 px-4">Year</th>
                <th className="py-3 px-4 text-right">Opening Balance</th>
                <th className="py-3 px-4 text-right">Total Installment</th>
                <th className="py-3 px-4 text-right">Principal Repaid</th>
                <th className="py-3 px-4 text-right">Interest Paid</th>
                <th className="py-3 px-4 text-right">Closing Balance</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {yearlySchedule.map((row) => (
                <tr
                  key={`year-${row.year}`}
                  className={`hover:bg-slate-50/60 transition-colors ${
                    row.isFinal ? 'bg-emerald-50/30 font-medium' : ''
                  }`}
                >
                  <td className="py-3 px-4">
                    <div className="font-bold text-slate-900 flex items-center gap-1.5">
                      <span>Year {row.year}</span>
                      {row.isFinal && (
                        <Badge variant="success" size="sm" className="text-[10px] px-1.5 py-0">
                          Complete
                        </Badge>
                      )}
                    </div>
                    <div className="text-[10px] text-slate-400">
                      Months {row.monthRange}
                    </div>
                  </td>
                  <td className="py-3 px-4 text-right font-mono font-medium text-slate-800">
                    {formatINR(row.openingBalance, true)}
                  </td>
                  <td className="py-3 px-4 text-right font-mono font-bold text-slate-900">
                    {formatINR(row.totalInstallment, true)}
                  </td>
                  <td className="py-3 px-4 text-right font-mono text-brand-700 font-semibold">
                    {formatINR(row.principalPaid, true)}
                  </td>
                  <td className="py-3 px-4 text-right font-mono text-amber-700 font-semibold">
                    {formatINR(row.interestPaid, true)}
                  </td>
                  <td className="py-3 px-4 text-right font-mono font-bold text-slate-900">
                    {row.closingBalance === 0 ? (
                      <span className="text-emerald-600 flex items-center justify-end gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        ₹0.00
                      </span>
                    ) : (
                      formatINR(row.closingBalance, true)
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          /* ── Monthly View ── */
          <table className="w-full text-left text-xs text-slate-600 border-collapse">
            <thead className="bg-slate-50/80 border-b border-slate-200/80 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              <tr>
                <th className="py-3 px-4">Month</th>
                <th className="py-3 px-4 text-right">Opening Balance</th>
                <th className="py-3 px-4 text-right">Monthly EMI</th>
                <th className="py-3 px-4 text-right">Principal</th>
                <th className="py-3 px-4 text-right">Interest</th>
                <th className="py-3 px-4 text-right">Closing Balance</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {paginatedMonthly.map((row) => {
                const isFinalMonth = row.month === schedule.length;
                return (
                  <tr
                    key={`month-${row.month}`}
                    className={`hover:bg-slate-50/60 transition-colors ${
                      isFinalMonth ? 'bg-emerald-50/30 font-medium' : ''
                    }`}
                  >
                    <td className="py-3 px-4 font-bold text-slate-900">
                      Month {row.month}
                    </td>
                    <td className="py-3 px-4 text-right font-mono text-slate-800">
                      {formatINR(parseFloat(row.opening_balance), true)}
                    </td>
                    <td className="py-3 px-4 text-right font-mono font-bold text-slate-900">
                      {formatINR(parseFloat(row.emi_amount), true)}
                    </td>
                    <td className="py-3 px-4 text-right font-mono text-brand-700 font-semibold">
                      {formatINR(parseFloat(row.principal_component), true)}
                    </td>
                    <td className="py-3 px-4 text-right font-mono text-amber-700 font-semibold">
                      {formatINR(parseFloat(row.interest_component), true)}
                    </td>
                    <td className="py-3 px-4 text-right font-mono font-bold text-slate-900">
                      {parseFloat(row.closing_balance) === 0 ? (
                        <span className="text-emerald-600 flex items-center justify-end gap-1">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          ₹0.00
                        </span>
                      ) : (
                        formatINR(parseFloat(row.closing_balance), true)
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination Controls for Monthly View */}
      {viewMode === 'monthly' && totalMonthlyPages > 1 && (
        <div className="px-6 py-3.5 bg-slate-50/60 border-t border-slate-100 flex items-center justify-between text-xs">
          <span className="text-slate-500 font-medium">
            Page {currentPage} of {totalMonthlyPages} ({schedule.length} total installments)
          </span>

          <div className="flex items-center gap-1.5">
            <button
              type="button"
              disabled={currentPage === 1}
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              className="px-2.5 py-1.5 rounded-lg border border-slate-200 bg-white text-slate-700 font-medium hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
              <span>Previous</span>
            </button>
            <button
              type="button"
              disabled={currentPage === totalMonthlyPages}
              onClick={() => setCurrentPage((p) => Math.min(totalMonthlyPages, p + 1))}
              className="px-2.5 py-1.5 rounded-lg border border-slate-200 bg-white text-slate-700 font-medium hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1"
            >
              <span>Next</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}
    </Card>
  );
};

export default AmortizationTable;
