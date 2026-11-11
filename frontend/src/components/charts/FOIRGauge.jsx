/**
 * frontend/src/components/charts/FOIRGauge.jsx
 * ─────────────────────────────────────────────
 * Interactive semicircular gauge visualizing Fixed Obligation to Income Ratio (FOIR).
 *
 * Displays:
 * - Color-coded risk zones (Optimal, Manageable, Stretched, Critical)
 * - Configured policy threshold marker
 * - Dynamic needle indicator for current FOIR
 * - Secondary ghost indicator for projected FOIR (when proposed loan is simulated)
 * - Prominent center readout and legend
 */

import React from 'react';
import { ShieldCheck, AlertTriangle, AlertOctagon, CheckCircle2 } from 'lucide-react';

const STATUS_CONFIG = {
  Optimal: {
    color: '#10b981',
    bgColor: 'bg-emerald-50',
    textColor: 'text-emerald-700',
    borderColor: 'border-emerald-200',
    icon: CheckCircle2,
    label: 'Optimal Headroom',
  },
  Manageable: {
    color: '#0284c7',
    bgColor: 'bg-sky-50',
    textColor: 'text-sky-700',
    borderColor: 'border-sky-200',
    icon: ShieldCheck,
    label: 'Manageable Debt',
  },
  Stretched: {
    color: '#f59e0b',
    bgColor: 'bg-amber-50',
    textColor: 'text-amber-700',
    borderColor: 'border-amber-200',
    icon: AlertTriangle,
    label: 'Stretched Capacity',
  },
  Critical: {
    color: '#ef4444',
    bgColor: 'bg-rose-50',
    textColor: 'text-rose-700',
    borderColor: 'border-rose-200',
    icon: AlertOctagon,
    label: 'High Burden / Deficit',
  },
};

