"""
LegacyLens Query API
FastAPI server with RAG endpoint for COBOL codebase queries.
"""

import json
import os
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

app = FastAPI(title="LegacyLens API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    question: str


class SourceItem(BaseModel):
    file: str
    paragraph: str
    start_line: int
    end_line: int
    snippet: str


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceItem]


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


SYSTEM_PROMPT = """You are an expert assistant helping developers understand a legacy COBOL codebase.
Answer based ONLY on the provided code context.
Always cite file names and line numbers when referencing code."""


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    vectorstore = get_vectorstore()

    # Retrieve top-5 matching chunks
    docs = vectorstore.similarity_search(request.question, k=5)

    if not docs:
        return QueryResponse(
            answer="No relevant code found for your question. Try rephrasing or asking about a specific file or paragraph.",
            sources=[],
        )

    context = "\n\n---\n\n".join(
        f"File: {d.metadata.get('file_name', 'unknown')}\n"
        f"Paragraph: {d.metadata.get('paragraph', '')}\n"
        f"Lines {d.metadata.get('start_line', '')}-{d.metadata.get('end_line', '')}\n\n"
        f"{d.page_content}"
        for d in docs
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "Context:\n{context}\n\nQuestion: {question}"),
    ])

    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    chain = prompt | llm | StrOutputParser()
    answer = chain.invoke({"context": context, "question": request.question})

    sources = [
        SourceItem(
            file=d.metadata.get("file_name", "unknown"),
            paragraph=d.metadata.get("paragraph", ""),
            start_line=d.metadata.get("start_line", 0),
            end_line=d.metadata.get("end_line", 0),
            snippet=d.page_content[:500] + ("..." if len(d.page_content) > 500 else ""),
        )
        for d in docs
    ]

    return QueryResponse(answer=answer, sources=sources)


@app.get("/health")
async def health():
    return {"status": "ok"}


# --- Phase 7: Code Understanding Features ---

class DependenciesResponse(BaseModel):
    answer: str
    call_graph: list[dict]  # [{ "caller": "PARA-A", "callee": "PARA-B", "file": "...", "line": N }]
    sources: list[SourceItem]


@app.post("/dependencies", response_model=DependenciesResponse)
async def dependencies(request: QueryRequest):
    """Retrieve chunks containing PERFORM statements and return a call-graph style summary."""
    vectorstore = get_vectorstore()
    docs = vectorstore.similarity_search(
        "PERFORM statement calling paragraph or section " + (request.question or "dependencies"),
        k=10,
    )
    if not docs:
        return DependenciesResponse(answer="No PERFORM/call patterns found.", call_graph=[], sources=[])

    context = "\n\n---\n\n".join(
        f"File: {d.metadata.get('file_name', '')} Lines {d.metadata.get('start_line', '')}-{d.metadata.get('end_line', '')}\n{d.page_content}"
        for d in docs
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a COBOL expert. Extract PERFORM-style call relationships. Return a JSON array of objects with keys: caller (paragraph/section name), callee (paragraph name being performed), file, line. Use only the provided code. If none found return []."),
        ("human", "Code:\n{context}\n\nQuestion or module: {question}\n\nJSON array of call graph items:"),
    ])
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
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
            paragraph=d.metadata.get("paragraph", ""),
            start_line=d.metadata.get("start_line", 0),
            end_line=d.metadata.get("end_line", 0),
            snippet=d.page_content[:500] + ("..." if len(d.page_content) > 500 else ""),
        )
        for d in docs
    ]
    return DependenciesResponse(answer=answer, call_graph=call_graph, sources=sources)


class DocumentRequest(BaseModel):
    paragraph: str | None = None
    file_name: str | None = None


class DocumentResponse(BaseModel):
    documentation: str
    sources: list[SourceItem]


@app.post("/document", response_model=DocumentResponse)
async def generate_documentation(body: DocumentRequest):
    """Retrieve paragraph or file code and generate technical documentation."""
    vectorstore = get_vectorstore()
    query = body.paragraph or body.file_name or "main program entry procedure division"
    docs = vectorstore.similarity_search(query, k=5)
    if not docs:
        return DocumentResponse(
            documentation="No matching code found to document.",
            sources=[],
        )
    context = "\n\n---\n\n".join(
        f"File: {d.metadata.get('file_name', '')} Paragraph: {d.metadata.get('paragraph', '')} Lines {d.metadata.get('start_line', '')}-{d.metadata.get('end_line', '')}\n{d.page_content}"
        for d in docs
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a technical writer. Write clear, concise technical documentation for the following COBOL code. Include purpose, inputs/outputs, and key logic. Use only the provided code."),
        ("human", "Code:\n{context}\n\nWrite technical documentation:"),
    ])
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    chain = prompt | llm | StrOutputParser()
    documentation = chain.invoke({"context": context})
    sources = [
        SourceItem(
            file=d.metadata.get("file_name", "unknown"),
            paragraph=d.metadata.get("paragraph", ""),
            start_line=d.metadata.get("start_line", 0),
            end_line=d.metadata.get("end_line", 0),
            snippet=d.page_content[:500] + ("..." if len(d.page_content) > 500 else ""),
        )
        for d in docs
    ]
    return DocumentResponse(documentation=documentation, sources=sources)


class PatternRequest(BaseModel):
    keyword: str = "OPEN READ WRITE"  # file I/O by default


class PatternResponse(BaseModel):
    answer: str
    sources: list[SourceItem]


@app.post("/patterns", response_model=PatternResponse)
async def pattern_detection(body: PatternRequest):
    """Search for keywords (e.g. OPEN, READ, WRITE) to find file I/O or other patterns."""
    vectorstore = get_vectorstore()
    docs = vectorstore.similarity_search(
        f"COBOL code containing {body.keyword} file operations or similar",
        k=10,
    )
    if not docs:
        return PatternResponse(
            answer=f"No chunks found matching pattern: {body.keyword}",
            sources=[],
        )
    sources = [
        SourceItem(
            file=d.metadata.get("file_name", "unknown"),
            paragraph=d.metadata.get("paragraph", ""),
            start_line=d.metadata.get("start_line", 0),
            end_line=d.metadata.get("end_line", 0),
            snippet=d.page_content[:500] + ("..." if len(d.page_content) > 500 else ""),
        )
        for d in docs
    ]
    answer = f"Found {len(docs)} chunk(s) matching pattern '{body.keyword}' (file I/O and related operations)."
    return PatternResponse(answer=answer, sources=sources)
