"use client";

import { useState, useEffect } from "react";
import SyntaxHighlighter from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";

type TabId = "query" | "dependencies" | "document" | "patterns" | "business-logic";

type SourceItem = {
  file: string;
  path?: string;
  paragraph: string;
  start_line: number;
  end_line: number;
  snippet: string;
  score?: number;
  source?: string;
};

const TABS: { id: TabId; label: string }[] = [
  { id: "query", label: "🔍 Ask a Question" },
  { id: "dependencies", label: "🔗 Dependencies" },
  { id: "document", label: "📄 Documentation" },
  { id: "patterns", label: "🔎 Patterns" },
  { id: "business-logic", label: "💼 Business Logic" },
];

const EXAMPLE_QUERIES: Record<TabId, string[]> = {
  query: [
    "Where is the main entry point of this program?",
    "Find all file I/O operations",
    "Show me error handling patterns in this codebase",
    "What does the PROCEDURE DIVISION do?",
  ],
  dependencies: [
    "What does MAIN-SECTION call?",
    "What calls the STOP-RUN paragraph?",
    "Show the call graph for this program",
  ],
  document: [
    "Generate docs for the main entry point",
    "Document the file I/O section",
    "Explain the PROCEDURE DIVISION",
  ],
  patterns: [
    "Find all OPEN READ WRITE operations",
    "Show all error handling patterns",
    "Find all PERFORM statements",
  ],
  "business-logic": [
    "Extract business rules from file I/O section",
    "What business process does error handling implement?",
    "Explain the business logic of the main procedure",
  ],
};

const PLACEHOLDERS: Record<TabId, string> = {
  query: "Ask about the COBOL codebase...",
  dependencies: "Ask about what calls what (e.g. What does MAIN-SECTION call?)",
  document: "Enter a paragraph or file name to generate documentation for",
  patterns: "Search for a code pattern (e.g. OPEN READ WRITE for file I/O)",
  "business-logic": "Describe a section to extract business rules from (e.g. interest calculation, file processing)",
};

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  sources?: SourceItem[];
  latencyMs?: number;
};

type FileTreeNode = {
  name: string;
  type: "directory" | "file";
  path?: string;
  lines?: number;
  children?: FileTreeNode[];
};