export const FOIRGauge = ({
  currentFoir = 0,
  configuredThreshold = 40,
  affordabilityStatus = 'Optimal',
  projectedFoir = null,
  proposedEmi = null,
  monthlyIncome = 0,
}) => {
  const foir = Math.max(0, Math.min(100, parseFloat(currentFoir) || 0));
  const threshold = Math.max(1, Math.min(100, parseFloat(configuredThreshold) || 40));
  const projFoir = projectedFoir !== null && projectedFoir !== undefined
    ? Math.max(0, Math.min(100, parseFloat(projectedFoir) || 0))
    : null;

  const statusInfo = STATUS_CONFIG[affordabilityStatus] || STATUS_CONFIG.Optimal;
  const StatusIcon = statusInfo.icon;

  // Semicircular geometry: 180° sweep from left (180°) to right (0°)
  // SVG ViewBox: 300 x 175
  const cx = 150;
  const cy = 145;
  const radius = 110;
  const strokeWidth = 18;

  // Convert percentage (0 - 100) to gauge angle in degrees (180° down to 0°)
  // 0% -> 180° (left), 50% -> 90° (top), 100% -> 0° (right)
  const percentToAngle = (p) => 180 - (Math.max(0, Math.min(100, p)) / 100) * 180;

  // Helper to convert polar coordinates to SVG Cartesian (x, y)
  const polarToCartesian = (centerX, centerY, r, angleInDegrees) => {
    const angleInRadians = (angleInDegrees * Math.PI) / 180.0;
    return {
      x: centerX + r * Math.cos(angleInRadians),
      y: centerY - r * Math.sin(angleInRadians),
    };
  };

  // Helper to describe an SVG arc between two angles
  const describeArc = (x, y, r, startAngle, endAngle) => {
    const start = polarToCartesian(x, y, r, startAngle);
    const end = polarToCartesian(x, y, r, endAngle);
    const largeArcFlag = endAngle - startAngle <= 180 ? '0' : '1';
    return ['M', start.x, start.y, 'A', r, r, 0, largeArcFlag, 1, end.x, end.y].join(' ');
  };

  // Slices for risk zones:
  // 1. Optimal: 0% to min(30%, threshold)
  // 2. Manageable: min(30%, threshold) to threshold%
  // 3. Stretched: threshold% to 55%
  // 4. Critical: 55% to 100%
  const optimalEnd = Math.min(30, threshold);
  const manageableEnd = threshold;
  const stretchedEnd = Math.max(threshold, 55);

  const zones = [
    { start: 0, end: optimalEnd, color: '#10b981' },               // Emerald
    { start: optimalEnd, end: manageableEnd, color: '#0284c7' },     // Sky Blue
    { start: manageableEnd, end: stretchedEnd, color: '#f59e0b' },   // Amber
    { start: stretchedEnd, end: 100, color: '#ef4444' },            // Rose
  ];

  // Calculate needle Cartesian endpoint for current FOIR
  const currentAngle = percentToAngle(foir);
  const needleTip = polarToCartesian(cx, cy, radius - 15, currentAngle);

  // Threshold marker endpoint
  const thresholdAngle = percentToAngle(threshold);
  const thresholdTickStart = polarToCartesian(cx, cy, radius - strokeWidth / 2 - 4, thresholdAngle);
  const thresholdTickEnd = polarToCartesian(cx, cy, radius + strokeWidth / 2 + 6, thresholdAngle);

  // Projected FOIR needle tip (if active)
  const projAngle = projFoir !== null ? percentToAngle(projFoir) : null;
  const projNeedleTip = projAngle !== null ? polarToCartesian(cx, cy, radius - 15, projAngle) : null;

  return (
    <div className="flex flex-col items-center justify-center w-full">
      {/* SVG Semicircular Gauge */}
      <div className="relative w-full max-w-[320px] aspect-[300/180]">
        <svg viewBox="0 0 300 180" className="w-full h-full overflow-visible">
          <defs>
            <filter id="gaugeShadow" x="-10%" y="-10%" width="120%" height="120%">
              <feDropShadow dx="0" dy="2" stdDeviation="3" floodOpacity="0.15" />
            </filter>
          </defs>

          {/* Background Zone Arcs */}
          {zones.map((zone, idx) => {
            if (zone.start >= zone.end) return null;
            const a1 = percentToAngle(zone.start);
            const a2 = percentToAngle(zone.end);
            return (
              <path
                key={idx}
                d={describeArc(cx, cy, radius, a1, a2)}
                fill="none"
                stroke={zone.color}
                strokeWidth={strokeWidth}
                strokeLinecap="butt"
                opacity={0.88}
              />
            );
          })}

          {/* Threshold Marker Tick */}
          <line
            x1={thresholdTickStart.x}
            y1={thresholdTickStart.y}
            x2={thresholdTickEnd.x}
            y2={thresholdTickEnd.y}
            stroke="#1e293b"
            strokeWidth="3.5"
            strokeLinecap="round"
          />

          {/* Secondary Ghost Needle for Projected FOIR (if simulation active) */}
          {projNeedleTip && (
            <g className="transition-all duration-300">
              <line
                x1={cx}
                y1={cy}
                x2={projNeedleTip.x}
                y2={projNeedleTip.y}
                stroke="#6366f1"
                strokeWidth="3"
                strokeDasharray="4 3"
                strokeLinecap="round"
              />
              <circle cx={projNeedleTip.x} cy={projNeedleTip.y} r="4" fill="#6366f1" />
            </g>
          )}

          {/* Primary Current FOIR Needle */}
          <line
            x1={cx}
            y1={cy}
            x2={needleTip.x}
            y2={needleTip.y}
            stroke="#0f172a"
            strokeWidth="4"
            strokeLinecap="round"
            filter="url(#gaugeShadow)"
            className="transition-all duration-500 ease-out"
          />

          {/* Center Needle Pivot Pin */}
          <circle cx={cx} cy={cy} r="8" fill="#0f172a" />
          <circle cx={cx} cy={cy} r="4" fill="#ffffff" />

          {/* Min & Max Labels */}
          <text x="35" y="162" textAnchor="middle" className="text-[11px] font-bold fill-slate-400">
            0%
          </text>
          <text x="265" y="162" textAnchor="middle" className="text-[11px] font-bold fill-slate-400">
            100%
          </text>

          {/* Policy Threshold Flag Label */}
          <text
            x={thresholdTickEnd.x}
            y={thresholdTickEnd.y - 6}
            textAnchor="middle"
            className="text-[10px] font-extrabold fill-slate-700"
          >
            {threshold}% Limit
          </text>
        </svg>

        {/* Center Readout Overlay */}
        <div className="absolute inset-x-0 bottom-1 flex flex-col items-center text-center">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
            Current FOIR
          </span>
          <div className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight leading-tight">
            {foir.toFixed(2)}%
          </div>

          <div
            className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold border mt-0.5 ${statusInfo.bgColor} ${statusInfo.textColor} ${statusInfo.borderColor}`}
          >
            <StatusIcon className="w-3.5 h-3.5" />
            <span>{affordabilityStatus}</span>
          </div>
        </div>
      </div>

      {/* Projected Simulation Indicator Pill */}
      {projFoir !== null && (
        <div className="mt-3 px-3 py-1.5 bg-indigo-50 border border-indigo-200 rounded-lg text-xs flex items-center gap-2 text-indigo-900 font-medium">
          <span className="w-2 h-2 rounded-full bg-indigo-600 animate-pulse" />
          <span>
            Projected with proposed EMI: <strong>{projFoir.toFixed(2)}%</strong>
            {projFoir > threshold && (
              <span className="text-amber-700 font-semibold ml-1">(Exceeds {threshold}% limit)</span>
            )}
          </span>
        </div>
      )}

      {/* Risk Zone Color Legend */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 w-full mt-4 pt-3 border-t border-slate-100 text-[11px]">
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shrink-0" />
          <span className="text-slate-600">
            Optimal: <strong>0 - {optimalEnd}%</strong>
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-sky-500 shrink-0" />
          <span className="text-slate-600">
            Manageable: <strong>{optimalEnd} - {manageableEnd}%</strong>
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-amber-500 shrink-0" />
          <span className="text-slate-600">
            Stretched: <strong>{manageableEnd} - {stretchedEnd}%</strong>
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-rose-500 shrink-0" />
          <span className="text-slate-600">
            Critical: <strong>&gt; {stretchedEnd}%</strong>
          </span>
        </div>
      </div>
    </div>
  );
};

export default FOIRGauge;
