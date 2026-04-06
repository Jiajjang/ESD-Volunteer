# test_delete_registration.py
import requests
import time

# ── CONFIG ─────────────────────────────────────────────────────────────
BASE_URLS = {
    "registration": "http://localhost:5000",
    "delete_registration": "http://localhost:5011",
    "waitlist": "http://localhost:5003"
}

EVENT_ID = 5
VOLUNTEER_TO_CANCEL = 27 # volunteer ID to cancel --> check if 23 (waitlisted) gets promoted as their registration is earliest
TIMEOUT_TEST_VOLUNTEER = 4 # volunteer ID to simulate timeout

# ── UTILITY FUNCTIONS ─────────────────────────────────────────────────
def pretty(resp):
    print(resp.status_code)
    print(resp.json())

def list_registrations():
    resp = requests.get(f"{BASE_URLS['registration']}/registration")
    try:
        data = resp.json()
    except ValueError:
        print("Error: registration service returned non-JSON")
        return []
    return data.get("data", {}).get("Registrations", [])

def list_waitlist(event_id):
    resp = requests.get(f"{BASE_URLS['waitlist']}/waitlist/{event_id}")
    return resp.json().get("data", [])

def pretty(resp):
    print(resp.status_code)
    try:
        print(resp.json())
    except ValueError:
        print(resp.text)  # safely print non-JSON responses
        
# ── 1. List registrations before cancel ───────────────────────────────
print("Registrations BEFORE cancel:")
regs = list_registrations()
print("DEBUG: regs type =", type(regs))  # should be <class 'list'>
if regs:
    print("DEBUG: first reg =", regs[0])
reg_to_cancel = next((r for r in regs if r["volunteer_id"] == VOLUNTEER_TO_CANCEL), None)


# Find registration ID to cancel for VOLUNTEER_TO_CANCEL
reg_to_cancel = next(
    (r for r in regs if r["volunteer_id"] == VOLUNTEER_TO_CANCEL), None
)
if not reg_to_cancel:
    raise Exception(f"No registration found for volunteer {VOLUNTEER_TO_CANCEL}")


# Use 'registration_id' from the API, not 'id'
registration_id = reg_to_cancel["registration_id"]

# ── 2. Cancel registration ────────────────────────────────────────────
cancel_payload = {
    "volunteer_id": VOLUNTEER_TO_CANCEL,
    "event_id": EVENT_ID,
    "registration_id": registration_id
}
print("\nCancelling registration...")
cancel_resp = requests.post(f"{BASE_URLS['delete_registration']}/cancel-registration", json=cancel_payload)
pretty(cancel_resp)

# ── 3. List registrations AFTER cancel ────────────────────────────────
print("\nRegistrations AFTER cancel:")
regs = list_registrations()
for r in regs:
    print(r)

# ── 4. Check waitlist and promotion ──────────────────────────────────
print("\nWaitlist for event after cancel:")
waitlist = list_waitlist(EVENT_ID)
for w in waitlist:
    print(w)

# Extract promoted volunteer ID
promoted_id = cancel_resp.json().get("data", {}).get("promotedVolunteerID")
if promoted_id:
    print(f"\nPromoted volunteer ID: {promoted_id}")

    # ── 5. Respond to promotion ──────────────────────────────────────
if promoted_id:
    respond_payload = {
        "volunteer_id": promoted_id,
        "event_id": EVENT_ID,
        "status": "confirmed"
    }
    print("\nResponding to promotion (confirming)...")
    url = f"{BASE_URLS['delete_registration']}/cancel-registration/respond"
    print("DEBUG URL:", url)
    print("DEBUG Payload:", respond_payload)
    resp_resp = requests.put(url, json=respond_payload)
    pretty(resp_resp)
else:
    print("No one promoted from waitlist (queue empty)")


# ── 6. Simulate a timeout (optional) ────────────────────────────────
print("\nSimulating timeout for volunteer_id:", TIMEOUT_TEST_VOLUNTEER)
timeout_payload = {
    "volunteer_id": TIMEOUT_TEST_VOLUNTEER,
    "event_id": EVENT_ID
}
timeout_resp = requests.put(f"{BASE_URLS['delete_registration']}/cancel-registration/timeout", json=timeout_payload)
pretty(timeout_resp)

print("\nTest completed.")