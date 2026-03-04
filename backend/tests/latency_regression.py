import requests
import time
import statistics

BASE_URL = "https://legacy-lens-production-5e14.up.railway.app"

# Warm up with a real query to initialize Pinecone + OpenAI connections
print("Warming up backend...")
try:
    requests.post(f"{BASE_URL}/query",
        json={"question": "Where is the main entry point?", "session_id": "warmup"},
        timeout=30)
    print("Backend warm.")
except Exception:
    pass
time.sleep(2)

ENDPOINTS = [
    ("GET /health", "get", "/health", None),
    ("GET /stats", "get", "/stats", None),
    ("GET /health-dashboard", "get", "/health-dashboard", None),
    ("POST /query", "post", "/query", {"question": "Where is the main entry point?", "session_id": "latency"}),
    ("POST /dependencies", "post", "/dependencies", {"question": "What calls main?"}),
    ("POST /patterns", "post", "/patterns", {"keyword": "error handling"}),
    ("POST /document", "post", "/document", {"paragraph": "main procedure"}),
    ("POST /business-logic", "post", "/business-logic", {"question": "What business rules exist?"}),
    ("POST /clear-history", "post", "/clear-history", {"session_id": "latency"}),
]

RUNS = 3

def run_latency_tests():
    print("\n" + "="*60)
    print(f"LATENCY REGRESSION TEST ({RUNS} runs each)")
    print("="*60)

    all_pass = True
    results = []
    for name, method, path, body in ENDPOINTS:
        latencies = []
        for i in range(RUNS):
            start = time.time()
            if method == "get":
                resp = requests.get(f"{BASE_URL}{path}", timeout=30)
            else:
                resp = requests.post(f"{BASE_URL}{path}", json=body, timeout=30)
            latencies.append(round((time.time() - start) * 1000))
            time.sleep(0.5)

        # For health and stats, skip first run (cold start) and average runs 2-3
        if name == "GET /health" or name == "GET /stats":
            measured_latencies = latencies[1:]  # Skip first run
            target = 1000
        else:
            measured_latencies = latencies
            target = 3000
        avg = round(statistics.mean(measured_latencies))
        min_l = min(measured_latencies)
        max_l = max(measured_latencies)
        passes = avg <= target
        if not passes:
            all_pass = False

        results.append({"name": name, "avg": avg, "min": min_l, "max": max_l, "pass": passes})

        print(f"\n{name}")
        print(f"  Runs: {latencies}")
        print(f"  Avg: {avg}ms | Min: {min_l}ms | Max: {max_l}ms")
        print(f"  Target: {target}ms — {'✓ PASS' if passes else '✗ FAIL'}")

    print(f"\nOVERALL: {'✓ ALL PASS' if all_pass else '✗ SOME FAILED'}")
    print("="*60)
    return results, all_pass

if __name__ == "__main__":
    run_latency_tests()
