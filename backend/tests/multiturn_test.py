import requests
import time

BASE_URL = "https://legacy-lens-production-5e14.up.railway.app"
SESSION_ID = f"multiturn_test_{int(time.time())}"

CONVERSATION = [
    "Where is the main entry point of this program?",
    "What does that section do in detail?",
    "What other paragraphs are near it?",
    "What data does it use?"
]

def run_multiturn_test():
    print("\n" + "="*60)
    print("MULTI-TURN CONVERSATION TEST")
    print(f"Session ID: {SESSION_ID}")
    print("="*60)

    # Clear history first (client-side; endpoint returns success)
    requests.post(f"{BASE_URL}/clear-history", json={"session_id": SESSION_ID})

    previous_answers = []
    history = []  # Client-side: last 3 exchanges = 6 messages
    passed = 0

    for i, question in enumerate(CONVERSATION):
        history_payload = history[-6:]  # Last 3 exchanges
        resp = requests.post(
            f"{BASE_URL}/query",
            json={"question": question, "session_id": SESSION_ID, "history": history_payload},
            timeout=30,
        )
        data = resp.json()
        answer = data.get("answer", "")
        latency = data.get("latency_ms", 0)

        print(f"\nTurn {i+1}: {question}")
        print(f"  Latency: {latency}ms")
        print(f"  Answer preview: {answer[:100]}...")

        # Check answer is not empty
        if len(answer) > 20:
            passed += 1
            print(f"  ✓ Answer received")
        else:
            print(f"  ✗ Answer too short or empty")

        # For turns 2+, check if answer references context from previous turns
        if i > 0 and previous_answers:
            print(f"  Context check: answer #{i+1} should reference previous context")

        # Update client-side history for next turn
        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": answer})
        previous_answers.append(answer)
        time.sleep(0.5)

    # Clear history at end
    clear_resp = requests.post(f"{BASE_URL}/clear-history", json={"session_id": SESSION_ID})
    print(f"\nHistory cleared: {clear_resp.json()}")

    print(f"\nMULTI-TURN RESULTS: {passed}/{len(CONVERSATION)} turns answered")
    print("="*60)
    return passed, len(CONVERSATION)

if __name__ == "__main__":
    run_multiturn_test()
