import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Calculator,
  Percent,
  GitCompare,
  Bot,
  User,
  ShieldCheck,
  ShieldAlert,
  TrendingUp,
  X,
  CreditCard,
  Sparkles,
} from 'lucide-react';
import { Badge } from '../common/Badge';
import { useAdvisorStatus } from '../../context/AdvisorStatusContext';

export const navigationItems = [
  {
    name: 'Dashboard',
    to: '/dashboard',
    icon: LayoutDashboard,
    badge: null,
  },
  {
    name: 'Risk Assessment',
    to: '/risk-assessment',
    icon: ShieldAlert,
    badge: 'Phase 2',
  },
  {
    name: 'Loan Affordability',
    to: '/loan-calculator',
    icon: Calculator,
    badge: 'Phase 2',
  },
  {
    name: 'EMI Calculator',
    to: '/emi-calculator',
    icon: Percent,
    badge: 'Phase 2',
  },
  {
    name: 'Recommendations',
    to: '/loan-recommendations',
    icon: Sparkles,
    badge: 'Phase 2',
  },
  {
    name: 'Loan Comparison',
    to: '/loan-comparison',
    icon: GitCompare,
    badge: 'Phase 2',
  },
  {
    name: 'AI Advisor',
    to: '/ai-advisor',
    icon: Bot,
    badge: null,
    showAdvisorProvider: true,
  },
  {
    name: 'Profile & Settings',
    to: '/profile',
    icon: User,
    badge: null,
  },
];

export const Sidebar = ({ isOpen, onClose, providerStatus }) => {
  const { advisorProvider } = useAdvisorStatus();
  const activeProvider = providerStatus || advisorProvider;
  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          onClick={onClose}
          className="fixed inset-0 z-40 bg-slate-900/40 backdrop-blur-sm lg:hidden transition-opacity"
          aria-hidden="true"
        />
      )}

      {/* Sidebar container */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 bg-white border-r border-slate-200/90 flex flex-col transition-transform duration-200 ease-in-out lg:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Brand header */}
        <div className="h-16 flex items-center justify-between px-6 border-b border-slate-100">
          <NavLink to="/dashboard" className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center text-white shadow-sm shadow-brand-500/20">
              <TrendingUp className="w-5 h-5" />
            </div>
            <div>
              <div className="text-base font-bold tracking-tight text-slate-900 leading-tight">
                Fin<span className="text-brand-600">Advisor</span>
              </div>
              <div className="text-[10px] font-medium tracking-wider uppercase text-slate-400">
                AI Advisory Platform
              </div>
            </div>
          </NavLink>

          <button
            type="button"
            onClick={onClose}
            className="lg:hidden text-slate-400 hover:text-slate-600 p-1.5 rounded-lg hover:bg-slate-100"
            aria-label="Close sidebar"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation list */}
        <div className="flex-1 overflow-y-auto px-4 py-5 space-y-1">
          <div className="px-3 pb-2 text-[11px] font-semibold tracking-wider uppercase text-slate-400">
            Main Navigation
          </div>
          {navigationItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={() => {
                  if (window.innerWidth < 1024) onClose();
                }}
                className={({ isActive }) =>
                  `flex items-center justify-between px-3.5 py-2.5 text-sm font-medium rounded-lg transition-colors group ${
                    isActive
                      ? 'bg-brand-50 text-brand-700 font-semibold'
                      : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <div className={`flex ${item.showAdvisorProvider ? 'items-start' : 'items-center'} gap-3 min-w-0`}>
                      <Icon
                        className={`w-4 h-4 shrink-0 transition-colors ${
                          item.showAdvisorProvider ? 'mt-0.5 ' : ''
                        }${
                          isActive ? 'text-brand-600' : 'text-slate-400 group-hover:text-slate-600'
                        }`}
                      />
                      <div className="min-w-0">
                        <div className="truncate">{item.name}</div>
                        {item.showAdvisorProvider && (
                          <div className="mt-1">
                            <Badge
                              variant={activeProvider.isGemini ? 'primary' : 'default'}
                              size="sm"
                              className="text-[10px] px-1.5 py-0 whitespace-nowrap"
                            >
                              {activeProvider.label}
                            </Badge>
                          </div>
                        )}
                      </div>
                    </div>
                    {item.badge && (
                      <Badge
                        variant={isActive ? 'primary' : 'default'}
                        size="sm"
                        className="text-[10px] px-1.5 py-0 shrink-0"
                      >
                        {item.badge}
                      </Badge>
                    )}
                  </>
                )}
              </NavLink>
            );
          })}
        </div>

        {/* System & Trust badge at bottom */}
        <div className="p-4 border-t border-slate-100 bg-slate-50/50">
          <div className="flex items-center gap-3 p-3 rounded-xl bg-white border border-slate-200/80 shadow-subtle">
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-xs font-semibold text-slate-900 truncate">
                Session Active
              </div>
              <div className="text-[11px] text-slate-500 truncate">
                PostgreSQL & bcrypt
              </div>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};
