import React, { createContext, useCallback, useContext, useMemo, useState } from 'react';
import {
  DEFAULT_ADVISOR_PROVIDER,
  resolveAdvisorProvider,
} from '../utils/advisorProvider';

const AdvisorStatusContext = createContext({
  advisorProvider: DEFAULT_ADVISOR_PROVIDER,
  updateAdvisorProviderFromResponse: () => {},
  resetAdvisorProvider: () => {},
});

export const AdvisorStatusProvider = ({ children, initialProvider = DEFAULT_ADVISOR_PROVIDER }) => {
  const [advisorProvider, setAdvisorProvider] = useState(initialProvider);

  const updateAdvisorProviderFromResponse = useCallback((response) => {
    setAdvisorProvider(resolveAdvisorProvider(response));
  }, []);

  const resetAdvisorProvider = useCallback(() => {
    setAdvisorProvider(DEFAULT_ADVISOR_PROVIDER);
  }, []);

  const value = useMemo(
    () => ({
      advisorProvider,
      updateAdvisorProviderFromResponse,
      resetAdvisorProvider,
    }),
    [advisorProvider, updateAdvisorProviderFromResponse, resetAdvisorProvider]
  );

  return (
    <AdvisorStatusContext.Provider value={value}>
      {children}
    </AdvisorStatusContext.Provider>
  );
};

export const useAdvisorStatus = () => useContext(AdvisorStatusContext);
