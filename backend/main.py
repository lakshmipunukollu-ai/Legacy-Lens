"""
LegacyLens Query API
FastAPI server with RAG endpoint for COBOL codebase queries.
"""

import json
import os
import re
import time
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_pinecone import PineconeVectorStore
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from tiktoken import encoding_for_model

app = FastAPI(title="LegacyLens API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load codebase stats at startup
STATS_FILE = Path(__file__).parent / "codebase_stats.json"
try:
    with open(STATS_FILE) as f:
        CODEBASE_STATS = json.load(f)
    print(f"Loaded codebase stats: {CODEBASE_STATS['total_files']} files, {CODEBASE_STATS['total_loc']:,} LOC")
except Exception:
    CODEBASE_STATS = {
        "total_files": 433,
        "total_loc": 354916,
        "top_files": [],
        "patterns_summary": [],
        "health_score": 72,
        "health_notes": ["Stats file not found — using fallback values"],
        "languages": [{"name": "COBOL", "files": 433, "percentage": 100}],
    }

# RAG accuracy constants
SNIPPET_MAX_CHARS = 80
CONTEXT_MAX_TOKENS = 1500
TOP_K = 2
TOP_K_BROAD = 8  # for summary/overview queries
TOP_K_DEPS = 3  # for dependencies (reduced for latency)
MAX_TOKENS = 150  # reduced for latency while keeping TOP_K=2

BROAD_QUERY_KEYWORDS = ("summary", "overview", "summarize", "describe the codebase", "what does this program do", "high level")

# Short system prompts (under 100 words each)
MARKDOWN_FORMAT = " Format your response using markdown. Use bold for important terms, bullet points for lists, and ### headers for sections."
SYSTEM_PROMPT_QUERY = """COBOL expert. Answer ONLY from provided context. Cite file names and line numbers. If the context contains OPEN, READ, WRITE, CLOSE, FAIL-ROUTINE, BAIL-OUT, or similar—that IS the answer; present it directly. Only say "I couldn't find" when the chunks are truly irrelevant (e.g., no file ops when asked about I/O). When context is relevant, answer confidently with specifics. Keep responses under 4 sentences. If the exact item is not found, describe the most relevant related code you did find and explain why the specific item may not be in the retrieved context.""" + MARKDOWN_FORMAT
SYSTEM_PROMPT_DEPS = """COBOL expert. Extract PERFORM call relationships. Return JSON array: [{{"caller":"X","callee":"Y","file":"...","line":N}}]. Use only provided code. If none: []."""
SYSTEM_PROMPT_DOC = """You are a COBOL expert. Write technical documentation for the provided code in 3 sentences maximum. Include: what it does, what data it uses, and what calls it.""" + MARKDOWN_FORMAT
SYSTEM_PROMPT_BUSINESS_LOGIC = """You are a COBOL expert. Analyze the code and respond in exactly this format with no extra text:
Business Rule: [one sentence]
Details: [one sentence]
Data Involved: [comma separated fields]
Business Impact: [one sentence]""" + MARKDOWN_FORMAT

SYSTEM_PROMPT_EXPLAIN_SNIPPET = """You are an expert COBOL developer. The user will paste raw COBOL code. Explain it in plain English using this exact format:

What it does: [1-2 sentences describing the overall purpose]
Step by step: [numbered list of what each section does]
Data involved: [bullet list of key variables and data structures]
Business meaning: [1 sentence on the real-world business purpose]
Potential issues: [bullet list of any risks, gotchas, or legacy concerns]""" + MARKDOWN_FORMAT


class QueryRequest(BaseModel):
    question: str
    session_id: str = "default"
    history: list = []  # Frontend sends last 3 exchanges


class SourceItem(BaseModel):
    file: str
    path: str = ""  # full path for /file drill-down (alias: source)
    paragraph: str
    start_line: int
    end_line: int
    snippet: str
    score: float  # 0-100 relevance percentage
    source: str = ""  # full path for /file drill-down (kept for backward compat)


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceItem]
    latency_ms: int


