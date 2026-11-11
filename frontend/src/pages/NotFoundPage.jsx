import React from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/common/Button';
import { Home, ArrowLeft } from 'lucide-react';

export const NotFoundPage = () => {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-4 text-center">
      <div className="w-16 h-16 rounded-2xl bg-brand-50 text-brand-600 flex items-center justify-center mx-auto mb-4 border border-brand-100">
        <span className="text-2xl font-bold font-mono">404</span>
      </div>

      <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
        Page Not Found
      </h1>
      <p className="text-sm text-slate-500 mt-2 max-w-sm">
        The financial page or calculation tool you are looking for does not exist or has been moved.
      </p>

      <div className="mt-6 flex items-center gap-3">
        <Link to="/dashboard">
          <Button variant="primary" icon={Home}>
            Back to Dashboard
          </Button>
        </Link>
      </div>
    </div>
  );
};
