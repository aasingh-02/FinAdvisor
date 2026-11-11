import React, { useState } from 'react';
import { Card } from '../common/Card';
import { Button } from '../common/Button';
import { formatINR } from '../../utils/formatCurrency';
import {
  SlidersHorizontal,
  RotateCcw,
  Search,
  Sparkles,
  Info,
  CheckCircle,
} from 'lucide-react';

const CATEGORIES = [
  { id: '', label: 'All 4 Categories' },
  { id: 'PERSONAL_LOAN', label: 'Personal Loan (13.5%)' },
  { id: 'HOME_LOAN', label: 'Home Loan (8.5%)' },
  { id: 'VEHICLE_LOAN', label: 'Vehicle Loan (9.5%)' },
  { id: 'EDUCATION_LOAN', label: 'Education Loan (10.0%)' },
];

const FOIR_PRESETS = [
  { value: 30, label: '30% (Conservative)' },
  { value: 35, label: '35% (Moderate)' },
  { value: 40, label: '40% (Benchmark)' },
  { value: 45, label: '45% (Flexible)' },
  { value: 50, label: '50% (High Leeway)' },
];

const AMOUNT_PRESETS = [
  { label: '₹2 Lakh', value: 200000 },
  { label: '₹5 Lakh', value: 500000 },
  { label: '₹10 Lakh', value: 1000000 },
  { label: '₹25 Lakh', value: 2500000 },
  { label: '₹50 Lakh', value: 5000000 },
];

export const CustomLoanForm = ({
  initialValues,
  onSubmit,
  onReset,
  isLoading,
}) => {
  const [category, setCategory] = useState(initialValues?.preferredCategory || '');
  const [desiredAmount, setDesiredAmount] = useState(
    initialValues?.desiredAmount ? String(initialValues.desiredAmount) : ''
  );
  const [tenure, setTenure] = useState(
    initialValues?.preferredTenure ? String(initialValues.preferredTenure) : ''
  );
  const [foirThreshold, setFoirThreshold] = useState(
    initialValues?.foirThreshold !== undefined ? initialValues.foirThreshold : 40.0
  );

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit({
      preferredCategory: category || null,
      desiredAmount: desiredAmount ? parseFloat(desiredAmount) : null,
      preferredTenure: tenure ? parseInt(tenure, 10) : null,
      foirThreshold: parseFloat(foirThreshold),
    });
  };

  const handleReset = () => {
    setCategory('');
    setDesiredAmount('');
    setTenure('');
    setFoirThreshold(40.0);
    onReset();
  };

  return (
    <Card
      title="Tailor Loan Sizing & Custom Simulation"
      subtitle="Evaluate custom loan principal, category, and tenure against your prudent cash-flow capacity"
    >
      <form onSubmit={handleSubmit} className="p-5 sm:p-6 space-y-6">
        {/* Row 1: Category & FOIR Benchmark */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
              Loan Category Preference
            </label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full h-10 px-3 rounded-lg border border-slate-300 bg-white text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
            >
              {CATEGORIES.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.label}
                </option>
              ))}
            </select>
            <span className="text-[11px] text-slate-400 mt-1 block">
              Leave on "All 4 Categories" to receive simultaneous multi-category sizing.
            </span>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
              FOIR Policy Benchmark ({foirThreshold}%)
            </label>
            <div className="flex flex-wrap gap-1.5">
              {FOIR_PRESETS.map((p) => (
                <button
                  key={p.value}
                  type="button"
                  onClick={() => setFoirThreshold(p.value)}
                  className={`px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    foirThreshold === p.value
                      ? 'bg-brand-600 text-white shadow-sm'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Row 2: Desired Amount & Custom Tenure */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 border-t border-slate-100">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
              Desired Loan Amount (Optional)
            </label>
            <div className="relative rounded-lg shadow-sm">
              <span className="absolute inset-y-0 left-0 pl-3 flex items-center text-slate-400 font-semibold text-sm">
                ₹
              </span>
              <input
                type="number"
                min="1000"
                step="5000"
                value={desiredAmount}
                onChange={(e) => setDesiredAmount(e.target.value)}
                placeholder="e.g. 500000"
                className="w-full pl-8 pr-3 h-10 rounded-lg border border-slate-300 bg-white text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
              />
            </div>

            {/* Quick Amount Pills */}
            <div className="flex flex-wrap gap-1 mt-2">
              {AMOUNT_PRESETS.map((preset) => (
                <button
                  key={preset.value}
                  type="button"
                  onClick={() => setDesiredAmount(String(preset.value))}
                  className="px-2 py-0.5 text-[11px] font-medium rounded bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors"
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
              Preferred Tenure in Months (Optional)
            </label>
            <input
              type="number"
              min="6"
              max="360"
              step="6"
              value={tenure}
              onChange={(e) => setTenure(e.target.value)}
              placeholder="e.g. 60 (5 years)"
              className="w-full px-3 h-10 rounded-lg border border-slate-300 bg-white text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
            />
            <span className="text-[11px] text-slate-400 mt-1 block">
              Leave blank to use the standard default tenure for each loan category.
            </span>
          </div>
        </div>

        {/* Buttons */}
        <div className="flex flex-wrap items-center justify-end gap-3 pt-4 border-t border-slate-100">
          <Button
            type="button"
            variant="ghost"
            onClick={handleReset}
            disabled={isLoading}
            className="flex items-center gap-1.5 text-xs text-slate-600 hover:text-slate-900"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Reset to Defaults
          </Button>

          <Button
            type="submit"
            variant="primary"
            disabled={isLoading}
            className="flex items-center gap-2 text-sm"
          >
            <Sparkles className="w-4 h-4" />
            {isLoading ? 'Evaluating Sizing...' : 'Generate Personalized Recommendations'}
          </Button>
        </div>
      </form>
    </Card>
  );
};

export default CustomLoanForm;
