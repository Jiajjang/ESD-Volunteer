import requests
import json

# ── CONFIG ──────────────────────────────────────────────
EVENT_ID = 10
CONFIRMED_VOLUNTEER_ID = 38  # volunteer to cancel
REGISTRATION_URL = "http://localhost:5000"          # Registration Service
COMPOSITE_URL = "http://localhost:5010"             # Composite Service

# ── HELPER FUNCTION TO FETCH REGISTRATIONS ─────────────
def fetch_registrations(event_id):
    try:
        res = requests.get(f"{REGISTRATION_URL}/registration/{event_id}")
        if res.status_code == 200:
            return res.json()["data"]["Registrations"]
        else:
            print(f"Failed to fetch registrations: {res.status_code} - {res.text}")
            return []
    except Exception as e:
        print(f"Error fetching registrations: {e}")
        return []

# ── FETCH CURRENT REGISTRATIONS ───────────────────────
registrations = fetch_registrations(EVENT_ID)
print(f"Current registrations for event {EVENT_ID}:")
for r in registrations:
    print(f"{r['volunteer_id']} - {r['email']} - {r['status']}")

# ── CANCEL CONFIRMED VOLUNTEER VIA COMPOSITE ──────────
print(f"\nCancelling confirmed volunteer: {CONFIRMED_VOLUNTEER_ID}")
try:
    cancel_resp = requests.post(
        f"{COMPOSITE_URL}/cancel-registration",
        json={
            "volunteerID": CONFIRMED_VOLUNTEER_ID,
            "eventID": EVENT_ID,
            "timeSlot": ""  # optional for now
        }
    )
    cancel_data = cancel_resp.json()
    print("\nComposite cancel response:")
    print(json.dumps(cancel_data, indent=2))
except Exception as e:
    print(f"Failed to cancel volunteer: {e}")

# ── FETCH UPDATED REGISTRATIONS ───────────────────────
updated_registrations = fetch_registrations(EVENT_ID)
print("\nUpdated registrations after cancellation and promotion:")
for r in updated_registrations:
    print(f"{r['volunteer_id']} - {r['email']} - {r['status']}")

# ── SHOW PROMOTED VOLUNTEER IF ANY ────────────────────
promoted_id = cancel_data.get("data", {}).get("promotedVolunteerID")
if promoted_id:
    print(f"\nPromoted volunteer ID: {promoted_id}")
else:
    print("\nNo volunteer was promoted.")