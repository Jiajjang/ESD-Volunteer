import requests
import json
from datetime import datetime, timedelta
import pytz
sg_tz = pytz.timezone('Asia/Singapore')

# ── CONFIG ──────────────────────────────────────────────
EVENT_ID = 3
CONFIRMED_VOLUNTEER_ID = 14  # volunteer to cancel
REGISTRATION_URL = "http://localhost:5000"          # Registration Service
WAITLIST_URL = "http://localhost:5003" #waitlist service
COMPOSITE_URL = "http://localhost:5011"             # Composite Service

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
    print(f"{r['volunteer_id']} - {r['email']} - {r['status']} - expires_at={r.get('expires_at')}")

# ── CANCEL CONFIRMED VOLUNTEER VIA COMPOSITE ──────────
print(f"\nCancelling confirmed volunteer: {CONFIRMED_VOLUNTEER_ID}")
try:
    request_time = datetime.now(sg_tz)
    cancel_resp = requests.post(
        f"{COMPOSITE_URL}/cancel-registration",
        json={
            "volunteer_id": CONFIRMED_VOLUNTEER_ID,
            "event_id": EVENT_ID,
            "timeSlot": ""  # optional for now
        }
    )
    response_time = datetime.now(sg_tz)
    cancel_data = cancel_resp.json()
    print("\nComposite cancel response:")
    print(json.dumps(cancel_data, indent=2))
except Exception as e:
    print(f"Failed to cancel volunteer: {e}")

# ── FETCH UPDATED REGISTRATIONS ───────────────────────
updated_registrations = fetch_registrations(EVENT_ID)
print("\nUpdated registrations after cancellation and promotion:")
for r in updated_registrations:
    print(f"{r['volunteer_id']} - {r['email']} - {r['status']} - expires_at={r.get('expires_at')}")

# ── SHOW PROMOTED VOLUNTEER IF ANY ────────────────────
promoted_id = cancel_data.get("data", {}).get("promotedVolunteerID")
if promoted_id:
    print(f"\nPromoted volunteer ID: {promoted_id}")
    promoted = cancel_data.get("data", {}).get("promotedVolunteer", {})
    expires_at = promoted.get("expires_at")

    print("expires_at returned:", expires_at)

    if expires_at:
        parsed = sg_tz.localize(datetime.strptime(expires_at, "%Y-%m-%dT%H:%M:%S"))
        print("parsed expires_at:", parsed)

        lower_bound = request_time + timedelta(hours=23, minutes=59)
        upper_bound = response_time + timedelta(hours=24, minutes=1)

        if lower_bound <= parsed <= upper_bound:
            print("PASS: expires_at is about 24 hours from now")
        else:
            print("FAIL: expires_at is not about 24 hours from now")

        print("time remaining:", parsed - response_time)
    else:
        print("No expires_at returned for promoted volunteer")
else:
    print("\nNo volunteer was promoted.")