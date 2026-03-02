"use client";

import { useState } from "react";

const EXAMPLE_QUERIES = [
  "Where is the main entry point of this program?",
  "What functions modify the CUSTOMER-RECORD?",
  "Explain what the CALCULATE-INTEREST paragraph does",
  "Find all file I/O operations",
  "Show me error handling patterns in this codebase",
];

export default function Home() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState<
    { file: string; paragraph: string; start_line: number; end_line: number; snippet: string }[]
  >([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const handleSubmit = async () => {
    if (!question.trim()) return;
    setLoading(true);
    setError(null);
    setAnswer("");
    setSources([]);
    try {
      const res = await fetch(`${apiUrl}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: question.trim() }),
      });
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const data = await res.json();
      setAnswer(data.answer);
      setSources(data.sources || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <div className="mx-auto max-w-3xl px-6 py-16">
        <h1 className="mb-2 text-3xl font-bold tracking-tight">Legacy Lens</h1>
        <p className="mb-10 text-gray-400">
          Query the GnuCOBOL codebase in natural language
        </p>

        <div className="mb-6">
          <div className="flex gap-2">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about the COBOL codebase..."
              className="flex-1 rounded-lg border border-gray-700 bg-gray-900 px-4 py-3 text-gray-100 placeholder-gray-500 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              disabled={loading}
            />
            <button
              onClick={handleSubmit}
              disabled={loading || !question.trim()}
              className="rounded-lg bg-emerald-600 px-6 py-3 font-medium text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? "Asking..." : "Ask"}
            </button>
          </div>
        </div>

        <div className="mb-8 flex flex-wrap gap-2">
          {EXAMPLE_QUERIES.map((q) => (
            <button
              key={q}
              onClick={() => {
                setQuestion(q);
              }}
              className="rounded-full border border-gray-600 bg-gray-900 px-4 py-2 text-sm text-gray-300 transition hover:border-emerald-600 hover:text-emerald-400"
            >
              {q}
            </button>
          ))}
        </div>

        {error && (
          <div className="mb-6 rounded-lg border border-red-800 bg-red-950/30 px-4 py-3 text-red-400">
            {error}
          </div>
        )}

        {answer && (
          <div className="mb-8 rounded-lg border border-gray-800 bg-gray-900/50 p-6">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-400">
              Answer
            </h2>
            <div className="whitespace-pre-wrap text-gray-200">{answer}</div>
          </div>
        )}

        {sources.length > 0 && (
          <div className="space-y-4">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-400">
              Sources
            </h2>
            {sources.map((s, i) => (
              <div
                key={i}
                className="rounded-lg border border-gray-800 bg-gray-900/50 p-4"
              >
                <div className="mb-2 flex flex-wrap gap-2">
                  <span className="rounded bg-emerald-900/50 px-2 py-0.5 text-xs font-medium text-emerald-400">
                    {s.file}
                  </span>
                  <span className="rounded bg-gray-700 px-2 py-0.5 text-xs text-gray-300">
                    {s.paragraph}
                  </span>
                  <span className="rounded bg-gray-700 px-2 py-0.5 text-xs text-gray-400">
                    L{s.start_line}–{s.end_line}
                  </span>
                </div>
                <pre className="overflow-x-auto rounded bg-gray-950 p-3 text-sm text-gray-300">
                  {s.snippet}
                </pre>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