def _truncate_context_to_tokens(text: str, max_tokens: int = CONTEXT_MAX_TOKENS) -> str:
    """Truncate text to fit within token limit."""
    enc = encoding_for_model("gpt-4")
    tokens = enc.encode(text)
    if len(tokens) <= max_tokens:
        return text
    return enc.decode(tokens[:max_tokens])


def _build_context(docs: list, snippet_max_chars: int = SNIPPET_MAX_CHARS, max_tokens: int = CONTEXT_MAX_TOKENS) -> str:
    """Build context from docs with truncated snippets, then enforce token limit."""
    parts = []
    for d in docs:
        snippet = (d.page_content[:snippet_max_chars] + "...") if len(d.page_content) > snippet_max_chars else d.page_content
        part = f"File: {d.metadata.get('file_name', 'unknown')}\nParagraph: {d.metadata.get('paragraph', '')}\nLines {d.metadata.get('start_line', '')}-{d.metadata.get('end_line', '')}\n\n{snippet}"
        parts.append(part)
    full = "\n\n---\n\n".join(parts)
    return _truncate_context_to_tokens(full, max_tokens)


def _get_pinecone_index():
    """Get raw Pinecone index for stats. Returns (index, index_name) or (None, None)."""
    index_host = os.getenv("PINECONE_INDEX_HOST", "").strip()
    index_name = os.getenv("PINECONE_INDEX_NAME", "legacylens")
    if index_host:
        from pinecone import Pinecone
        api_key = os.getenv("PINECONE_API_KEY", "").strip()
        if not api_key:
            return None, index_name
        pc = Pinecone(api_key=api_key)
        index = pc.Index(host=index_host)
        return index, index_name
    return None, index_name


def get_vectorstore():
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        dimensions=1024,
    )
    index_host = os.getenv("PINECONE_INDEX_HOST", "").strip()
    if index_host:
        from pinecone import Pinecone
        api_key = os.getenv("PINECONE_API_KEY", "").strip()
        pc = Pinecone(api_key=api_key)
        index = pc.Index(host=index_host)
        return PineconeVectorStore(index=index, embedding=embeddings)
    index_name = os.getenv("PINECONE_INDEX_NAME", "legacylens")
    return PineconeVectorStore.from_existing_index(index_name, embeddings)


def _distance_to_score(distance: float) -> float:
    """Convert cosine distance to 0-100 similarity percentage."""
    score_pct = round((1 - distance) * 100, 1)
    return max(0.0, min(100.0, score_pct))


ENTRY_POINT_KEYWORDS = ("main entry", "entry point", "start", "begin", "program start")
ENTRY_POINT_APPEND = """ Entry point means where execution STARTS (PROGRAM-ID in IDENTIFICATION DIVISION, or first paragraph of PROCEDURE DIVISION). STOP RUN is an EXIT point (where execution ends)—never treat it as an entry point. Answer only from chunks that show PROGRAM-ID, IDENTIFICATION DIVISION, or PROCEDURE DIVISION. Keep your answer under 3 sentences."""
ENTRY_POINT_SEARCH_BOOST = " PROGRAM-ID IDENTIFICATION DIVISION PROCEDURE DIVISION"

FILE_IO_KEYWORDS = ("file i/o", "file io", "open read write", "file operations", "i/o operations")
FILE_IO_SEARCH_BOOST = " OPEN READ WRITE CLOSE INPUT OUTPUT"

