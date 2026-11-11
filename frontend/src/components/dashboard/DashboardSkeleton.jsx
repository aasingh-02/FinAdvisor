import React from 'react';
import { Card } from '../common/Card';

export const DashboardSkeleton = () => {
  return (
    <div className="space-y-6 animate-pulse" aria-label="Loading dashboard...">
      {/* Welcome Banner Skeleton */}
      <div className="h-28 rounded-2xl bg-slate-200" />

      {/* Metric Cards Skeleton */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-32 rounded-xl bg-slate-200" />
        ))}
      </div>

      {/* Health Score Card Skeleton */}
      <Card>
        <div className="flex flex-col md:flex-row gap-6">
          <div className="w-full md:w-56 h-48 bg-slate-200 rounded-2xl" />
          <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-24 bg-slate-100 rounded-xl" />
            ))}
          </div>
        </div>
      </Card>

      {/* Lower Section Skeleton */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="h-64 rounded-xl bg-slate-200" />
        <div className="h-64 rounded-xl bg-slate-200" />
      </div>
    </div>
  );
};

export default DashboardSkeleton;
