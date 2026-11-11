import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Mail, Lock, ArrowRight, CheckCircle2 } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { Input } from '../components/common/Input';
import { Button } from '../components/common/Button';
import { ErrorAlert } from '../components/common/ErrorAlert';

export const LoginPage = () => {
  const { login, error: authError, clearError } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [validationErrors, setValidationErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [localError, setLocalError] = useState('');

  const from = location.state?.from?.pathname || '/dashboard';

  const validate = () => {
    const errors = {};
    if (!email.trim()) {
      errors.email = 'Email address is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      errors.email = 'Please enter a valid email address';
    }

    if (!password) {
      errors.password = 'Password is required';
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
      await login(email, password);
      navigate(from, { replace: true });
    } catch (err) {
      setLocalError(err.message || 'Login failed. Please check your credentials.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-xl font-bold tracking-tight text-slate-900">
          Welcome back
        </h2>
        <p className="text-sm text-slate-500 mt-1">
          Sign in to your FinAdvisor account to manage your loan portfolio.
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

        <Input
          id="password"
          name="password"
          label="Password"
          type="password"
          icon={Lock}
          placeholder="••••••••"
          autoComplete="current-password"
          value={password}
          onChange={(e) => {
            setPassword(e.target.value);
            if (validationErrors.password) setValidationErrors((prev) => ({ ...prev, password: '' }));
          }}
          error={validationErrors.password}
          required
        />

        <Button
          type="submit"
          variant="primary"
          size="md"
          className="w-full mt-2"
          isLoading={isSubmitting}
          icon={ArrowRight}
        >
          Sign In
        </Button>
      </form>

      {/* Development Quick-fill info */}
      <div className="mt-6 p-3 bg-slate-50 border border-slate-200/80 rounded-xl text-xs text-slate-600">
        <div className="font-semibold text-slate-700 flex items-center gap-1.5 mb-1">
          <CheckCircle2 className="w-3.5 h-3.5 text-brand-600" />
          Quick Test Credentials
        </div>
        <p className="text-slate-500 leading-relaxed">
          Email: <span className="font-mono text-slate-800 font-semibold select-all">jane@example.com</span><br/>
          Password: <span className="font-mono text-slate-800 font-semibold select-all">Str0ng!Pass</span>
        </p>
      </div>

      <div className="mt-6 text-center text-xs text-slate-500">
        Don&apos;t have an account yet?{' '}
        <Link
          to="/register"
          className="font-semibold text-brand-600 hover:text-brand-700 hover:underline"
        >
          Create an account
        </Link>
      </div>
    </div>
  );
};
