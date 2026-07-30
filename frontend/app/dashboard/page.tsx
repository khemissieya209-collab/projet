"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  FaLeaf,
  FaRobot,
  FaChartLine,
  FaCheckCircle,
  FaTimesCircle,
  FaExclamationTriangle,
  FaClock,
  FaArrowLeft,
} from "react-icons/fa";
import ESGPillarsBarChart from "@/components/charts/ESGPillarsBarChart";
import GreenwashingPieChart from "@/components/charts/GreenwashingPieChart";
import IntegrityGauge from "@/components/charts/IntegrityGauge";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PillarSummary {
  pillar_name: string;
  summary?: string | null;
  strengths: string[];
  weaknesses: string[];
  score?: number | null;
}

interface Indicator {
  name?: string | null;
  pillar: string;
  value?: string | null;
  year?: string | null;
  trend?: string | null;
  unit?: string | null;
}

interface GreenwashingClaim {
  text: string;
  category: string;
  risk_level: string;
  justification: string;
  is_verifiable: boolean;
}

interface ESGAnalysis {
  company_name?: string | null;
  reporting_period?: string | null;
  industry?: string | null;
  country?: string | null;
  global_summary?: string | null;
  environmental_summary: PillarSummary;
  social_summary: PillarSummary;
  governance_summary: PillarSummary;
  indicators: Indicator[];
}

interface Greenwashing {
  integrity_score: number;
  overall_risk: string;
  summary: string;
  claims: GreenwashingClaim[];
}

interface Strategy {
  priority_actions: string[];
  short_term: string[];
  mid_term: string[];
  long_term: string[];
  improvement_plan?: string | null;
}