ERROR_HANDLING_KEYWORDS = ("error handling", "error patterns", "fail routine", "bail-out")
ERROR_HANDLING_SEARCH_BOOST = " FAIL-ROUTINE BAIL-OUT ERROR EXCEPTION"


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    start_time = time.time()
    q_lower = request.question.lower()
    is_entry_point_query = any(kw in q_lower for kw in ENTRY_POINT_KEYWORDS)
    is_broad_query = any(kw in q_lower for kw in BROAD_QUERY_KEYWORDS)
    broad_append = " Synthesize a concise summary from the provided chunks. Cite key files and paragraphs." if is_broad_query else ""
    file_io_append = " List findings as brief bullet points only. Maximum 5 bullets." if ("file i/o" in q_lower or "file io" in q_lower or "operations" in q_lower or "error handling patterns" in q_lower) else ""
    system_prompt = SYSTEM_PROMPT_QUERY + (ENTRY_POINT_APPEND if is_entry_point_query else "") + broad_append + file_io_append

    vectorstore = get_vectorstore()
    k = TOP_K_BROAD if is_broad_query else TOP_K
    search_query = request.question
    if is_entry_point_query:
        search_query += ENTRY_POINT_SEARCH_BOOST
    elif any(kw in q_lower for kw in FILE_IO_KEYWORDS):
        search_query += FILE_IO_SEARCH_BOOST
    elif any(kw in q_lower for kw in ERROR_HANDLING_KEYWORDS):
        search_query += ERROR_HANDLING_SEARCH_BOOST
    doc_scores = vectorstore.similarity_search_with_score(search_query, k=k)

    if not doc_scores:
        latency_ms = round((time.time() - start_time) * 1000)
        return QueryResponse(
            answer="No relevant code found for your question. Try rephrasing or asking about a specific file or paragraph.",
            sources=[],
            latency_ms=latency_ms,
        )

    docs = [d for d, _ in doc_scores]
    scores = [_distance_to_score(s) for _, s in doc_scores]
    context = _build_context(docs)

    # Build messages from history sent by frontend (last 3 exchanges = 6 messages)
    messages = [("system", system_prompt)]
    for h in (request.history or [])[-6:]:
        role = "human" if h.get("role") == "user" else "ai"
        content = h.get("content", "")
        if content:
            messages.append((role, content))
    messages.append(("human", "Context:\n{context}\n\nQuestion: {question}"))

    prompt = ChatPromptTemplate.from_messages(messages)

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=MAX_TOKENS)
    chain = prompt | llm | StrOutputParser()
    answer = chain.invoke({"context": context, "question": request.question})

    sources = [
        SourceItem(
            file=d.metadata.get("file_name", "unknown"),
            path=d.metadata.get("source", ""),
            paragraph=d.metadata.get("paragraph", ""),
            start_line=d.metadata.get("start_line", 0),
            end_line=d.metadata.get("end_line", 0),
            snippet=d.page_content[:SNIPPET_MAX_CHARS] + ("..." if len(d.page_content) > SNIPPET_MAX_CHARS else ""),
            score=scores[i],
            source=d.metadata.get("source", ""),
        )
        for i, d in enumerate(docs)
    ]

    latency_ms = round((time.time() - start_time) * 1000)
    return QueryResponse(answer=answer, sources=sources, latency_ms=latency_ms)


class ExplainSnippetRequest(BaseModel):
    code: str


class ExplainSnippetResponse(BaseModel):
    explanation: str
    latency_ms: int


@app.post("/explain-snippet", response_model=ExplainSnippetResponse)
async def explain_snippet(request: ExplainSnippetRequest):
    """Explain raw COBOL code directly — no Pinecone, just GPT-4o-mini."""
    start_time = time.time()
    code = (request.code or "").strip()
    if not code:
        latency_ms = round((time.time() - start_time) * 1000)
        return ExplainSnippetResponse(
            explanation="Please paste some COBOL code to explain.",
            latency_ms=latency_ms,
        )
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT_EXPLAIN_SNIPPET),
        ("human", "COBOL code:\n\n{code}\n\nExplain in the required format:"),
    ])
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=300)
    chain = prompt | llm | StrOutputParser()
    explanation = chain.invoke({"code": code})
    latency_ms = round((time.time() - start_time) * 1000)
    return ExplainSnippetResponse(explanation=explanation, latency_ms=latency_ms)


class ClearHistoryRequest(BaseModel):
    session_id: str = "default"


@app.post("/clear-history")
async def clear_history(request: ClearHistoryRequest):
    """Clear conversation history. History is now client-side; this endpoint returns success for compatibility."""
    start_time = time.time()
    latency_ms = round((time.time() - start_time) * 1000)
    return {"status": "cleared", "session_id": request.session_id, "latency_ms": latency_ms}


@app.get("/health")
async def health():
    start = time.time()
    return {"status": "ok", "latency_ms": round((time.time() - start) * 1000)}


