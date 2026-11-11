import React, { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { profileService } from '../services/profileService';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';
import { Input } from '../components/common/Input';
import { ErrorAlert } from '../components/common/ErrorAlert';
import {
  User,
  Mail,
  ShieldCheck,
  Calendar,
  Lock,
  Key,
  IndianRupee,
  Briefcase,
  Layers,
  Save,
  CheckCircle2,
} from 'lucide-react';

export const ProfilePage = () => {
  const { user } = useAuth();

  // Financial Profile form state
  const [formData, setFormData] = useState({
    monthly_net_income: '',
    monthly_expenses: '',
    existing_monthly_emi: '',
    emergency_savings: '',
    employment_type: 'SALARIED',
    existing_loan_count: '0',
  });

  const [isLoadingProfile, setIsLoadingProfile] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [validationErrors, setValidationErrors] = useState({});

  // Load existing profile on mount
  useEffect(() => {
    let isMounted = true;

    async function fetchProfile() {
      try {
        setIsLoadingProfile(true);
        const data = await profileService.getProfile();
        if (data && isMounted) {
          setFormData({
            monthly_net_income: data.monthly_net_income || '',
            monthly_expenses: data.monthly_expenses || '',
            existing_monthly_emi: data.existing_monthly_emi || '',
            emergency_savings: data.emergency_savings || '',
            employment_type: data.employment_type || 'SALARIED',
            existing_loan_count: String(data.existing_loan_count ?? 0),
          });
        }
      } catch (err) {
        if (isMounted) {
          setErrorMessage(err.message || 'Failed to load profile.');
        }
      } finally {
        if (isMounted) setIsLoadingProfile(false);
      }
    }

    fetchProfile();
    return () => {
      isMounted = false;
    };
  }, []);

  const validate = () => {
    const errors = {};
    const income = parseFloat(formData.monthly_net_income);
    const expenses = parseFloat(formData.monthly_expenses || 0);
    const emi = parseFloat(formData.existing_monthly_emi || 0);
    const savings = parseFloat(formData.emergency_savings || 0);
    const loans = parseInt(formData.existing_loan_count || 0, 10);

    if (isNaN(income) || income <= 0) {
      errors.monthly_net_income = 'Monthly net income must be greater than ₹0';
    }
    if (isNaN(expenses) || expenses < 0) {
      errors.monthly_expenses = 'Monthly expenses cannot be negative';
    }
    if (isNaN(emi) || emi < 0) {
      errors.existing_monthly_emi = 'Monthly EMI obligations cannot be negative';
    }
    if (isNaN(savings) || savings < 0) {
      errors.emergency_savings = 'Emergency savings cannot be negative';
    }
    if (isNaN(loans) || loans < 0) {
      errors.existing_loan_count = 'Loan count cannot be negative';
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSaveProfile = async (e) => {
    e.preventDefault();
    setSuccessMessage('');
    setErrorMessage('');

    if (!validate()) return;

    try {
      setIsSaving(true);
      const payload = {
        monthly_net_income: parseFloat(formData.monthly_net_income),
        monthly_expenses: parseFloat(formData.monthly_expenses || 0),
        existing_monthly_emi: parseFloat(formData.existing_monthly_emi || 0),
        emergency_savings: parseFloat(formData.emergency_savings || 0),
        employment_type: formData.employment_type,
        existing_loan_count: parseInt(formData.existing_loan_count || 0, 10),
      };

      const result = await profileService.saveProfile(payload);
      setSuccessMessage(result.message || 'Financial profile saved successfully!');
    } catch (err) {
      setErrorMessage(err.message || 'Failed to save financial profile.');
    } finally {
      setIsSaving(false);
    }
  };

  const formattedDate = user?.created_at
    ? new Date(user.created_at).toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      })
    : 'Recently';

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          Account Profile & Financial Settings
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Review your personal credentials, manage income details, and configure FOIR obligations.
        </p>
      </div>

      {/* Account Info Card */}
      <Card
        title="Personal Information"
        subtitle="Credentials linked to your database-backed session"
      >
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase text-slate-400">
                <User className="w-4 h-4 text-slate-500" />
                Full Name
              </div>
              <div className="text-base font-semibold text-slate-900 mt-1">
                {user?.full_name || 'N/A'}
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase text-slate-400">
                <Mail className="w-4 h-4 text-slate-500" />
                Email Address
              </div>
              <div className="text-base font-semibold text-slate-900 mt-1">
                {user?.email || 'N/A'}
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase text-slate-400">
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                Account Status
              </div>
              <div className="mt-1">
                <Badge variant={user?.is_active ? 'success' : 'danger'} size="sm">
                  {user?.is_active ? 'Active & Verified' : 'Inactive'}
                </Badge>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase text-slate-400">
                <Calendar className="w-4 h-4 text-slate-500" />
                Member Since
              </div>
              <div className="text-base font-semibold text-slate-900 mt-1">
                {formattedDate}
              </div>
            </div>
          </div>

          <div className="pt-2 text-xs text-slate-400 font-mono">
            User ID: {user?.id}
          </div>
        </div>
      </Card>

      {/* Financial Profile Settings Card (Step 1 Integration) */}
      <Card
        title="Financial Profile & Income Details"
        subtitle="These figures strictly power deterministic FOIR affordability calculations"
        headerAction={
          <Badge variant="success" size="sm">
            Phase 2 Active API
          </Badge>
        }
      >
        {successMessage && (
          <div className="mb-5 p-3.5 bg-emerald-50 border border-emerald-200 rounded-lg text-sm text-emerald-800 flex items-center gap-2.5">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
            <span className="font-medium">{successMessage}</span>
          </div>
        )}

        <ErrorAlert message={errorMessage} onClose={() => setErrorMessage('')} />

        <form onSubmit={handleSaveProfile} className="space-y-5 mt-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              id="monthly_net_income"
              name="monthly_net_income"
              label="Monthly Net Income (In-Hand)"
              type="number"
              step="0.01"
              icon={IndianRupee}
              placeholder="e.g. 75000"
              value={formData.monthly_net_income}
              onChange={(e) => {
                setFormData((prev) => ({ ...prev, monthly_net_income: e.target.value }));
                if (validationErrors.monthly_net_income) {
                  setValidationErrors((prev) => ({ ...prev, monthly_net_income: '' }));
                }
              }}
              error={validationErrors.monthly_net_income}
              helperText="Net monthly take-home salary or business profits after taxes"
              required
            />

            <Input
              id="monthly_expenses"
              name="monthly_expenses"
              label="Monthly Living Expenses"
              type="number"
              step="0.01"
              icon={IndianRupee}
              placeholder="e.g. 30000"
              value={formData.monthly_expenses}
              onChange={(e) => {
                setFormData((prev) => ({ ...prev, monthly_expenses: e.target.value }));
                if (validationErrors.monthly_expenses) {
                  setValidationErrors((prev) => ({ ...prev, monthly_expenses: '' }));
                }
              }}
              error={validationErrors.monthly_expenses}
              helperText="Rent, groceries, utilities, and fixed household costs"
            />

            <Input
              id="existing_monthly_emi"
              name="existing_monthly_emi"
              label="Current Monthly EMI Obligations"
              type="number"
              step="0.01"
              icon={IndianRupee}
              placeholder="e.g. 15000"
              value={formData.existing_monthly_emi}
              onChange={(e) => {
                setFormData((prev) => ({ ...prev, existing_monthly_emi: e.target.value }));
                if (validationErrors.existing_monthly_emi) {
                  setValidationErrors((prev) => ({ ...prev, existing_monthly_emi: '' }));
                }
              }}
              error={validationErrors.existing_monthly_emi}
              helperText="Active personal, home, vehicle or credit card EMIs"
            />

            <Input
              id="emergency_savings"
              name="emergency_savings"
              label="Total Emergency Reserves"
              type="number"
              step="0.01"
              icon={IndianRupee}
              placeholder="e.g. 200000"
              value={formData.emergency_savings}
              onChange={(e) => {
                setFormData((prev) => ({ ...prev, emergency_savings: e.target.value }));
                if (validationErrors.emergency_savings) {
                  setValidationErrors((prev) => ({ ...prev, emergency_savings: '' }));
                }
              }}
              error={validationErrors.emergency_savings}
              helperText="Liquid funds in savings accounts and fixed deposits"
            />

            <div>
              <label
                htmlFor="employment_type"
                className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5"
              >
                Employment Type
              </label>
              <div className="relative rounded-lg shadow-subtle">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <Briefcase className="w-4 h-4" />
                </div>
                <select
                  id="employment_type"
                  name="employment_type"
                  value={formData.employment_type}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, employment_type: e.target.value }))
                  }
                  className="block w-full rounded-lg border border-slate-300 pl-10 pr-3.5 py-2.5 text-sm bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-100 focus:border-brand-500"
                >
                  <option value="SALARIED">Salaried Employee</option>
                  <option value="SELF_EMPLOYED">Self-Employed Professional</option>
                  <option value="BUSINESS">Business Owner</option>
                  <option value="OTHER">Other / Freelance</option>
                </select>
              </div>
            </div>

            <Input
              id="existing_loan_count"
              name="existing_loan_count"
              label="Active Loans Count"
              type="number"
              min="0"
              icon={Layers}
              placeholder="e.g. 1"
              value={formData.existing_loan_count}
              onChange={(e) => {
                setFormData((prev) => ({ ...prev, existing_loan_count: e.target.value }));
                if (validationErrors.existing_loan_count) {
                  setValidationErrors((prev) => ({ ...prev, existing_loan_count: '' }));
                }
              }}
              error={validationErrors.existing_loan_count}
              helperText="Total number of active loan lines"
            />
          </div>

          <div className="pt-2 flex justify-end">
            <Button
              type="submit"
              variant="primary"
              size="md"
              isLoading={isSaving}
              icon={Save}
              className="w-full sm:w-auto"
            >
              Save Financial Profile
            </Button>
          </div>
        </form>
      </Card>

      {/* Security Architecture Card */}
      <Card
        title="Security & Session Architecture"
        subtitle="How your financial session is safeguarded"
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="p-4 rounded-xl border border-slate-200/80 bg-white space-y-1.5">
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
              <Lock className="w-4 h-4 text-brand-600" />
              Secure HTTP-Only Cookies
            </div>
            <p className="text-xs text-slate-500 leading-relaxed">
              Session tokens are never stored in browser localStorage or accessible by JavaScript, blocking XSS token theft completely.
            </p>
          </div>

          <div className="p-4 rounded-xl border border-slate-200/80 bg-white space-y-1.5">
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
              <Key className="w-4 h-4 text-emerald-600" />
              Bcrypt Password Hashing
            </div>
            <p className="text-xs text-slate-500 leading-relaxed">
              Your password is salt-hashed with bcrypt cost factor 12 before touching PostgreSQL. Plaintext passwords are never logged or stored.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
};