interface PipelineResult {
  esg_analysis: ESGAnalysis;
  greenwashing: Greenwashing;
  strategy: Strategy;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const colors = {
  blue: { bg: "bg-blue-50", text: "text-blue-700" },
  orange: { bg: "bg-orange-50", text: "text-orange-700" },
  green: { bg: "bg-green-50", text: "text-green-700" },
};

function getRiskBadgeColor(risk: string): string {
  switch (risk?.toLowerCase()) {
    case "high":
    case "haut":
      return "bg-red-100 text-red-800 border border-red-200";
    case "medium":
    case "moyen":
      return "bg-yellow-100 text-yellow-800 border border-yellow-200";
    default:
      return "bg-green-100 text-green-800 border border-green-200";
  }
}

/**
 * Render a list of strings with a per-item icon, falling back to a message
 * when the list is empty. Fixes the broken `[].map() || fallback` pattern:
 * Array.map() always returns a truthy array even if empty.
 */
function StringList({
  items,
  icon,
  emptyMessage,
}: {
  items: string[];
  icon: React.ReactNode;
  emptyMessage: string;
}) {
  if (!items || items.length === 0) {
    return <li className="text-gray-400 italic">{emptyMessage}</li>;
  }
  return (
    <>
      {items.map((s, idx) => (
        <li key={idx} className="flex items-start gap-2">
          <span className="mt-1 shrink-0">{icon}</span>
          <span>{s}</span>
        </li>
      ))}
    </>
  );
}

/** Render a timeline recommendation list with a numbered fallback. */
function RecommendationList({
  items,
  emptyMessage,
}: {
  items: string[];
  emptyMessage: string;
}) {
  if (!items || items.length === 0) {
    return <li className="text-gray-400 italic">{emptyMessage}</li>;
  }
  return (
    <>
      {items.map((rec, idx) => (
        <li key={idx}>{rec}</li>
      ))}
    </>
  );
}

/** Render a pillar card — Environmental, Social, or Governance. */
function PillarCard({
  pillar,
  colorSet,
  badge,
}: {
  pillar: PillarSummary;
  colorSet: { bg: string; text: string };
  badge: string;
}) {
  return (
    <div className="rounded-2xl p-6 shadow-md border border-gray-100 bg-white">
      <div className="flex items-center justify-between mb-4">
        <h3 className={`text-lg font-bold ${colorSet.text}`}>
          {pillar.pillar_name}
        </h3>
        <span
          className={`px-2.5 py-0.5 text-xs font-semibold rounded-full ${colorSet.bg} ${colorSet.text}`}
        >
          {badge}
        </span>
      </div>
      <p className="text-gray-600 text-sm mb-4 leading-relaxed">
        {pillar.summary || (
          <span className="italic text-gray-400">
            No summary available for this pillar.
          </span>
        )}
      </p>
      <div className="space-y-4">
        <div>
          <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">
            Strengths
          </h4>
          <ul className="space-y-1 text-sm text-gray-700">
            <StringList
              items={pillar.strengths}
              icon={<FaCheckCircle className="text-green-500" />}
              emptyMessage="No specific strengths identified"
            />
          </ul>
        </div>
        <div>
          <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">
            Areas for Improvement
          </h4>
          <ul className="space-y-1 text-sm text-gray-700">
            <StringList
              items={pillar.weaknesses}
              icon={<FaExclamationTriangle className="text-yellow-500" />}
              emptyMessage="No specific weaknesses identified"
            />
          </ul>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function DashboardPage() {
  const [results, setResults] = useState<PipelineResult | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const cached = localStorage.getItem("esg_results");
    if (cached) {
      try {
        setResults(JSON.parse(cached));
      } catch (e) {
        console.error("Error parsing ESG results", e);
      }
    }
    setLoading(false);
  }, []);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-100">
        <div className="text-center">
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-green-600 border-t-transparent mx-auto" />
          <p className="mt-4 text-gray-600 font-semibold">
            Loading analysis dashboard...
          </p>
        </div>
      </div>
    );
  }

  if (!results) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-slate-100 p-6 text-center">
        <div className="max-w-md rounded-2xl bg-white p-8 shadow-xl">
          <FaExclamationTriangle className="mx-auto text-5xl text-yellow-500" />
          <h1 className="mt-4 text-2xl font-bold text-gray-900">
            No ESG Results Found
          </h1>
          <p className="mt-2 text-gray-600">
            Please upload a sustainability report first to generate a full
            analysis.
          </p>
          <button
            onClick={() => router.push("/upload")}
            className="mt-6 w-full rounded-xl bg-green-600 py-3 font-semibold text-white transition hover:bg-green-700"
          >
            Go to Upload
          </button>
        </div>
      </div>
    );
  }

  const { esg_analysis, greenwashing, strategy } = results;

  // Guard: only render greenwashing section when there are real claims
  const hasGreenwashingClaims =
    Array.isArray(greenwashing?.claims) && greenwashing.claims.length > 0;

  return (
    <div className="min-h-screen bg-slate-100 py-10 px-4 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl">

        {/* ── Top Bar ── */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-8 gap-4">
          <div>
            <button
              onClick={() => router.push("/upload")}
              className="flex items-center gap-2 text-sm text-gray-600 hover:text-green-600 font-medium mb-2 transition"
            >
              <FaArrowLeft /> Upload another report
            </button>
            <h1 className="text-4xl font-extrabold text-gray-900">
              {esg_analysis?.company_name || "Company ESG Analysis"}
            </h1>
            <p className="text-gray-500 mt-1">
              {esg_analysis?.reporting_period
                ? `Reporting Period: ${esg_analysis.reporting_period}`
                : "Reporting period not identified"}
              {esg_analysis?.industry ? ` · ${esg_analysis.industry}` : ""}
              {esg_analysis?.country ? ` · ${esg_analysis.country}` : ""}
            </p>
          </div>
          <span className="inline-flex self-start sm:self-center items-center rounded-full bg-green-100 px-4 py-2 text-sm font-semibold text-green-800 shadow-sm">
            🌍 AI Audit Complete
          </span>
        </div>

        {/* ── Global Summary ── */}
        <div className="rounded-2xl bg-white p-6 shadow-md mb-8 border border-gray-100">
          <div className="flex items-center gap-3 mb-4">
            <div className="bg-green-100 p-2 rounded-lg text-green-700">
              <FaLeaf className="text-xl" />
            </div>
            <h2 className="text-xl font-bold text-gray-900">
              Global ESG Summary
            </h2>
          </div>
          <p className="text-gray-700 leading-relaxed">
            {esg_analysis?.global_summary || (
              <span className="italic text-gray-400">
                No global summary available.
              </span>
            )}
          </p>
        </div>

        {/* ── ESG Pillars ── */}
        <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center gap-2">
          <FaLeaf className="text-green-600" /> ESG Performance Pillars
        </h2>
        <div className="grid gap-6 md:grid-cols-3 mb-8">
          {esg_analysis?.environmental_summary && (
            <PillarCard
              pillar={esg_analysis.environmental_summary}
              colorSet={colors.green}
              badge="Environmental"
            />
          )}
          {esg_analysis?.social_summary && (
            <PillarCard
              pillar={esg_analysis.social_summary}
              colorSet={colors.blue}
              badge="Social"
            />
          )}
          {esg_analysis?.governance_summary && (
            <PillarCard
              pillar={esg_analysis.governance_summary}
              colorSet={colors.orange}
              badge="Governance"
            />
          )}
        </div>

        {/* ── ESG Bar Chart ── */}
        {esg_analysis && (
          <div className="mb-8">
            <ESGPillarsBarChart
              environmental={esg_analysis.environmental_summary}
              social={esg_analysis.social_summary}
              governance={esg_analysis.governance_summary}
            />
          </div>
        )}

        {/* ── Key Indicators ── */}
        {esg_analysis?.indicators && esg_analysis.indicators.length > 0 && (
          <div className="rounded-2xl bg-white p-6 shadow-md border border-gray-100 mb-8">
            <h3 className="text-xl font-bold text-gray-900 mb-4">
              Key Indicators
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-gray-500">
                <thead className="bg-slate-50 text-xs font-bold text-gray-700 uppercase">
                  <tr>
                    <th className="px-6 py-3 rounded-l-lg">Indicator Name</th>
                    <th className="px-6 py-3">Pillar</th>
                    <th className="px-6 py-3">Value</th>
                    <th className="px-6 py-3">Year</th>
                    <th className="px-6 py-3 rounded-r-lg">Trend</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {esg_analysis.indicators.map((ind, idx) => (
                    <tr key={idx} className="bg-white hover:bg-slate-50">
                      <td className="px-6 py-4 font-semibold text-gray-900">
                        {ind.name ?? "—"}
                      </td>
                      <td className="px-6 py-4">{ind.pillar}</td>
                      <td className="px-6 py-4 font-mono text-green-700 font-bold">
                        {ind.value ?? "—"}
                      </td>
                      <td className="px-6 py-4">{ind.year || "N/A"}</td>
                      <td className="px-6 py-4 capitalize">
                        {ind.trend || "N/A"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ── Greenwashing Risk Audit ── */}
        {/* Only render this entire section when there are real claims */}
        {greenwashing && hasGreenwashingClaims && (
          <>
            <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center gap-2">
              <FaRobot className="text-blue-600" /> Greenwashing Risk Audit
            </h2>
            <div className="grid gap-6 md:grid-cols-3 mb-8">
              {/* Integrity Gauge */}
              <div className="md:col-span-1">
                <IntegrityGauge
                  score={greenwashing.integrity_score}
                  riskLevel={greenwashing.overall_risk}
                />
              </div>

              {/* Audit Details */}
              <div className="rounded-2xl bg-white p-6 shadow-md border border-gray-100 md:col-span-2">
                <h3 className="text-lg font-bold text-gray-900 mb-3">
                  Greenwashing Summary
                </h3>
                <p className="text-gray-700 leading-relaxed text-sm mb-6">
                  {greenwashing.summary || (
                    <span className="italic text-gray-400">
                      No greenwashing assessment summary available.
                    </span>
                  )}
                </p>

                <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">
                  Claims Verifiability Audit
                </h4>
                <div className="space-y-4 max-h-[300px] overflow-y-auto pr-2">
                  {greenwashing.claims.map((c, idx) => (
                    <div
                      key={idx}
                      className="rounded-xl border border-gray-100 p-4 bg-slate-50"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                        <span className="text-sm font-semibold text-gray-900">
                          &ldquo;{c.text}&rdquo;
                        </span>
                        <div className="flex items-center gap-2">
                          <span
                            className={`px-2 py-0.5 text-xs font-semibold rounded-full ${getRiskBadgeColor(
                              c.risk_level
                            )}`}
                          >
                            {c.risk_level} Risk
                          </span>
                          {c.is_verifiable ? (
                            <span className="inline-flex items-center gap-1 text-xs font-semibold text-green-700 bg-green-50 border border-green-100 px-2 py-0.5 rounded-full">
                              <FaCheckCircle /> Verifiable
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-xs font-semibold text-red-700 bg-red-50 border border-red-100 px-2 py-0.5 rounded-full">
                              <FaTimesCircle /> Unverifiable
                            </span>
                          )}
                        </div>
                      </div>
                      <p className="text-xs text-gray-600 leading-relaxed">
                        <strong className="text-gray-800">Audit Finding:</strong>{" "}
                        {c.justification}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Pie Chart */}
            <div className="mb-8">
              <GreenwashingPieChart
                claims={greenwashing.claims}
                overallRisk={greenwashing.overall_risk}
              />
            </div>
          </>
        )}

        {/* ── Strategic Action Plan ── */}
        {strategy && (
          <>
            <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center gap-2">
              <FaChartLine className="text-emerald-600" /> Strategic Action Plan
            </h2>
            <div className="grid gap-6 md:grid-cols-3 mb-8">
              {/* Priority Actions */}
              <div className="rounded-2xl bg-amber-50/50 p-6 shadow-md border border-amber-100 md:col-span-1">
                <h3 className="text-lg font-bold text-amber-900 mb-4 flex items-center gap-2">
                  <FaExclamationTriangle className="text-amber-600" /> Priority
                  Actions
                </h3>
                <ul className="space-y-3 text-sm text-amber-950 font-medium">
                  {!strategy.priority_actions ||
                  strategy.priority_actions.length === 0 ? (
                    <li className="italic text-amber-700/60">
                      No priority actions generated
                    </li>
                  ) : (
                    strategy.priority_actions.map((act, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-amber-200 text-xs font-bold text-amber-800 mt-0.5">
                          {idx + 1}
                        </span>
                        <span>{act}</span>
                      </li>
                    ))
                  )}
                </ul>
              </div>

              {/* Roadmap Timeline */}
              <div className="rounded-2xl bg-white p-6 shadow-md border border-gray-100 md:col-span-2">
                <h3 className="text-lg font-bold text-gray-900 mb-4">
                  Strategic Timeline
                </h3>
                <div className="space-y-6 relative border-l border-gray-100 pl-4 ml-2">
                  {/* Short Term */}
                  <div className="relative">
                    <div className="absolute -left-[25px] top-0.5 bg-blue-100 text-blue-700 p-1 rounded-full border-2 border-white">
                      <FaClock className="text-xs" />
                    </div>
                    <h4 className="text-sm font-bold text-gray-900 mb-1">
                      Short Term (0 – 6 Months)
                    </h4>
                    <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
                      <RecommendationList
                        items={strategy.short_term}
                        emptyMessage="No short-term recommendations generated"
                      />
                    </ul>
                  </div>

                  {/* Mid Term */}
                  <div className="relative">
                    <div className="absolute -left-[25px] top-0.5 bg-indigo-100 text-indigo-700 p-1 rounded-full border-2 border-white">
                      <FaClock className="text-xs" />
                    </div>
                    <h4 className="text-sm font-bold text-gray-900 mb-1">
                      Medium Term (6 – 24 Months)
                    </h4>
                    <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
                      <RecommendationList
                        items={strategy.mid_term}
                        emptyMessage="No medium-term recommendations generated"
                      />
                    </ul>
                  </div>

                  {/* Long Term */}
                  <div className="relative">
                    <div className="absolute -left-[25px] top-0.5 bg-purple-100 text-purple-700 p-1 rounded-full border-2 border-white">
                      <FaClock className="text-xs" />
                    </div>
                    <h4 className="text-sm font-bold text-gray-900 mb-1">
                      Long Term (2+ Years)
                    </h4>
                    <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
                      <RecommendationList
                        items={strategy.long_term}
                        emptyMessage="No long-term recommendations generated"
                      />
                    </ul>
                  </div>
                </div>
              </div>
            </div>

            {/* Improvement Roadmap Card */}
            <div className="rounded-2xl bg-white p-6 shadow-md border border-gray-100">
              <h3 className="text-lg font-bold text-gray-900 mb-3">
                Improvement Roadmap Summary
              </h3>
              <p className="text-gray-700 leading-relaxed text-sm">
                {strategy.improvement_plan || (
                  <span className="italic text-gray-400">
                    No detailed strategic improvement roadmap available.
                  </span>
                )}
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}