@app.get("/stats")
async def stats():
    """Return Pinecone index stats: total chunk count."""
    start_time = time.time()
    index, index_name = _get_pinecone_index()
    if index is None:
        latency_ms = round((time.time() - start_time) * 1000)
        return {"total_chunks": 0, "index_name": index_name, "status": "ok", "message": "Pinecone not configured (PINECONE_INDEX_HOST required)", "latency_ms": latency_ms}
    try:
        s = index.describe_index_stats()
        total = s.get("total_vector_count", 0)
        latency_ms = round((time.time() - start_time) * 1000)
        return {"total_chunks": total, "index_name": index_name, "status": "ok", "latency_ms": latency_ms}
    except Exception as e:
        latency_ms = round((time.time() - start_time) * 1000)
        return {"total_chunks": 0, "index_name": index_name, "status": "error", "message": str(e), "latency_ms": latency_ms}


# --- Full file drill-down ---
CODEBASE_DIR = Path(__file__).resolve().parent.parent / "codebase"
COBOL_EXTENSIONS = {".cob", ".cbl", ".cpy", ".COB", ".CBL", ".CPY"}


def _build_file_tree(root: Path, base: Path) -> list:
    """Build nested tree of directories and COBOL files only. Sorted alphabetically."""
    items = []
    try:
        entries = sorted(root.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except OSError:
        return items
    for item in entries:
        if item.name.startswith("."):
            continue
        rel = item.relative_to(base)
        rel_str = str(rel).replace("\\", "/")
        if item.is_dir():
            children = _build_file_tree(item, base)
            if children:
                items.append({
                    "name": item.name,
                    "type": "directory",
                    "children": children,
                })
        elif item.is_file() and item.suffix in COBOL_EXTENSIONS:
            try:
                lines = len(item.read_text(encoding="utf-8", errors="replace").splitlines())
            except Exception:
                lines = 0
            items.append({
                "name": item.name,
                "type": "file",
                "path": rel_str,
                "lines": lines,
            })
    return items


def _compute_codebase_stats():
    """Compute file stats from codebase when available. Returns (total_files, total_loc, top_files, patterns_summary)."""
    if not CODEBASE_DIR.exists() or not CODEBASE_DIR.is_dir():
        return 0, 0, [], []

    file_stats = []
    total_loc = 0
    pattern_counts = {"File I/O Operations": 0, "Error Handling": 0, "PERFORM Statements": 0, "Data Division": 0, "MOVE Statements": 0}

    for path in CODEBASE_DIR.rglob("*"):
        if not path.is_file() or path.suffix not in COBOL_EXTENSIONS:
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines()
            loc = len(lines)
            total_loc += loc
            rel = path.relative_to(CODEBASE_DIR)
            file_stats.append({"file": path.name, "path": str(rel).replace("\\", "/"), "loc": loc})
            content_upper = content.upper()
            if "OPEN " in content_upper or "READ " in content_upper or "WRITE " in content_upper:
                pattern_counts["File I/O Operations"] += 1
            if "FAIL" in content_upper or "ERROR" in content_upper or "EXCEPTION" in content_upper:
                pattern_counts["Error Handling"] += 1
            pattern_counts["PERFORM Statements"] += content_upper.count("PERFORM ")
            if "DATA DIVISION" in content_upper:
                pattern_counts["Data Division"] += 1
            pattern_counts["MOVE Statements"] += content_upper.count(" MOVE ")
        except Exception:
            continue

    top_files = sorted(file_stats, key=lambda x: x["loc"], reverse=True)[:5]
    for t in top_files:
        t["chunks"] = max(1, t["loc"] // 50)
    patterns_summary = [{"pattern": k, "count": v} for k, v in pattern_counts.items() if v > 0]
    patterns_summary.sort(key=lambda x: x["count"], reverse=True)
    return len(file_stats), total_loc, top_files, patterns_summary


@app.get("/health-dashboard")
async def health_dashboard():
    """Return stats about the indexed codebase for the health dashboard."""
    start_time = time.time()
    total_chunks = 0

    index, index_name = _get_pinecone_index()
    if index is not None:
        try:
            stats = index.describe_index_stats()
            total_chunks = stats.get("total_vector_count", 0)
        except Exception:
            pass

    latency_ms = round((time.time() - start_time) * 1000)
    return {
        "total_chunks": total_chunks,
        "total_files": CODEBASE_STATS["total_files"],
        "total_loc": CODEBASE_STATS["total_loc"],
        "top_files": CODEBASE_STATS.get("top_files", [])[:5],
        "languages": CODEBASE_STATS.get("languages", [{"name": "COBOL", "files": CODEBASE_STATS["total_files"], "percentage": 100}]),
        "patterns_summary": CODEBASE_STATS.get("patterns_summary", [])[:5],
        "health_score": CODEBASE_STATS.get("health_score", 72),
        "health_notes": CODEBASE_STATS.get("health_notes", []),
        "computed_at": CODEBASE_STATS.get("computed_at", "unknown"),
        "latency_ms": latency_ms,
    }


@app.get("/files")
async def list_files():
    """Return nested file tree of COBOL files in codebase/. Grouped by top-level directory."""
    if not CODEBASE_DIR.exists() or not CODEBASE_DIR.is_dir():
        return {"tree": [], "total_files": 0, "error": "Codebase not available in production"}

    tree = _build_file_tree(CODEBASE_DIR, CODEBASE_DIR)

    def count_files(items: list) -> int:
        n = 0
        for x in items:
            if x.get("type") == "file":
                n += 1
            else:
                n += count_files(x.get("children", []))
        return n

    total_files = count_files(tree)
    return {"tree": tree, "total_files": total_files}


@app.get("/file")
async def get_file(path: str = ""):
    """Return full file content for drill-down. path is relative to codebase/."""
    if not path or ".." in path or path.startswith("/"):
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=400,
            content={"detail": "Invalid path. Use relative path within codebase."},
        )
    full_path = (CODEBASE_DIR / path).resolve()
    if not str(full_path).startswith(str(CODEBASE_DIR.resolve())):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=403, content={"detail": "Path traversal not allowed."})
    if not full_path.exists() or not full_path.is_file():
        return {
            "error": "Full file view is available in local development only. The codebase is not bundled with the production deployment."
        }
    try:
        content = full_path.read_text(encoding="utf-8", errors="replace")
        line_count = len(content.splitlines())
        return {"path": path, "content": content, "line_count": line_count}
    except Exception as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=500,
            content={"detail": f"Could not read file: {e}"},
        )


