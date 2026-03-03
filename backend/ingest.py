"""
LegacyLens Ingestion Pipeline
Recursively finds COBOL files, chunks by paragraph boundaries, and uploads to Pinecone.
"""

import os
import re
import time
from pathlib import Path

# Load .env from this script's directory (backend/) so it works regardless of cwd
_script_dir = Path(__file__).resolve().parent
from dotenv import load_dotenv
load_dotenv(_script_dir / ".env")

# Ensure Pinecone key is set and stripped (avoids 401 from hidden whitespace/newlines)
_raw = os.environ.get("PINECONE_API_KEY")
if _raw:
    os.environ["PINECONE_API_KEY"] = _raw.strip()

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from tiktoken import encoding_for_model

# Paths
SCRIPT_DIR = _script_dir
PROJECT_ROOT = SCRIPT_DIR.parent
CODEBASE_DIR = PROJECT_ROOT / "codebase"

# COBOL paragraph/section pattern: line with word(s) ending in period (Area A/B)
# Matches: "PARAGRAPH-NAME." or "SECTION-NAME SECTION."
PARAGRAPH_PATTERN = re.compile(
    r"^\s{0,11}[A-Za-z0-9][A-Za-z0-9-]*(\s+SECTION)?\.\s*$",
    re.IGNORECASE
)

# Exclude comment lines (col 7 * or *>)
COMMENT_PATTERN = re.compile(r"^\s*\*|^\s*$")

# Extensions to include
COBOL_EXTENSIONS = {".cob", ".cbl", ".cpy", ".COB", ".CBL", ".CPY"}

# Chunking config
CHUNK_SIZE = 512
CHUNK_OVERLAP = 50


def find_cobol_files(root: Path) -> list[Path]:
    """Recursively find all COBOL files."""
    files = []
    for path in root.rglob("*"):
        if path.is_file() and path.suffix in COBOL_EXTENSIONS:
            files.append(path)
    return files


def read_file_utf8(path: Path) -> str:
    """Read file and normalize to UTF-8."""
    encodings = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]
    for enc in encodings:
        try:
            return path.read_text(encoding=enc)
        except Exception:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def is_paragraph_line(line: str) -> bool:
    """Check if line is a COBOL paragraph/section boundary."""
    if COMMENT_PATTERN.match(line):
        return False
    stripped = line.strip()
    if not stripped or len(stripped) < 2:
        return False
    # Must end with period, start with alphanumeric
    if not stripped.endswith("."):
        return False
    # Paragraph/section: word followed by optional " SECTION" and period
    return bool(PARAGRAPH_PATTERN.match(line))


def chunk_by_paragraphs(lines: list[str], file_name: str, source_path: str) -> list[dict]:
    """Split content by COBOL paragraph boundaries. Returns list of chunk dicts."""
    chunks = []
    current_paragraph = None
    current_lines = []
    start_line = 0

    for i, line in enumerate(lines, start=1):
        if is_paragraph_line(line):
            # Save previous chunk
            if current_paragraph and current_lines:
                text = "\n".join(current_lines)
                if text.strip():
                    chunks.append({
                        "text": text,
                        "file_name": file_name,
                        "source": source_path,
                        "paragraph": current_paragraph,
                        "start_line": start_line,
                        "end_line": i - 1,
                    })
            # Start new chunk
            current_paragraph = line.strip().rstrip(".")
            current_lines = [line]
            start_line = i
        else:
            current_lines.append(line)

    # Flush last chunk
    if current_paragraph and current_lines:
        text = "\n".join(current_lines)
        if text.strip():
            chunks.append({
                "text": text,
                "file_name": file_name,
                "source": source_path,
                "paragraph": current_paragraph,
                "start_line": start_line,
                "end_line": len(lines),
            })

    return chunks