export default function Home() {
  const [activeTab, setActiveTab] = useState<TabId>("query");
  const [sessionId] = useState(() => Math.random().toString(36).substring(2, 15));
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [queryInput, setQueryInput] = useState("");
  const [docInput, setDocInput] = useState("");
  const [patternInput, setPatternInput] = useState("OPEN READ WRITE");
  const [businessLogicInput, setBusinessLogicInput] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState<SourceItem[]>([]);
  const [callGraph, setCallGraph] = useState<{ caller: string; callee: string; file: string; line: number }[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [expandedFile, setExpandedFile] = useState<{ path: string; content: string; line_count: number } | null>(null);
  const [expandedSourceIdx, setExpandedSourceIdx] = useState<number | null>(null);
  const [expandedSourcesForMessage, setExpandedSourcesForMessage] = useState<number | null>(null);
  const [expandedChatSource, setExpandedChatSource] = useState<{ messageIdx: number; sourceIdx: number } | null>(null);
  const [fileTree, setFileTree] = useState<{ tree: FileTreeNode[]; total_files: number; error?: string } | null>(null);
  const [fileSearch, setFileSearch] = useState("");
  const [expandedDirs, setExpandedDirs] = useState<Set<string>>(new Set());
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [fileModal, setFileModal] = useState<{ path: string; content: string; line_count: number } | null>(null);
  const [selectedFilePath, setSelectedFilePath] = useState<string | null>(null);
  const [expandedMessageIdx, setExpandedMessageIdx] = useState<number | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const askedQuestions = new Set(chatHistory.filter((m) => m.role === "user").map((m) => m.content.trim().toLowerCase()));
  const suggestedQueries = EXAMPLE_QUERIES[activeTab].filter(
    (q) => !askedQuestions.has(q.trim().toLowerCase())
  );

  const formatLineRange = (start: number, end: number) => {
    if (end > start && end - start > 1000) return `L${start}–${end} (large range)`;
    return `L${start}–${end}`;
  };

  useEffect(() => {
    fetch(`${apiUrl}/files`)
      .then((r) => r.json())
      .then((d) => setFileTree(d))
      .catch(() => setFileTree({ tree: [], total_files: 0, error: "Failed to load" }));
  }, [apiUrl]);

  const filterTree = (nodes: FileTreeNode[], search: string): FileTreeNode[] => {
    if (!search.trim()) return nodes;
    const q = search.toLowerCase();
    return nodes
      .map((n) => {
        if (n.type === "file") {
          return n.name.toLowerCase().includes(q) ? n : null;
        }
        const filtered = filterTree(n.children || [], search);
        return filtered.length > 0 ? { ...n, children: filtered } : null;
      })
      .filter((n): n is FileTreeNode => n !== null);
  };

  const toggleDir = (path: string) => {
    setExpandedDirs((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  const handleFileClick = async (path: string) => {
    setSelectedFilePath(path);
    setSidebarOpen(false);
    try {
      const res = await fetch(`${apiUrl}/file?path=${encodeURIComponent(path)}`);
      const data = await res.json();
      if (data.error || !data.content) {
        setError("File not available. Codebase may not be deployed in production.");
        return;
      }
      setFileModal({ path: data.path, content: data.content, line_count: data.line_count });
    } catch {
      setError("Failed to load file.");
    }
  };

  const getInput = () => {
    if (activeTab === "query") return queryInput;
    if (activeTab === "dependencies") return queryInput;
    if (activeTab === "document") return docInput;
    if (activeTab === "business-logic") return businessLogicInput;
    return patternInput;
  };

  const setInput = (v: string) => {
    if (activeTab === "query" || activeTab === "dependencies") setQueryInput(v);
    else if (activeTab === "document") setDocInput(v);
    else if (activeTab === "business-logic") setBusinessLogicInput(v);
    else setPatternInput(v);
  };

  const canSubmit = () => {
    if (activeTab === "query" || activeTab === "dependencies") return queryInput.trim();
    if (activeTab === "document") return docInput.trim();
    if (activeTab === "business-logic") return businessLogicInput.trim();
    return patternInput.trim();
  };

  const handleClearConversation = async () => {
    try {
      await fetch(`${apiUrl}/clear-history`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });
      setChatHistory([]);
      setExpandedSourcesForMessage(null);
      setExpandedChatSource(null);
      setExpandedMessageIdx(null);
    } catch {
      setChatHistory([]);
      setExpandedMessageIdx(null);
    }
  };

  const handleSubmit = async (overrideQuestion?: string) => {
    const canSend = activeTab === "query"
      ? (overrideQuestion ? overrideQuestion.trim() : queryInput.trim())
      : canSubmit();
    if (!canSend) return;
    setLoading(true);
    setError(null);
    if (activeTab !== "query") {
      setAnswer("");
      setSources([]);
      setCallGraph([]);
      setLatencyMs(null);
    }
    setExpandedFile(null);
    setExpandedSourceIdx(null);

    try {
      if (activeTab === "query") {
        const question = (overrideQuestion ?? queryInput).trim();
        const res = await fetch(`${apiUrl}/query`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question, session_id: sessionId }),
        });
        if (!res.ok) throw new Error(`API error: ${res.status}`);
        const data = await res.json();
        setChatHistory((prev) => [
          ...prev,
          { role: "user" as const, content: question },
          {
            role: "assistant" as const,
            content: data.answer,
            sources: data.sources || [],
            latencyMs: data.latency_ms ?? undefined,
          },
        ]);
        if (!overrideQuestion) setQueryInput("");
      } else if (activeTab === "dependencies") {
        const res = await fetch(`${apiUrl}/dependencies`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: queryInput.trim() || undefined }),
        });
        if (!res.ok) throw new Error(`API error: ${res.status}`);
        const data = await res.json();
        setAnswer(data.answer);
        setSources(data.sources || []);
        setCallGraph(data.call_graph || []);
        setLatencyMs(data.latency_ms ?? null);
      } else if (activeTab === "document") {
        const res = await fetch(`${apiUrl}/document`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ paragraph: docInput.trim(), file_name: docInput.trim() }),
        });
        if (!res.ok) throw new Error(`API error: ${res.status}`);
        const data = await res.json();
        setAnswer(data.documentation);
        setSources(data.sources || []);
        setLatencyMs(data.latency_ms ?? null);
      } else if (activeTab === "business-logic") {
        const res = await fetch(`${apiUrl}/business-logic`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: businessLogicInput.trim() }),
        });
        if (!res.ok) throw new Error(`API error: ${res.status}`);
        const data = await res.json();
        setAnswer(data.business_logic);
        setSources(data.sources || []);
        setLatencyMs(data.latency_ms ?? null);
      } else {
        const res = await fetch(`${apiUrl}/patterns`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ keyword: patternInput.trim() }),
        });
        if (!res.ok) throw new Error(`API error: ${res.status}`);
        const data = await res.json();
        setAnswer(data.answer);
        setSources(data.sources || []);
        setLatencyMs(data.latency_ms ?? null);
      }
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

  const handleViewFullFile = async (sourcePath: string, idx: number) => {
    if (!sourcePath) return;
    if (expandedSourceIdx === idx && expandedFile) {
      setExpandedFile(null);
      setExpandedSourceIdx(null);
      return;
    }
    try {
      const res = await fetch(`${apiUrl}/file?path=${encodeURIComponent(sourcePath)}`);
      const data = await res.json();
      if (data.error || !res.ok) {
        setError("Full file preview is not available in production. Clone the repo locally to use this feature.");
        return;
      }
      setError(null);
      setExpandedFile({ path: data.path, content: data.content, line_count: data.line_count });
      setExpandedSourceIdx(idx);
    } catch {
      setError("Full file preview is not available in production. Clone the repo locally to use this feature.");
    }
  };

  const getButtonLabel = () => {
    if (loading) return "Loading...";
    if (activeTab === "query") return "Ask";
    if (activeTab === "dependencies") return "Search";
    if (activeTab === "document") return "Generate";
    if (activeTab === "business-logic") return "Extract";
    return "Search";
  };

  const renderFileTree = (nodes: FileTreeNode[], parentPath: string = "") =>
    nodes.map((n) => {
      const fullPath = parentPath ? `${parentPath}/${n.name}` : n.name;
      if (n.type === "directory") {
        const isExpanded = expandedDirs.has(fullPath);
        return (
          <div key={fullPath} className="select-none">
            <button
              onClick={() => toggleDir(fullPath)}
              className="flex w-full items-center gap-1 px-2 py-1 text-left text-sm text-gray-300 hover:bg-gray-800"
            >
              <span className="w-4 text-gray-500">{isExpanded ? "▼" : "▶"}</span>
              {n.name}
            </button>
            {isExpanded && (
              <div className="ml-4 border-l border-gray-700 pl-1">
                {renderFileTree(n.children || [], fullPath)}
              </div>
            )}
          </div>
        );
      }
      return (
        <button
          key={n.path || fullPath}
          onClick={() => handleFileClick(n.path || fullPath)}
          className={`flex w-full items-center justify-between gap-2 px-2 py-1 text-left text-sm hover:bg-gray-800 ${
            selectedFilePath === (n.path || fullPath) ? "bg-blue-900/50 text-blue-300" : "text-gray-300"
          }`}
        >
          <span className="truncate">{n.name}</span>
          {n.lines != null && <span className="shrink-0 text-xs text-gray-500">{n.lines}</span>}
        </button>
      );
    });

  return (
    <div className="flex min-h-screen bg-gray-950 text-gray-100">
      {/* Mobile hamburger */}
      <button
        onClick={() => setSidebarOpen((o) => !o)}
        className="fixed left-4 top-4 z-50 rounded border border-gray-600 bg-gray-900 p-2 text-xl md:hidden"
      >
        📁
      </button>

      {/* Sidebar backdrop (mobile) */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar - left column, always visible on md+ */}
      <div
        className={`w-64 flex-shrink-0 overflow-y-auto border-r border-gray-700 bg-gray-900 ${
          sidebarOpen ? "fixed inset-y-0 left-0 z-40 translate-x-0 md:relative md:translate-x-0" : "hidden md:block"
        }`}
      >
        <div className="p-4 pt-14 md:pt-4">
          <div className="mb-3 flex items-center gap-2">
            <h2 className="font-semibold text-gray-200">📁 Files</h2>
            {fileTree && !fileTree.error && (
              <span className="rounded bg-gray-700 px-2 py-0.5 text-xs text-gray-400">
                {fileTree.total_files}
              </span>
            )}
          </div>
          {fileTree?.error || (fileTree && fileTree.tree.length === 0) ? (
            <div className="space-y-2 text-sm text-gray-500">
              <p>File tree available when running locally.</p>
              <p className="text-xs">Clone the repo and run the frontend to browse the codebase.</p>
            </div>
          ) : (
            <>
              <input
                type="text"
                value={fileSearch}
                onChange={(e) => setFileSearch(e.target.value)}
                placeholder="Search files..."
                className="mb-3 w-full rounded border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:border-emerald-500 focus:outline-none"
              />
              <div className="space-y-0.5">
                {fileTree && renderFileTree(filterTree(fileTree.tree, fileSearch))}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Main content - right column */}
      <main className="flex-1 overflow-auto">
        <div className="mx-auto max-w-3xl px-6 py-16">
          <h1 className="mb-2 text-3xl font-bold tracking-tight">Legacy Lens</h1>
        <p className="mb-10 text-gray-400">
          Query the COBOL codebase in natural language
        </p>

        {/* Tab bar - always visible above main content */}
        <div className="mb-6 flex items-center justify-between gap-4 border-b border-gray-700 overflow-x-auto">
          <div className="flex gap-1 shrink-0">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-2 text-sm font-medium transition ${
                  activeTab === tab.id
                    ? "border-b-2 border-blue-500 text-blue-400"
                    : "text-gray-400 hover:text-gray-200"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
          {activeTab === "query" && (
            <button
              onClick={handleClearConversation}
              className="rounded border border-gray-600 bg-gray-800 px-3 py-1.5 text-sm text-gray-300 hover:bg-gray-700"
            >
              🗑 Clear conversation
            </button>
          )}
        </div>

        {/* Chat history (Ask a Question tab only) */}
        {activeTab === "query" && chatHistory.length > 0 && (
          <div className="mb-6 space-y-4">
            {chatHistory.map((msg, msgIdx) => {
              const isExpanded = expandedMessageIdx === msgIdx;
              const contentPreviewLen = 180;
              const showExpand = msg.role === "assistant" && msg.content.length > contentPreviewLen;
              const displayContent = showExpand && !isExpanded
                ? msg.content.slice(0, contentPreviewLen) + (msg.content.length > contentPreviewLen ? "…" : "")
                : msg.content;

              return (
                <div
                  key={msgIdx}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[85%] rounded-lg px-4 py-3 ${
                      msg.role === "user"
                        ? "bg-blue-600 text-white"
                        : "bg-gray-800 text-gray-200"
                    }`}
                  >
                    <div className="whitespace-pre-wrap">{displayContent}</div>
                    {showExpand && (
                      <button
                        onClick={() => setExpandedMessageIdx(isExpanded ? null : msgIdx)}
                        className="mt-1 text-xs text-emerald-400 hover:text-emerald-300"
                      >
                        {isExpanded ? "Show less" : "Show more"}
                      </button>
                    )}
                    {msg.role === "assistant" && msg.latencyMs != null && (
                      <div className="mt-2 text-xs text-gray-500">⚡ {msg.latencyMs}ms</div>
                    )}
                    {msg.role === "assistant" && msg.sources && msg.sources.length > 0 && (
                      <div className="mt-3">
                        <button
                          onClick={() =>
                            setExpandedSourcesForMessage(
                              expandedSourcesForMessage === msgIdx ? null : msgIdx
                            )
                          }
                          className="text-xs text-emerald-400 hover:text-emerald-300"
                        >
                          {expandedSourcesForMessage === msgIdx
                            ? "Hide sources ▲"
                            : `Show ${msg.sources.length} source${msg.sources.length === 1 ? "" : "s"} ▼`}
                        </button>
                        {expandedSourcesForMessage === msgIdx && (
                          <div className="mt-3 space-y-2">
                            {msg.sources.map((s, sIdx) => (
                              <div
                                key={sIdx}
                                className="rounded-lg border border-gray-700 bg-gray-900/80 p-3"
                              >
                                <div className="mb-2 grid grid-cols-[1fr_auto_auto] gap-2 items-center text-xs sm:flex sm:flex-wrap">
                                  <span className="font-medium text-emerald-400 truncate" title={s.file}>
                                    {s.file}
                                  </span>
                                  <span className="text-gray-400">
                                    {formatLineRange(s.start_line, s.end_line)}
                                  </span>
                                  {s.score != null && (
                                    <span
                                      className={`shrink-0 px-2 py-0.5 rounded-full font-medium ${
                                        s.score >= 80 ? "bg-green-900 text-green-300" :
                                        s.score >= 50 ? "bg-yellow-900 text-yellow-300" :
                                        "bg-red-900 text-red-300"
                                      }`}
                                    >
                                      {typeof s.score === "number" ? s.score.toFixed(1) : s.score}%
                                    </span>
                                  )}
                                </div>
                                <SyntaxHighlighter
                                  language="cobol"
                                  style={vscDarkPlus}
                                  customStyle={{ borderRadius: "6px", fontSize: "12px" }}
                                  PreTag="div"
                                  codeTagProps={{ style: { fontFamily: "var(--font-geist-mono)" } }}
                                >
                                  {s.snippet}
                                </SyntaxHighlighter>
                                {(s.source || s.path) && (
                                  <button
                                    onClick={() => {
                                      if (
                                        expandedChatSource?.messageIdx === msgIdx &&
                                        expandedChatSource?.sourceIdx === sIdx
                                      ) {
                                        setExpandedChatSource(null);
                                        setExpandedFile(null);
                                        return;
                                      }
                                      setExpandedChatSource({ messageIdx: msgIdx, sourceIdx: sIdx });
                                      fetch(`${apiUrl}/file?path=${encodeURIComponent(s.source || s.path || "")}`)
                                        .then((r) => r.json())
                                        .then((d) => {
                                          if (d.error || !d.content) return;
                                          setExpandedFile({ path: d.path, content: d.content, line_count: d.line_count });
                                        });
                                    }}
                                    className="mt-2 rounded border border-gray-600 bg-gray-800 px-2 py-1 text-xs text-gray-300 hover:bg-gray-700"
                                  >
                                    {expandedChatSource?.messageIdx === msgIdx &&
                                    expandedChatSource?.sourceIdx === sIdx &&
                                    expandedFile
                                      ? "Collapse"
                                      : "View full file"}
                                  </button>
                                )}
                                {expandedChatSource?.messageIdx === msgIdx &&
                                  expandedChatSource?.sourceIdx === sIdx &&
                                  expandedFile && (
                                    <div className="mt-3 rounded border border-gray-700 bg-gray-950 p-3">
                                      <div className="mb-1 text-xs text-gray-400">
                                        {expandedFile.path} ({expandedFile.line_count} lines)
                                      </div>
                                      <SyntaxHighlighter
                                        language="cobol"
                                        style={vscDarkPlus}
                                        customStyle={{ borderRadius: "6px", fontSize: "12px", maxHeight: "300px" }}
                                        PreTag="div"
                                        showLineNumbers
                                      >
                                        {expandedFile.content}
                                      </SyntaxHighlighter>
                                    </div>
                                  )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Input area */}
        <div className="mb-6">
          <div className="flex gap-2">
            <input
              type="text"
              value={getInput()}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={PLACEHOLDERS[activeTab]}
              className="flex-1 rounded-lg border border-gray-700 bg-gray-900 px-4 py-3 text-gray-100 placeholder-gray-500 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              disabled={loading}
            />
            <button
              onClick={() => handleSubmit()}
              disabled={loading || !canSubmit()}
              className="rounded-lg bg-emerald-600 px-6 py-3 font-medium text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {getButtonLabel()}
            </button>
          </div>
        </div>

        {/* Example chips - hide ones already asked */}
        <div className="mb-8 flex flex-wrap gap-2">
          {(suggestedQueries.length > 0 ? suggestedQueries : EXAMPLE_QUERIES[activeTab]).map((q) => (
            <button
              key={q}
              onClick={() =>
                activeTab === "query"
                  ? handleSubmit(q)
                  : setInput(q)
              }
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

        {/* Call graph (dependencies tab only) */}
        {activeTab === "dependencies" && callGraph.length > 0 && (
          <div className="mb-8 rounded-lg border border-gray-800 bg-gray-900/50 p-6">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-400">
              Call Graph
            </h2>
            <div className="space-y-1 font-mono text-sm text-gray-300">
              {callGraph.map((cg, i) => (
                <div key={i}>
                  {cg.caller} → {cg.callee} ({cg.file}:{cg.line})
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Answer (non-query tabs only) */}
        {activeTab !== "query" && answer && (
          <div className="mb-8 rounded-lg border border-gray-800 bg-gray-900/50 p-6">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-400">
              {activeTab === "document" ? "Documentation" : activeTab === "business-logic" ? "Business Logic" : "Answer"}
            </h2>
            <div className="whitespace-pre-wrap text-gray-200">{answer}</div>
            {latencyMs != null && (
              <div className="mt-3 text-sm text-gray-500">
                ⚡ Response time: {latencyMs}ms
              </div>
            )}
          </div>
        )}

        {/* Sources (non-query tabs only) - structured cards */}
        {activeTab !== "query" && sources.length > 0 && (
          <div className="space-y-4">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-400">
              Sources ({sources.length})
            </h2>
            {sources.map((s, i) => (
              <div
                key={i}
                className="rounded-lg border border-gray-700 bg-gray-900/80 p-3"
              >
                <div className="mb-2 flex flex-wrap gap-2 items-center text-xs">
                  <span className="font-medium text-emerald-400 truncate" title={s.file}>
                    {s.file}
                  </span>
                  <span className="text-gray-400">{s.paragraph}</span>
                  <span className="text-gray-400">
                    {formatLineRange(s.start_line, s.end_line)}
                  </span>
                  {s.score != null && (
                    <span
                      className={`shrink-0 px-2 py-0.5 rounded-full font-medium ${
                        s.score >= 80 ? "bg-green-900 text-green-300" :
                        s.score >= 50 ? "bg-yellow-900 text-yellow-300" :
                        "bg-red-900 text-red-300"
                      }`}
                    >
                      {typeof s.score === "number" ? s.score.toFixed(1) : s.score}%
                    </span>
                  )}
                </div>
                <SyntaxHighlighter
                  language="cobol"
                  style={vscDarkPlus}
                  customStyle={{ borderRadius: "6px", fontSize: "12px" }}
                  PreTag="div"
                  codeTagProps={{ style: { fontFamily: "var(--font-geist-mono)" } }}
                >
                  {s.snippet}
                </SyntaxHighlighter>
                {(s.source || s.path) && (
                  <button
                    onClick={() => handleViewFullFile(s.source || s.path || "", i)}
                    className="mt-2 rounded border border-gray-600 bg-gray-800 px-2 py-1 text-xs text-gray-300 hover:bg-gray-700"
                  >
                    {expandedSourceIdx === i && expandedFile ? "Collapse" : "View full file"}
                  </button>
                )}
                {expandedSourceIdx === i && expandedFile && (
                  <div className="mt-3 rounded border border-gray-700 bg-gray-950 p-3">
                    <div className="mb-1 text-xs text-gray-400">
                      {expandedFile.path} ({expandedFile.line_count} lines)
                    </div>
                    <SyntaxHighlighter
                      language="cobol"
                      style={vscDarkPlus}
                      customStyle={{ borderRadius: "6px", fontSize: "12px", maxHeight: "300px" }}
                      PreTag="div"
                      showLineNumbers
                    >
                      {expandedFile.content}
                    </SyntaxHighlighter>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
        </div>
      </main>

      {/* File modal */}
      {fileModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="flex max-h-[90vh] w-full max-w-4xl flex-col rounded-lg border border-gray-700 bg-gray-900 shadow-xl">
            <div className="flex items-center justify-between border-b border-gray-700 px-4 py-3">
              <h3 className="truncate font-medium text-gray-200">
                {fileModal.path} ({fileModal.line_count} lines)
              </h3>
              <button
                onClick={() => setFileModal(null)}
                className="rounded p-1 text-gray-400 hover:bg-gray-800 hover:text-white"
              >
                ✕
              </button>
            </div>
            <div className="overflow-auto p-4">
              <SyntaxHighlighter
                language="cobol"
                style={vscDarkPlus}
                customStyle={{ borderRadius: "8px", fontSize: "13px" }}
                PreTag="div"
                showLineNumbers
              >
                {fileModal.content}
              </SyntaxHighlighter>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
