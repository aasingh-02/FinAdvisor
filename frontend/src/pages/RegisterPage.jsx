import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { User, Mail, Lock, ArrowRight, ShieldCheck, Check } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { Input } from '../components/common/Input';
import { Button } from '../components/common/Button';
import { ErrorAlert } from '../components/common/ErrorAlert';

export const RegisterPage = () => {
  const { register, error: authError, clearError } = useAuth();
  const navigate = useNavigate();

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [validationErrors, setValidationErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [localError, setLocalError] = useState('');

  // Password rule checks matching backend schema
  const hasMinLength = password.length >= 8;
  const hasUppercase = /[A-Z]/.test(password);
  const hasDigit = /[0-9]/.test(password);

  const validate = () => {
    const errors = {};
    if (!fullName.trim() || fullName.trim().length < 2) {
      errors.fullName = 'Full name must be at least 2 characters';
    }

    if (!email.trim()) {
      errors.email = 'Email address is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      errors.email = 'Please enter a valid email address';
    }

    if (!password) {
      errors.password = 'Password is required';
    } else if (!hasMinLength || !hasUppercase || !hasDigit) {
      errors.password = 'Password does not satisfy all complexity requirements';
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLocalError('');
    clearError();

    if (!validate()) return;

    try {
      setIsSubmitting(true);
      await register(fullName, email, password);
      navigate('/dashboard', { replace: true });
    } catch (err) {
      setLocalError(err.message || 'Registration failed. An account with this email may already exist.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-xl font-bold tracking-tight text-slate-900">
          Create an account
        </h2>
        <p className="text-sm text-slate-500 mt-1">
          Start evaluating loan affordability and AI-guided financial metrics.
        </p>
      </div>

      <ErrorAlert
        message={localError || authError}
        onClose={() => {
          setLocalError('');
          clearError();
        }}
      />

      <form onSubmit={handleSubmit} className="space-y-4 mt-5">
        <Input
          id="fullName"
          name="fullName"
          label="Full Name"
          type="text"
          icon={User}
          placeholder="e.g. Alex Morgan"
          autoComplete="name"
          value={fullName}
          onChange={(e) => {
            setFullName(e.target.value);
            if (validationErrors.fullName) setValidationErrors((prev) => ({ ...prev, fullName: '' }));
          }}
          error={validationErrors.fullName}
          required
        />

        <Input
          id="email"
          name="email"
          label="Email address"
          type="email"
          icon={Mail}
          placeholder="name@example.com"
          autoComplete="email"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            if (validationErrors.email) setValidationErrors((prev) => ({ ...prev, email: '' }));
          }}
          error={validationErrors.email}
          required
        />

        <div>
          <Input
            id="password"
            name="password"
            label="Password"
            type="password"
            icon={Lock}
            placeholder="At least 8 characters"
            autoComplete="new-password"
            value={password}
            onChange={(e) => {
              setPassword(e.target.value);
              if (validationErrors.password) setValidationErrors((prev) => ({ ...prev, password: '' }));
            }}
            error={validationErrors.password}
            required
          />

          {/* Password complexity checklist */}
          <div className="mt-2.5 p-2.5 bg-slate-50 rounded-lg border border-slate-200/80 space-y-1.5 text-xs">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              Password Requirements
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-1.5 text-[11px]">
              <span className={`flex items-center gap-1 ${hasMinLength ? 'text-emerald-600 font-medium' : 'text-slate-400'}`}>
                <Check className={`w-3 h-3 ${hasMinLength ? 'text-emerald-500' : 'text-slate-300'}`} />
                8+ characters
              </span>
              <span className={`flex items-center gap-1 ${hasUppercase ? 'text-emerald-600 font-medium' : 'text-slate-400'}`}>
                <Check className={`w-3 h-3 ${hasUppercase ? 'text-emerald-500' : 'text-slate-300'}`} />
                1 uppercase
              </span>
              <span className={`flex items-center gap-1 ${hasDigit ? 'text-emerald-600 font-medium' : 'text-slate-400'}`}>
                <Check className={`w-3 h-3 ${hasDigit ? 'text-emerald-500' : 'text-slate-300'}`} />
                1 number
              </span>
            </div>
          </div>
        </div>

        <Button
          type="submit"
          variant="primary"
          size="md"
          className="w-full mt-2"
          isLoading={isSubmitting}
          icon={ArrowRight}
        >
          Create Account
        </Button>
      </form>

      <div className="mt-6 text-center text-xs text-slate-500">
        Already registered?{' '}
        <Link
          to="/login"
          className="font-semibold text-brand-600 hover:text-brand-700 hover:underline"
        >
          Sign in here
        </Link>
      </div>
    </div>
  );
};
