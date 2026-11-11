import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { useAuth } from './hooks/useAuth';
import { ProtectedRoute } from './components/layout/ProtectedRoute';
import { DashboardLayout } from './layouts/DashboardLayout';
import { AuthLayout } from './layouts/AuthLayout';

// Pages
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { DashboardPage } from './pages/DashboardPage';
import { RiskDashboardPage } from './pages/RiskDashboardPage';
import { LoanAffordabilityPage } from './pages/LoanAffordabilityPage';
import { EMICalculatorPage } from './pages/EMICalculatorPage';
import { LoanComparisonPage } from './pages/LoanComparisonPage';
import { LoanRecommendationsPage } from './pages/LoanRecommendationsPage';
import { AIAdvisorPage } from './pages/AIAdvisorPage';
import { ProfilePage } from './pages/ProfilePage';
import { NotFoundPage } from './pages/NotFoundPage';

// Root redirect handler
const RootRedirect = () => {
  const { user, loading } = useAuth();

  if (loading) {
    return null; // Top-level ProtectedRoute will render spinner if needed
  }

  return user ? <Navigate to="/dashboard" replace /> : <Navigate to="/login" replace />;
};

export const App = () => {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Root Redirect */}
          <Route path="/" element={<RootRedirect />} />

          {/* Authentication Routes (Public) */}
          <Route element={<AuthLayout />}>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
          </Route>

          {/* Protected Application Routes */}
          <Route
            element={
              <ProtectedRoute>
                <DashboardLayout />
              </ProtectedRoute>
            }
          >
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/risk-assessment" element={<RiskDashboardPage />} />
            <Route path="/risk-dashboard" element={<RiskDashboardPage />} />
            <Route path="/loan-calculator" element={<LoanAffordabilityPage />} />
            <Route path="/loan-affordability" element={<LoanAffordabilityPage />} />
            <Route path="/emi-calculator" element={<EMICalculatorPage />} />
            <Route path="/loan-recommendations" element={<LoanRecommendationsPage />} />
            <Route path="/recommendations" element={<LoanRecommendationsPage />} />
            <Route path="/loan-comparison" element={<LoanComparisonPage />} />
            <Route path="/ai-advisor" element={<AIAdvisorPage />} />
            <Route path="/profile" element={<ProfilePage />} />
          </Route>

          {/* 404 Catch-all */}
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
};

export default App;