# --- Phase 7: Code Understanding Features ---

class DependenciesResponse(BaseModel):
    answer: str
    call_graph: list[dict]  # [{ "caller": "PARA-A", "callee": "PARA-B", "file": "...", "line": N }]
    graph: dict  # { "nodes": [...], "edges": [...] }
    sources: list[SourceItem]
    latency_ms: int


@app.post("/dependencies", response_model=DependenciesResponse)
async def dependencies(request: QueryRequest):
    """Retrieve chunks containing PERFORM statements and return a call-graph style summary."""
    start_time = time.time()
    vectorstore = get_vectorstore()
    doc_scores = vectorstore.similarity_search_with_score(
        "PERFORM statement calling paragraph or section " + (request.question or "dependencies"),
        k=TOP_K_DEPS,
    )
    if not doc_scores:
        latency_ms = round((time.time() - start_time) * 1000)
        return DependenciesResponse(
            answer="No PERFORM/call patterns found.",
            call_graph=[],
            graph={"nodes": [], "edges": []},
            sources=[],
            latency_ms=latency_ms,
        )

    docs = [d for d, _ in doc_scores]
    scores = [_distance_to_score(s) for _, s in doc_scores]
    context = _build_context(docs)

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT_DEPS),
        ("human", "Code:\n{context}\n\nQuestion or module: {question}\n\nJSON array of call graph items:"),
    ])
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=150)
    chain = prompt | llm | StrOutputParser()
    raw = chain.invoke({"context": context, "question": request.question or "all PERFORM calls"})
    # Parse JSON from response (may be wrapped in markdown)
    call_graph = []
    try:
        if "[" in raw:
            start = raw.index("[")
            end = raw.rindex("]") + 1
            call_graph = json.loads(raw[start:end])
    except Exception:
        pass

    # Fallback: parse raw text for "X calls Y" or "X performs Y" when call_graph is empty
    if not call_graph:
        for m in re.finditer(
            r"(\w+(?:-\w+)*)\s+(?:calls|performs)\s+(\w+(?:-\w+)*)",
            raw,
            re.IGNORECASE,
        ):
            caller, callee = m.group(1).strip(), m.group(2).strip()
            if caller and callee and caller != callee:
                call_graph.append({"caller": caller, "callee": callee, "file": "unknown", "line": 0})

    nodes_by_id: dict[str, dict] = {}
    edges: list[dict] = []
    for item in call_graph:
        if not isinstance(item, dict):
            continue
        caller = str(item.get("caller", "")).strip()
        callee = str(item.get("callee", "")).strip()
        file_name = str(item.get("file", "unknown"))
        if not caller or not callee:
            continue
        if caller not in nodes_by_id:
            nodes_by_id[caller] = {"id": caller, "type": "paragraph", "file": file_name}
        if callee not in nodes_by_id:
            nodes_by_id[callee] = {"id": callee, "type": "paragraph", "file": file_name}
        edges.append({"source": caller, "target": callee, "type": "calls"})

    # Add nodes from doc metadata when we have docs but no nodes yet (so graph shows retrieved paragraphs)
    if not nodes_by_id and docs:
        for d in docs:
            para = (d.metadata.get("paragraph") or "").strip()
            if para:
                fname = d.metadata.get("file_name", "unknown")
                nodes_by_id[para] = {"id": para, "type": "paragraph", "file": fname}

    graph = {"nodes": list(nodes_by_id.values()), "edges": edges}

    answer = f"Found {len(docs)} chunk(s) related to PERFORM/calls. Extracted {len(call_graph)} call relationship(s)."
    sources = [
        SourceItem(
            file=d.metadata.get("file_name", "unknown"),
            path=d.metadata.get("source", ""),
            paragraph=d.metadata.get("paragraph", ""),
            start_line=d.metadata.get("start_line", 0),
            end_line=d.metadata.get("end_line", 0),
            snippet=d.page_content[:SNIPPET_MAX_CHARS] + ("..." if len(d.page_content) > SNIPPET_MAX_CHARS else ""),
            score=scores[i],
            source=d.metadata.get("source", ""),
        )
        for i, d in enumerate(docs)
    ]
    latency_ms = round((time.time() - start_time) * 1000)
    return DependenciesResponse(
        answer=answer,
        call_graph=call_graph,
        graph=graph,
        sources=sources,
        latency_ms=latency_ms,
    )


