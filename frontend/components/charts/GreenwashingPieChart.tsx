"use client";

import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

interface Claim {
  text: string;
  risk_level: string;
  is_verifiable: boolean;
  justification: string;
}

interface GreenwashingPieChartProps {
  claims?: Claim[];
  overallRisk?: string;
}

const RISK_CONFIG: Record<string, { color: string; gradient: [string, string]; label: string }> = {
  high: {
    color: "#ef4444",
    gradient: ["#ef4444", "#dc2626"],
    label: "High Risk",
  },
  haut: {
    color: "#ef4444",
    gradient: ["#ef4444", "#dc2626"],
    label: "High Risk",
  },
  medium: {
    color: "#f59e0b",
    gradient: ["#f59e0b", "#d97706"],
    label: "Medium Risk",
  },
  moyen: {
    color: "#f59e0b",
    gradient: ["#f59e0b", "#d97706"],
    label: "Medium Risk",
  },
  low: {
    color: "#10b981",
    gradient: ["#10b981", "#059669"],
    label: "Low Risk",
  },
  bas: {
    color: "#10b981",
    gradient: ["#10b981", "#059669"],
    label: "Low Risk",
  },
};

function normalizeRisk(risk: string): string {
  const r = risk?.toLowerCase()?.trim();
  if (r === "haut" || r === "high") return "high";
  if (r === "moyen" || r === "medium") return "medium";
  return "low";
}

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="rounded-xl bg-white/95 backdrop-blur-sm border border-gray-200 shadow-xl px-5 py-3">
      <div className="flex items-center gap-2 mb-1">
        <span
          className="inline-block h-3 w-3 rounded-full"
          style={{ backgroundColor: d.color }}
        />
        <span className="text-sm font-bold text-gray-900">{d.name}</span>
      </div>
      <p className="text-lg font-extrabold" style={{ color: d.color }}>
        {d.value} claim{d.value !== 1 ? "s" : ""}
      </p>
      <p className="text-xs text-gray-500">{d.pct}% of total</p>
    </div>
  );
};

const renderCustomLabel = ({
  cx,
  cy,
  midAngle,
  innerRadius,
  outerRadius,
  percent,
}: any) => {
  if (percent < 0.08) return null;
  const RADIAN = Math.PI / 180;
  const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);
  return (
    <text
      x={x}
      y={y}
      fill="#fff"
      textAnchor="middle"
      dominantBaseline="central"
      fontSize={13}
      fontWeight={700}
    >
      {`${(percent * 100).toFixed(0)}%`}
    </text>
  );
};

export default function GreenwashingPieChart({
  claims,
  overallRisk,
}: GreenwashingPieChartProps) {
  if (!claims || claims.length === 0) return null;

  const counts: Record<string, number> = { high: 0, medium: 0, low: 0 };
  claims.forEach((c) => {
    const norm = normalizeRisk(c.risk_level);
    counts[norm] = (counts[norm] || 0) + 1;
  });

  const data = Object.entries(counts)
    .filter(([, v]) => v > 0)
    .map(([key, value]) => ({
      name: RISK_CONFIG[key]?.label ?? key,
      value,
      color: RISK_CONFIG[key]?.color ?? "#94a3b8",
      pct: Math.round((value / claims.length) * 100),
    }));

  const verifiable = claims.filter((c) => c.is_verifiable).length;
  const unverifiable = claims.length - verifiable;

  return (
    <div className="rounded-2xl bg-white p-6 shadow-md border border-gray-100">
      <div className="flex items-center justify-between mb-2">
        <div>
          <h3 className="text-lg font-bold text-gray-900">
            Greenwashing Risk Distribution
          </h3>
          <p className="text-xs text-gray-500 mt-0.5">
            Breakdown of {claims.length} audited claim
            {claims.length !== 1 ? "s" : ""} by risk level
          </p>
        </div>
      </div>

      <div className="flex flex-col md:flex-row items-center gap-6">
        {/* Pie */}
        <div className="w-full md:w-1/2" style={{ minHeight: 260 }}>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <defs>
                {data.map((d, i) => (
                  <linearGradient key={i} id={`pieGrad${i}`} x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stopColor={d.color} stopOpacity={0.9} />
                    <stop offset="100%" stopColor={d.color} stopOpacity={1} />
                  </linearGradient>
                ))}
              </defs>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={105}
                paddingAngle={3}
                dataKey="value"
                strokeWidth={2}
                stroke="#fff"
                animationBegin={0}
                animationDuration={1000}
                label={renderCustomLabel}
                labelLine={false}
              >
                {data.map((d, i) => (
                  <Cell key={i} fill={`url(#pieGrad${i})`} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Stats panel */}
        <div className="w-full md:w-1/2 space-y-4">
          {/* Legend */}
          <div className="space-y-2">
            {data.map((d) => (
              <div key={d.name} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span
                    className="inline-block h-3 w-3 rounded-full"
                    style={{ backgroundColor: d.color }}
                  />
                  <span className="text-sm font-medium text-gray-700">
                    {d.name}
                  </span>
                </div>
                <span className="text-sm font-bold text-gray-900">
                  {d.value}
                </span>
              </div>
            ))}
          </div>

          <div className="border-t border-gray-100 pt-4 space-y-3">
            {/* Verifiability stats */}
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Verifiable
              </span>
              <span className="text-sm font-bold text-green-600">
                {verifiable}/{claims.length}
              </span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-2">
              <div
                className="h-2 rounded-full transition-all duration-700"
                style={{
                  width: `${(verifiable / claims.length) * 100}%`,
                  background: "linear-gradient(90deg, #10b981, #059669)",
                }}
              />
            </div>

            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Unverifiable
              </span>
              <span className="text-sm font-bold text-red-500">
                {unverifiable}/{claims.length}
              </span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-2">
              <div
                className="h-2 rounded-full transition-all duration-700"
                style={{
                  width: `${(unverifiable / claims.length) * 100}%`,
                  background: "linear-gradient(90deg, #ef4444, #dc2626)",
                }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
