"use client";

import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";

interface IntegrityGaugeProps {
  score: number;
  riskLevel?: string;
}

function getScoreColor(score: number): { main: string; bg: string; track: string } {
  if (score >= 75) return { main: "#10b981", bg: "#ecfdf5", track: "#d1fae5" };
  if (score >= 50) return { main: "#f59e0b", bg: "#fffbeb", track: "#fef3c7" };
  return { main: "#ef4444", bg: "#fef2f2", track: "#fecaca" };
}

function getScoreLabel(score: number): string {
  if (score >= 80) return "Excellent";
  if (score >= 65) return "Good";
  if (score >= 50) return "Moderate";
  if (score >= 35) return "Weak";
  return "Critical";
}

export default function IntegrityGauge({ score, riskLevel }: IntegrityGaugeProps) {
  const clampedScore = Math.max(0, Math.min(100, score));
  const colors = getScoreColor(clampedScore);
  const label = getScoreLabel(clampedScore);

  // Build the semi-circle gauge data
  const gaugeData = [
    { value: clampedScore, fill: colors.main },
    { value: 100 - clampedScore, fill: colors.track },
  ];

  return (
    <div className="rounded-2xl bg-white p-6 shadow-md border border-gray-100 flex flex-col items-center">
      <h3 className="text-lg font-bold text-gray-900 mb-1 self-start">
        Integrity Gauge
      </h3>
      <p className="text-xs text-gray-500 mb-4 self-start">
        Measures the backing and verifiability of claims
      </p>

      <div className="relative w-full" style={{ maxWidth: 260, height: 150 }}>
        <ResponsiveContainer width="100%" height={150}>
          <PieChart>
            <defs>
              <linearGradient id="gaugeGrad" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor={colors.main} stopOpacity={0.8} />
                <stop offset="100%" stopColor={colors.main} stopOpacity={1} />
              </linearGradient>
            </defs>
            <Pie
              data={gaugeData}
              cx="50%"
              cy="100%"
              startAngle={180}
              endAngle={0}
              innerRadius={70}
              outerRadius={100}
              paddingAngle={0}
              dataKey="value"
              stroke="none"
              animationBegin={0}
              animationDuration={1400}
              cornerRadius={6}
            >
              <Cell fill="url(#gaugeGrad)" />
              <Cell fill={colors.track} />
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        {/* Center label overlay */}
        <div className="absolute inset-0 flex flex-col items-center justify-end pb-1 pointer-events-none">
          <span
            className="text-4xl font-black"
            style={{ color: colors.main }}
          >
            {clampedScore}%
          </span>
          <span
            className="text-xs font-bold uppercase tracking-widest mt-0.5"
            style={{ color: colors.main }}
          >
            {label}
          </span>
        </div>
      </div>

      {/* Scale labels */}
      <div className="flex w-full justify-between px-2 mt-1" style={{ maxWidth: 260 }}>
        <span className="text-[10px] font-semibold text-gray-400">0</span>
        <span className="text-[10px] font-semibold text-gray-400">50</span>
        <span className="text-[10px] font-semibold text-gray-400">100</span>
      </div>

      {/* Risk badge */}
      {riskLevel && (
        <div className="mt-5 self-start w-full">
          <span className="text-xs font-bold text-gray-400 uppercase tracking-wider block mb-1.5">
            Overall Risk Level
          </span>
          <span
            className={`inline-block px-3 py-1 text-sm font-bold rounded-full ${
              riskLevel?.toLowerCase() === "high" || riskLevel?.toLowerCase() === "haut"
                ? "bg-red-100 text-red-800 border border-red-200"
                : riskLevel?.toLowerCase() === "medium" || riskLevel?.toLowerCase() === "moyen"
                ? "bg-yellow-100 text-yellow-800 border border-yellow-200"
                : "bg-green-100 text-green-800 border border-green-200"
            }`}
          >
            {riskLevel} Risk
          </span>
        </div>
      )}
    </div>
  );
}
