import requests
import json

BASE_URL = "https://legacy-lens-production-5e14.up.railway.app"

# For each query, define what a RELEVANT source looks like
PRECISION_TESTS = [
    {
        "id": "P1",
        "query": {"question": "Where is the main entry point?", "session_id": "precision"},
        "relevant_indicators": ["procedure division", "main", "program-id", "identification"],
        "description": "Main entry point query"
    },
    {
        "id": "P2",
        "query": {"question": "Find all file I/O operations", "session_id": "precision"},
        "relevant_indicators": ["open", "close", "read", "write", "file"],
        "description": "File I/O query"
    },
    {
        "id": "P3",
        "query": {"question": "Show me error handling patterns", "session_id": "precision"},
        "relevant_indicators": ["error", "invalid key", "at end", "exception", "on error"],
        "description": "Error handling query"
    }
]

def run_precision_tests():
    print("\n" + "="*60)
    print("RETRIEVAL PRECISION TEST")
    print("="*60)

    total_relevant = 0
    total_retrieved = 0

    for test in PRECISION_TESTS:
        resp = requests.post(f"{BASE_URL}/query", json=test["query"], timeout=30)
        data = resp.json()
        sources = data.get("sources", [])

        relevant = 0
        for source in sources:
            snippet = source.get("snippet", "").lower()
            if any(ind in snippet for ind in test["relevant_indicators"]):
                relevant += 1

        precision = relevant / len(sources) if sources else 0
        total_relevant += relevant
        total_retrieved += len(sources)

        print(f"\n[{test['id']}] {test['description']}")
        print(f"  Retrieved: {len(sources)} chunks")
        print(f"  Relevant: {relevant} chunks")
        print(f"  Precision: {precision:.0%}")
        for s in sources:
            print(f"  - {s.get('file')} L{s.get('start_line')} score={s.get('score', 0):.1f}")

    overall_precision = total_relevant / total_retrieved if total_retrieved else 0
    print(f"\nOVERALL PRECISION: {overall_precision:.0%} (target: >70%)")
    print("="*60)
    return overall_precision

if __name__ == "__main__":
    run_precision_tests()