def chunk_by_tokens(text: str, file_name: str, source_path: str, start_line: int = 1) -> list[dict]:
    """Fallback: fixed-size chunking by token count with overlap."""
    enc = encoding_for_model("gpt-4")
    tokens = enc.encode(text)
    chunks = []
    i = 0
    chunk_id = 0
    while i < len(tokens):
        chunk_tokens = tokens[i : i + CHUNK_SIZE]
        chunk_text = enc.decode(chunk_tokens)
        # Estimate line range (rough)
        line_count = chunk_text.count("\n") + 1
        end_line = start_line + line_count - 1
        chunks.append({
            "text": chunk_text,
            "file_name": file_name,
            "source": source_path,
            "paragraph": f"chunk_{chunk_id}",
            "start_line": start_line,
            "end_line": end_line,
        })
        start_line = end_line + 1
        i += CHUNK_SIZE - CHUNK_OVERLAP
        chunk_id += 1
    return chunks


def chunk_file(content: str, file_name: str, source_path: str) -> list[Document]:
    """Chunk file content. Primary: paragraphs. Fallback: token-based."""
    lines = content.splitlines()
    chunks = chunk_by_paragraphs(lines, file_name, source_path)

    if not chunks:
        # Fallback: fixed-size chunking
        chunks = chunk_by_tokens(content, file_name, source_path)

    docs = []
    for c in chunks:
        doc = Document(
            page_content=c["text"],
            metadata={
                "file_name": c["file_name"],
                "source": c["source"],
                "paragraph": c["paragraph"],
                "start_line": c["start_line"],
                "end_line": c["end_line"],
            },
        )
        docs.append(doc)
    return docs


def delete_all_vectors(index_host: str, api_key: str) -> None:
    """Delete all vectors from the Pinecone index before re-ingesting."""
    if not index_host or not api_key:
        print("Skipping delete (PINECONE_INDEX_HOST or PINECONE_API_KEY not set).")
        return
    from pinecone import Pinecone
    pc = Pinecone(api_key=api_key)
    index = pc.Index(host=index_host)
    # LangChain PineconeVectorStore uses empty string namespace by default
    index.delete(delete_all=True, namespace="")
    print("Deleted all existing vectors from Pinecone index.")


def main():
    start_time = time.time()

    if not CODEBASE_DIR.exists():
        print(f"Error: codebase not found at {CODEBASE_DIR}")
        print("Run: git clone repos into codebase/ (see README)")
        return

    files = find_cobol_files(CODEBASE_DIR)
    print(f"Found {len(files)} COBOL files")

    all_docs = []
    for path in files:
        try:
            content = read_file_utf8(path)
            rel_path = path.relative_to(CODEBASE_DIR)
            source_path = str(rel_path)
            file_name = path.name
            docs = chunk_file(content, file_name, source_path)
            all_docs.extend(docs)
        except Exception as e:
            print(f"  Skip {path}: {e}")

    print(f"Total chunks: {len(all_docs)}")

    if not all_docs:
        print("No documents to upload.")
        return

    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        dimensions=1024,
    )

    index_name = os.getenv("PINECONE_INDEX_NAME", "legacylens")
    index_host = os.getenv("PINECONE_INDEX_HOST", "").strip()
    api_key = os.environ.get("PINECONE_API_KEY", "").strip()

    # Delete all existing vectors before re-ingesting
    print("Deleting existing vectors from Pinecone...")
    try:
        delete_all_vectors(index_host, api_key)
    except Exception as e:
        print(f"Warning: Could not delete existing vectors: {e}")
        print("Proceeding with upload (may create duplicates).")

    # Upload to Pinecone
    print("Uploading to Pinecone...")
    if index_host:
        if not api_key:
            raise ValueError("PINECONE_API_KEY is required when using PINECONE_INDEX_HOST")
        from pinecone import Pinecone
        pc = Pinecone(api_key=api_key)
        index = pc.Index(host=index_host)
        vectorstore = PineconeVectorStore(index=index, embedding=embeddings)
        vectorstore.add_documents(all_docs)
    else:
        PineconeVectorStore.from_documents(
            all_docs,
            embeddings,
            index_name=index_name,
        )

    elapsed = time.time() - start_time
    print(f"Done! Uploaded {len(all_docs)} chunks to Pinecone.")
    print(f"Ingestion took {elapsed:.1f} seconds ({elapsed/60:.1f} minutes).")


if __name__ == "__main__":
    main()
