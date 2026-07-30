import Link from "next/link";
import { FaLeaf, FaRobot, FaChartLine } from "react-icons/fa";

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-green-50 via-white to-emerald-100">

      {/* Hero */}
      <section className="mx-auto flex max-w-7xl flex-col items-center px-6 py-24 text-center">

        <span className="rounded-full bg-green-100 px-5 py-2 text-green-700 font-semibold">
          🌍 AI for Sustainable Development
        </span>

        <h1 className="mt-8 text-6xl font-extrabold text-gray-900">
          ESG Multi-Agents
          <span className="block text-green-600">
            Platform
          </span>
        </h1>

        <p className="mt-8 max-w-3xl text-xl leading-9 text-gray-800">
          Analyze ESG reports using autonomous AI agents capable of
          evaluating sustainability performance, detecting
          greenwashing risks, and generating actionable strategic
          recommendations.
        </p>

        <div className="mt-12 flex gap-6">

          <Link
            href="/upload"
            className="rounded-xl bg-green-600 px-8 py-4 text-lg font-semibold text-white shadow-lg transition hover:bg-green-700"
          >
            🚀 Get Started
          </Link>

          <Link
            href="#features"
            className="rounded-xl border border-green-600 px-8 py-4 text-lg font-semibold text-green-700 transition hover:bg-green-100"
          >
            Learn More
          </Link>

        </div>

      </section>

      {/* Features */}

      <section
        id="features"
        className="mx-auto grid max-w-7xl gap-8 px-8 pb-24 md:grid-cols-3"
      >

        <div className="rounded-2xl bg-white p-8 shadow-lg transition hover:-translate-y-2 hover:shadow-2xl">

          <FaLeaf className="text-5xl text-green-600" />

          <h2 className="mt-6 text-2xl font-bold">
            ESG Analysis
          </h2>

          <p className="mt-4 text-gray-600">
            Evaluate Environmental, Social and Governance
            performance from sustainability reports.
          </p>

        </div>

        <div className="rounded-2xl bg-white p-8 shadow-lg transition hover:-translate-y-2 hover:shadow-2xl">

          <FaRobot className="text-5xl text-blue-600" />

          <h2 className="mt-6 text-2xl font-bold">
            Greenwashing Detection
          </h2>

          <p className="mt-4 text-gray-600">
            Detect misleading sustainability claims using
            autonomous AI agents.
          </p>

        </div>

        <div className="rounded-2xl bg-white p-8 shadow-lg transition hover:-translate-y-2 hover:shadow-2xl">

          <FaChartLine className="text-5xl text-emerald-600" />

          <h2 className="mt-6 text-2xl font-bold">
            Strategy Generator
          </h2>

          <p className="mt-4 text-gray-600">
            Generate personalized ESG improvement strategies
            and long-term sustainability plans.
          </p>

        </div>

      </section>

      {/* Workflow */}

      <section className="bg-white py-20">

        <div className="mx-auto max-w-6xl text-center">

          <h2 className="text-4xl font-bold text-gray-900">
            How It Works
          </h2>

          <div className="mt-14 grid gap-10 md:grid-cols-4">

            <div>
              <div className="text-5xl">📄</div>
              <h3 className="mt-4 font-bold">
                Upload PDF
              </h3>
            </div>

            <div>
              <div className="text-5xl">🤖</div>
              <h3 className="mt-4 font-bold">
                AI Analysis
              </h3>
            </div>

            <div>
              <div className="text-5xl">⚠️</div>
              <h3 className="mt-4 font-bold">
                Risk Detection
              </h3>
            </div>

            <div>
              <div className="text-5xl">📊</div>
              <h3 className="mt-4 font-bold">
                Dashboard
              </h3>
            </div>

          </div>

        </div>

      </section>

    </main>
  );
}
