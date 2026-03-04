import subprocess
import threading
import time
import requests
import sys
import os

BASE_URL = "https://legacy-lens-production-5e14.up.railway.app"
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))

stop_event = threading.Event()


def keep_warm():
    """Ping backend every 60 seconds to prevent Railway from sleeping"""
    while not stop_event.is_set():
        try:
            requests.get(f"{BASE_URL}/health", timeout=5)
        except Exception:
            pass
        stop_event.wait(60)


def warm_up():
    print("=" * 60)
    print("WARMING UP BACKEND...")
    print("=" * 60)
    for i in range(2):
        try:
            resp = requests.post(
                f"{BASE_URL}/query",
                json={"question": "Where is the main entry point?", "session_id": "warmup"},
                timeout=30,
            )
            print(f"Warm-up {i+1}/2: {resp.status_code} {resp.json().get('latency_ms')}ms")
        except Exception as e:
            print(f"Warm-up {i+1}/2: {e}")
        time.sleep(2)
    print("Backend warm.\n")


def run_test(test_file):
    print(f"\n{'='*60}")
    print(f"RUNNING: {test_file}")
    print(f"{'='*60}")
    result = subprocess.run(
        [sys.executable, os.path.join(TESTS_DIR, test_file)],
        capture_output=False,
        timeout=120,
    )
    time.sleep(2)
    return result.returncode


if __name__ == "__main__":
    # Start keep-warm thread
    warm_thread = threading.Thread(target=keep_warm, daemon=True)
    warm_thread.start()

    try:
        # Warm up first
        warm_up()

        # Run all tests sequentially
        tests = [
            "golden_eval.py",
            "retrieval_precision.py",
            "latency_regression.py",
            "response_shape.py",
            "multiturn_test.py",
        ]

        results = {}
        for test in tests:
            try:
                code = run_test(test)
                results[test] = "PASS" if code == 0 else "FAIL"
            except subprocess.TimeoutExpired:
                results[test] = "TIMEOUT"
            except Exception as e:
                results[test] = f"ERROR: {e}"

        print("\n" + "=" * 60)
        print("FINAL SUMMARY")
        print("=" * 60)
        for test, result in results.items():
            print(f"{result:10} — {test}")

    finally:
        stop_event.set()