class DocumentRequest(BaseModel):
    paragraph: str | None = None
    file_name: str | None = None


class DocumentResponse(BaseModel):
    documentation: str
    sources: list[SourceItem]
    latency_ms: int


@app.post("/document", response_model=DocumentResponse)
async def generate_documentation(body: DocumentRequest):
    """Retrieve paragraph or file code and generate technical documentation."""
    start_time = time.time()
    vectorstore = get_vectorstore()
    query = body.paragraph or body.file_name or "main program entry procedure division"
    doc_scores = vectorstore.similarity_search_with_score(query, k=TOP_K)
    if not doc_scores:
        latency_ms = round((time.time() - start_time) * 1000)
        return DocumentResponse(
            documentation="No matching code found to document.",
            sources=[],
            latency_ms=latency_ms,
        )
    docs = [d for d, _ in doc_scores]
    scores = [_distance_to_score(s) for _, s in doc_scores]
    context = _build_context(docs)
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT_DOC),
        ("human", "Code:\n{context}\n\nWrite technical documentation:"),
    ])
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=100)
    chain = prompt | llm | StrOutputParser()
    documentation = chain.invoke({"context": context})
    sources = [
        SourceItem(
            file=d.metadata.get("file_name", "unknown"),
            path=d.metadata.get("source", ""),
            paragraph=d.metadata.get("paragraph", ""),
            start_line=d.metadata.get("start_line", 0),
            end_line=d.metadata.get("end_line", 0),
            snippet=d.page_content[:SNIPPET_MAX_CHARS] + ("..." if len(d.page_content) > SNIPPET_MAX_CHARS else ""),
            score=scores[i],
            source=d.metadata.get("source", ""),
        )
        for i, d in enumerate(docs)
    ]
    latency_ms = round((time.time() - start_time) * 1000)
    return DocumentResponse(documentation=documentation, sources=sources, latency_ms=latency_ms)


