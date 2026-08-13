import urllib.request
import json
import time

BASE = "http://localhost:8000"

# Test 1: health
print("=== TEST 1: Backend root ===")
try:
    resp = urllib.request.urlopen(f"{BASE}/", timeout=5)
    print(f"Status: {resp.status}")
except Exception as e:
    print(f"Root: {e}")

# Test 2: workspace/chat with empty paper_ids
print("\n=== TEST 2: workspace/chat ===")
payload = json.dumps({"message": "cho minh chi tiet thuat toan 1", "paper_ids": []}).encode()
req = urllib.request.Request(
    f"{BASE}/api/v1/workspace/chat",
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST"
)
try:
    t0 = time.time()
    resp = urllib.request.urlopen(req, timeout=60)
    elapsed = time.time() - t0
    data = json.loads(resp.read())
    print(f"Status: 200 OK ({elapsed:.1f}s)")
    print(f"Answer: {data.get('answer', '')[:200]}")
    print(f"Citations count: {len(data.get('citations', []))}")
    print(f"Context used: {len(data.get('context_used', []))}")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"HTTP {e.code}: {body[:500]}")
except Exception as e:
    print(f"FAIL: {type(e).__name__}: {e}")
