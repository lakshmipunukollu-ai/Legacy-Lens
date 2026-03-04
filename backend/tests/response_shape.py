import requests

BASE_URL = "https://legacy-lens-production-5e14.up.railway.app"

SHAPE_TESTS = [
    ("GET /health", "get", "/health", None, ["status", "latency_ms"]),
    ("GET /stats", "get", "/stats", None, ["total_chunks", "latency_ms"]),
    ("GET /health-dashboard", "get", "/health-dashboard", None, ["total_files", "total_loc", "total_chunks", "health_score", "health_notes", "top_files", "patterns_summary", "latency_ms"]),
    ("POST /query", "post", "/query", {"question": "test", "session_id": "shape"}, ["answer", "sources", "latency_ms"]),
    ("POST /dependencies", "post", "/dependencies", {"question": "test"}, ["answer", "sources", "graph", "latency_ms"]),
    ("POST /patterns", "post", "/patterns", {"keyword": "test"}, ["answer", "sources", "latency_ms"]),
    ("POST /document", "post", "/document", {"paragraph": "test"}, ["documentation", "sources", "latency_ms"]),
    ("POST /business-logic", "post", "/business-logic", {"question": "test"}, ["business_logic", "sources", "latency_ms"]),
    ("POST /explain-snippet", "post", "/explain-snippet", {"code": "MOVE ZEROS TO WS-COUNTER."}, ["explanation", "latency_ms"]),
    ("POST /clear-history", "post", "/clear-history", {"session_id": "shape"}, ["status", "session_id", "latency_ms"]),
]

def run_shape_tests():
    print("\n" + "="*60)
    print("RESPONSE SHAPE TEST")
    print("="*60)

    passed = 0
    failed = 0
    results = []

    for name, method, path, body, required_fields in SHAPE_TESTS:
        try:
            if method == "get":
                resp = requests.get(f"{BASE_URL}{path}", timeout=30)
            else:
                resp = requests.post(f"{BASE_URL}{path}", json=body, timeout=30)

            data = resp.json()
            missing = [f for f in required_fields if f not in data]

            # Check sources shape if present
            sources_ok = True
            if "sources" in data and data["sources"]:
                for s in data["sources"]:
                    if not all(k in s for k in ["file", "start_line", "end_line", "score", "snippet"]):
                        sources_ok = False
                        break

            if not missing and sources_ok:
                passed += 1
                results.append({"name": name, "status": "PASS"})
                print(f"\n✅ {name} — all {len(required_fields)} fields present")
                if "sources" in data:
                    print(f"   Sources shape: {'✓' if sources_ok else '✗'}")
            else:
                failed += 1
                results.append({"name": name, "status": "FAIL", "missing": missing, "sources_ok": sources_ok})
                print(f"\n❌ {name}")
                if missing:
                    print(f"   Missing fields: {missing}")
                if not sources_ok:
                    print(f"   Sources missing required fields")
        except Exception as e:
            failed += 1
            results.append({"name": name, "status": "ERROR", "error": str(e)})
            print(f"\n❌ {name} — ERROR: {e}")

    print(f"\nSHAPE TEST RESULTS: {passed}/{len(SHAPE_TESTS)} passed")
    print("="*60)
    return results, passed, failed

if __name__ == "__main__":
    run_shape_tests()
