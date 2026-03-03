"""
LegacyLens Query API
FastAPI server with RAG endpoint for COBOL codebase queries.
"""

import json
import os
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

# Latency optimization constants
SNIPPET_MAX_CHARS = 100
CONTEXT_MAX_TOKENS = 2000
TOP_K = 1
MAX_TOKENS = 300

# Short system prompts (under 100 words each)
SYSTEM_PROMPT_QUERY = """COBOL expert. Answer ONLY from provided context. Cite file names and line numbers. If the asked identifier is not in context, say "I couldn't find [identifier] in the indexed codebase. Here is what I found that may be related:" then summarize the closest chunks. If the requested identifier, paragraph, or function does not exist in the retrieved context, respond in exactly 2 sentences maximum: one sentence saying it was not found, and one sentence describing the closest related code you did find. Never write more than 2 sentences for a not-found response."""
SYSTEM_PROMPT_DEPS = """COBOL expert. Extract PERFORM call relationships. Return JSON array: [{{"caller":"X","callee":"Y","file":"...","line":N}}]. Use only provided code. If none: []."""
SYSTEM_PROMPT_DOC = """Technical writer. Write concise docs for this COBOL code: purpose, inputs/outputs, key logic. Use only provided code."""
SYSTEM_PROMPT_BUSINESS_LOGIC = """You are an expert at analyzing legacy COBOL code and extracting business rules. Given the following COBOL code, identify and explain the business rules in plain English. Format your response exactly like this:
Business Rule: [one sentence summary]
Details: [2-3 sentences explaining what the code does]
Data Involved: [list the key data fields mentioned]
Business Impact: [one sentence on what breaks if this code fails]"""


class QueryRequest(BaseModel):
    question: str


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
ENTRY_POINT_APPEND = " Focus your answer on IDENTIFICATION DIVISION, PROGRAM-ID, and PROCEDURE DIVISION entries. Keep your answer under 3 sentences."


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    start_time = time.time()
    q_lower = request.question.lower()
    is_entry_point_query = any(kw in q_lower for kw in ENTRY_POINT_KEYWORDS)
    system_prompt = SYSTEM_PROMPT_QUERY + (ENTRY_POINT_APPEND if is_entry_point_query else "")

    vectorstore = get_vectorstore()
    doc_scores = vectorstore.similarity_search_with_score(request.question, k=TOP_K)

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

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Context:\n{context}\n\nQuestion: {question}"),
    ])

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


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/stats")
async def stats():
    """Return Pinecone index stats: total chunk count."""
    index, index_name = _get_pinecone_index()
    if index is None:
        return {"total_chunks": 0, "index_name": index_name, "status": "ok", "message": "Pinecone not configured (PINECONE_INDEX_HOST required)"}
    try:
        stats = index.describe_index_stats()
        total = stats.get("total_vector_count", 0)
        return {"total_chunks": total, "index_name": index_name, "status": "ok"}
    except Exception as e:
        return {"total_chunks": 0, "index_name": index_name, "status": "error", "message": str(e)}


# --- Full file drill-down ---
CODEBASE_DIR = Path(__file__).resolve().parent.parent / "codebase"


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
    sources: list[SourceItem]
    latency_ms: int


@app.post("/dependencies", response_model=DependenciesResponse)
async def dependencies(request: QueryRequest):
    """Retrieve chunks containing PERFORM statements and return a call-graph style summary."""
    start_time = time.time()
    vectorstore = get_vectorstore()
    doc_scores = vectorstore.similarity_search_with_score(
        "PERFORM statement calling paragraph or section " + (request.question or "dependencies"),
        k=TOP_K,
    )
    if not doc_scores:
        latency_ms = round((time.time() - start_time) * 1000)
        return DependenciesResponse(answer="No PERFORM/call patterns found.", call_graph=[], sources=[], latency_ms=latency_ms)

    docs = [d for d, _ in doc_scores]
    scores = [_distance_to_score(s) for _, s in doc_scores]
    context = _build_context(docs)

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT_DEPS),
        ("human", "Code:\n{context}\n\nQuestion or module: {question}\n\nJSON array of call graph items:"),
    ])
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=MAX_TOKENS)
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
    return DependenciesResponse(answer=answer, call_graph=call_graph, sources=sources, latency_ms=latency_ms)


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
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=MAX_TOKENS)
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
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=MAX_TOKENS)
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