class PatternRequest(BaseModel):
    keyword: str = "OPEN READ WRITE"  # file I/O by default


class PatternResponse(BaseModel):
    answer: str
    sources: list[SourceItem]
    latency_ms: int


@app.post("/patterns", response_model=PatternResponse)
async def pattern_detection(body: PatternRequest):
    """Search for keywords (e.g. OPEN, READ, WRITE) to find file I/O or other patterns."""
    start_time = time.time()
    vectorstore = get_vectorstore()
    doc_scores = vectorstore.similarity_search_with_score(
        f"COBOL code containing {body.keyword} file operations or similar",
        k=TOP_K,
    )
    if not doc_scores:
        latency_ms = round((time.time() - start_time) * 1000)
        return PatternResponse(
            answer=f"No chunks found matching pattern: {body.keyword}",
            sources=[],
            latency_ms=latency_ms,
        )
    docs = [d for d, _ in doc_scores]
    scores = [_distance_to_score(s) for _, s in doc_scores]
    sources = [
        SourceItem(
            file=d.metadata.get("file_name", "unknown"),
            path=d.metadata.get("source", ""),
            paragraph=d.metadata.get("paragraph", ""),
            start_line=d.metadata.get("start_line", 0),
            end_line=d.metadata.get("end_line", 0),
            snippet=d.page_content[:SNIPPET_MAX_CHARS] + ("..." if len(d.page_content) > SNIPPET_MAX_CHARS else ""),
            score=scores[i],
            source=d.metadata.get("source", ""),
        )
        for i, d in enumerate(docs)
    ]
    answer = f"Found {len(docs)} chunk(s) matching pattern '{body.keyword}' (file I/O and related operations)."
    latency_ms = round((time.time() - start_time) * 1000)
    return PatternResponse(answer=answer, sources=sources, latency_ms=latency_ms)


class BusinessLogicResponse(BaseModel):
    business_logic: str
    sources: list[SourceItem]
    latency_ms: int


@app.post("/business-logic", response_model=BusinessLogicResponse)
async def business_logic(request: QueryRequest):
    """Extract business rules from COBOL code using similarity search and GPT-4o-mini."""
    start_time = time.time()
    vectorstore = get_vectorstore()
    doc_scores = vectorstore.similarity_search_with_score(request.question, k=TOP_K)

    if not doc_scores:
        latency_ms = round((time.time() - start_time) * 1000)
        return BusinessLogicResponse(
            business_logic="No relevant code found for your question. Try rephrasing or asking about a specific section.",
            sources=[],
            latency_ms=latency_ms,
        )

    docs = [d for d, _ in doc_scores]
    scores = [_distance_to_score(s) for _, s in doc_scores]
    context = _build_context(docs)

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT_BUSINESS_LOGIC),
        ("human", "COBOL code:\n{context}\n\nExtract business rules:"),
    ])
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=80)
    chain = prompt | llm | StrOutputParser()
    business_logic_text = chain.invoke({"context": context})

    sources = [
        SourceItem(
            file=d.metadata.get("file_name", "unknown"),
            path=d.metadata.get("source", ""),
            paragraph=d.metadata.get("paragraph", ""),
            start_line=d.metadata.get("start_line", 0),
            end_line=d.metadata.get("end_line", 0),
            snippet=d.page_content[:SNIPPET_MAX_CHARS] + ("..." if len(d.page_content) > SNIPPET_MAX_CHARS else ""),
            score=scores[i],
            source=d.metadata.get("source", ""),
        )
        for i, d in enumerate(docs)
    ]

    latency_ms = round((time.time() - start_time) * 1000)
    return BusinessLogicResponse(
        business_logic=business_logic_text,
        sources=sources,
        latency_ms=latency_ms,
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
