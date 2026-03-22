"""
test_waitlist.py — run with: python test_waitlist.py
Make sure waitlist.py is already running on port 5003.
"""
import requests, json

BASE = "http://127.0.0.1:5003"
OK   = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"

def check(label, r, expected):
    symbol = OK if r.status_code == expected else FAIL
    print(f"{symbol} [{r.status_code}] {label}")
    if r.status_code != expected:
        print(f"     Expected {expected} — body: {r.text}")
    else:
        print(f"     {json.dumps(r.json())}")

# ── Cleanup: pop everything out before starting ───────────────────────────────
print("\n=== CLEANUP: clearing any leftover data from previous runs ===")
for event_id in [101, 202]:
    while True:
        r = requests.get(f"{BASE}/waitlist/{event_id}/next")
        if r.json().get('volunteer_id') is None:
            break
print("     Done — queues are empty\n")

# ── Health ────────────────────────────────────────────────────────────────────
print("=== HEALTH ===")
check("GET /health", requests.get(f"{BASE}/health"), 200)

# ── Scenario 1: Add volunteers ────────────────────────────────────────────────
print("\n=== SCENARIO 1: Add 3 volunteers to waitlist for event 101 ===")
check("Add volunteer 201", requests.post(f"{BASE}/waitlist/101", json={"volunteer_id": 201}), 201)
check("Add volunteer 202", requests.post(f"{BASE}/waitlist/101", json={"volunteer_id": 202}), 201)
check("Add volunteer 203", requests.post(f"{BASE}/waitlist/101", json={"volunteer_id": 203}), 201)
check("Duplicate 201 → 409", requests.post(f"{BASE}/waitlist/101", json={"volunteer_id": 201}), 409)
check("Missing volunteer_id → 400", requests.post(f"{BASE}/waitlist/101", json={}), 400)

print("\n=== View queue (should show exactly 3 people in order) ===")
r = requests.get(f"{BASE}/waitlist/101")
check("GET /waitlist/101", r, 200)
assert r.json()['count'] == 3, f"Expected 3 in queue, got {r.json()['count']}"

# ── Scenario 2: Pop next volunteer ───────────────────────────────────────────
print("\n=== SCENARIO 2: Slot opens — pop next volunteer ===")

r = requests.get(f"{BASE}/waitlist/101/next")
check("GET /waitlist/101/next — should return and remove volunteer 201", r, 200)
assert r.json().get('volunteer_id') == 201, f"Expected 201, got {r.json().get('volunteer_id')}"

r = requests.get(f"{BASE}/waitlist/101")
check("GET /waitlist/101 — should now show 2 people", r, 200)
assert r.json()['count'] == 2, f"Expected 2 in queue, got {r.json()['count']}"

r = requests.get(f"{BASE}/waitlist/101/next")
check("GET /waitlist/101/next — should return volunteer 202", r, 200)
assert r.json().get('volunteer_id') == 202

r = requests.get(f"{BASE}/waitlist/101/next")
check("GET /waitlist/101/next — should return volunteer 203", r, 200)
assert r.json().get('volunteer_id') == 203

r = requests.get(f"{BASE}/waitlist/101/next")
check("GET /waitlist/101/next — queue empty, should return null", r, 200)
assert r.json().get('volunteer_id') is None

# ── Scenario 3: Fanout test setup ────────────────────────────────────────────
print("\n=== SCENARIO 3: AMQP fanout test ===")
requests.post(f"{BASE}/waitlist/101", json={"volunteer_id": 201})
requests.post(f"{BASE}/waitlist/101", json={"volunteer_id": 202})
r = requests.get(f"{BASE}/waitlist/101")
check("GET /waitlist/101 — 2 volunteers re-added for fanout test", r, 200)
assert r.json()['count'] == 2

print("""
     To test the fanout (event cancelled), run in a SEPARATE terminal:
         python simulate_event_cancelled.py 101

     Then check in browser:  http://127.0.0.1:5003/waitlist/101
     Expect:                 count = 0
""")

print("=== All HTTP tests passed! ===\n")