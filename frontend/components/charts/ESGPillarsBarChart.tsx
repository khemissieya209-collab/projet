"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  LabelList,
} from "recharts";

interface PillarSummary {
  pillar_name?: string;
  summary?: string | null;
  strengths?: string[];
  weaknesses?: string[];
  score?: number | null;
}

interface ESGPillarsBarChartProps {
  environmental?: PillarSummary;
  social?: PillarSummary;
  governance?: PillarSummary;
}

const PILLAR_COLORS = [
  { main: "#10b981", gradient: ["#10b981", "#059669"] },
  { main: "#3b82f6", gradient: ["#3b82f6", "#2563eb"] },
  { main: "#f97316", gradient: ["#f97316", "#ea580c"] },
];

function derivePillarScore(pillar?: PillarSummary): number {
  if (!pillar) return 0;
  if (typeof pillar.score === "number") return pillar.score;
  const strengths = pillar.strengths?.length ?? 0;
  const weaknesses = pillar.weaknesses?.length ?? 0;
  const total = strengths + weaknesses;
  if (total === 0) return 50;
  return Math.round((strengths / total) * 100);
}

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="rounded-xl bg-white/95 backdrop-blur-sm border border-gray-200 shadow-xl px-5 py-4 max-w-xs">
      <p className="text-sm font-bold text-gray-900 mb-1">{d.name}</p>
      <p className="text-2xl font-extrabold" style={{ color: d.color }}>
        {d.score}
        <span className="text-sm font-medium text-gray-500">/100</span>
      </p>
      <div className="mt-2 text-xs text-gray-500 space-y-0.5">
        <p>✅ {d.strengths} strength{d.strengths !== 1 ? "s" : ""}</p>
        <p>⚠️ {d.weaknesses} area{d.weaknesses !== 1 ? "s" : ""} to improve</p>
      </div>
    </div>
  );
};

export default function ESGPillarsBarChart({
  environmental,
  social,
  governance,
}: ESGPillarsBarChartProps) {
  const data = [
    {
      name: "Environmental",
      score: derivePillarScore(environmental),
      strengths: environmental?.strengths?.length ?? 0,
      weaknesses: environmental?.weaknesses?.length ?? 0,
      color: PILLAR_COLORS[0].main,
    },
    {
      name: "Social",
      score: derivePillarScore(social),
      strengths: social?.strengths?.length ?? 0,
      weaknesses: social?.weaknesses?.length ?? 0,
      color: PILLAR_COLORS[1].main,
    },
    {
      name: "Governance",
      score: derivePillarScore(governance),
      strengths: governance?.strengths?.length ?? 0,
      weaknesses: governance?.weaknesses?.length ?? 0,
      color: PILLAR_COLORS[2].main,
    },
  ];

  return (
    <div className="rounded-2xl bg-white p-6 shadow-md border border-gray-100">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-bold text-gray-900">
            ESG Pillar Scores
          </h3>
          <p className="text-xs text-gray-500 mt-0.5">
            Derived from strengths vs. areas for improvement
          </p>
        </div>
        <div className="flex gap-3">
          {data.map((d) => (
            <div key={d.name} className="flex items-center gap-1.5">
              <span
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: d.color }}
              />
              <span className="text-xs text-gray-500">{d.name}</span>
            </div>
          ))}
        </div>
      </div>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart
          data={data}
          margin={{ top: 20, right: 20, left: 0, bottom: 5 }}
          barCategoryGap="30%"
        >
          <defs>
            {PILLAR_COLORS.map((c, i) => (
              <linearGradient
                key={i}
                id={`pillarGrad${i}`}
                x1="0"
                y1="0"
                x2="0"
                y2="1"
              >
                <stop offset="0%" stopColor={c.gradient[0]} stopOpacity={1} />
                <stop offset="100%" stopColor={c.gradient[1]} stopOpacity={0.8} />
              </linearGradient>
            ))}
          </defs>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="#f1f5f9"
            vertical={false}
          />
          <XAxis
            dataKey="name"
            tick={{ fontSize: 13, fill: "#64748b", fontWeight: 600 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fontSize: 12, fill: "#94a3b8" }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => `${v}`}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(0,0,0,0.03)" }} />
          <Bar dataKey="score" radius={[10, 10, 4, 4]} animationDuration={1200}>
            {data.map((_, i) => (
              <Cell key={i} fill={`url(#pillarGrad${i})`} />
            ))}
            <LabelList
              dataKey="score"
              position="top"
              formatter={((v: any) => `${v}%`) as any}
              style={{ fontSize: 13, fontWeight: 700, fill: "#374151" }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
