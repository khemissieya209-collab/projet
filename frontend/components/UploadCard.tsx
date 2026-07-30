"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { FaCloudUploadAlt, FaFilePdf } from "react-icons/fa";

export default function UploadCard() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const handleAnalyze = async () => {
    if (!file) return;

    setLoading(true);
    setError(null);

    try {
      // Build FormData with the PDF
      const formData = new FormData();
      formData.append("file", file);

      // Single API call — the backend pipeline handles everything
      const response = await fetch("http://localhost:8000/upload", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      // The backend returns the complete PipelineResult JSON
      const result = await response.json();

      // Persist the full result for the dashboard
      localStorage.setItem("esg_results", JSON.stringify(result));

      // Redirect to the dashboard
      router.push("/dashboard");
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "An unexpected error occurred.";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto mt-10 max-w-3xl rounded-3xl bg-white p-10 shadow-2xl">

      <div className="text-center">

        <FaCloudUploadAlt className="mx-auto text-6xl text-green-600" />

        <h1 className="mt-6 text-4xl font-bold text-gray-900">
          Upload ESG Report
        </h1>

        <p className="mt-4 text-gray-600">
          Upload your Sustainability Report (PDF)
          and let our AI Multi-Agent System analyze it.
        </p>

      </div>

      <label className="mt-10 flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-green-400 bg-green-50 p-12 transition hover:bg-green-100">

        <FaFilePdf className="text-5xl text-red-500" />

        <p className="mt-5 text-lg font-semibold">
          Drag & Drop your PDF here
        </p>

        <p className="text-gray-500">
          or click to browse
        </p>

        <input
          type="file"
          accept=".pdf"
          className="hidden"
          onChange={(e) => {
            if (e.target.files) {
              setFile(e.target.files[0]);
            }
          }}
        />

      </label>

      {file && (

        <div className="mt-8 rounded-xl bg-green-100 p-4">

          <p className="font-semibold text-green-800">
            Selected file
          </p>

          <p className="mt-2">
            📄 {file.name}
          </p>

        </div>

      )}

      {error && (

        <div className="mt-6 rounded-xl bg-red-100 p-4 text-red-700">
          ⚠️ {error}
        </div>

      )}

      <button
        onClick={handleAnalyze}
        disabled={!file || loading}
        className="mt-10 w-full rounded-xl bg-green-600 py-4 text-lg font-bold text-white transition hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {loading ? "⏳ Analyzing..." : "🚀 Analyze Report"}
      </button>

    </div>
  );
}