import React from 'react';
import { Info, ShieldAlert } from 'lucide-react';

export const AdvisorDisclaimerBanner = ({ disclaimer }) => {
  const text =
    disclaimer ||
    'FinAdvisor AI provides personal financial educational guidance based on self-reported data. ' +
      'It is not a formal credit bureau evaluation, commercial lender underwriting commitment, or legal financial advice.';

  return (
    <div className="flex items-start gap-2.5 p-3 rounded-lg bg-amber-50/70 border border-amber-200/60 text-amber-900 text-xs leading-relaxed">
      <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
      <div>
        <span className="font-semibold text-amber-950">Educational Advisory Notice: </span>
        <span>{text}</span>
      </div>
    </div>
  );
};

export default AdvisorDisclaimerBanner;
