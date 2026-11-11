import React from 'react';
import { AlertCircle, X } from 'lucide-react';

export const ErrorAlert = ({ message, onClose }) => {
  if (!message) return null;

  return (
    <div className="flex items-start gap-3 p-3.5 text-sm text-red-800 bg-red-50 border border-red-200 rounded-lg animate-in fade-in duration-200">
      <AlertCircle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
      <div className="flex-1 font-medium leading-relaxed">{message}</div>
      {onClose && (
        <button
          type="button"
          onClick={onClose}
          className="text-red-400 hover:text-red-600 transition-colors p-0.5"
          aria-label="Dismiss"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
};
