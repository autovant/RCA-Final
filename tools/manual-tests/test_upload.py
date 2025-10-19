"""Manual helper to upload a log file and inspect progress events."""

from pathlib import Path
import json
import time

import requests

# Resolve assets relative to this script so the tool works from any cwd
ASSET_DIR = Path(__file__).parent
token_path = ASSET_DIR / "test_token.txt"
log_path = ASSET_DIR / "test-error.log"


if not token_path.exists():
    print("No token found! Run get_token.py first.")
    exit(1)

token = token_path.read_text(encoding="utf-8").strip()

headers = {"Authorization": f"Bearer {token}"}

# Upload file
print("Uploading test file...")
with log_path.open("rb") as f:
    files = {"file": (log_path.name, f, "text/plain")}
    response = requests.post("http://localhost:8001/api/files/upload", files=files, headers=headers)

print(f"Upload Status: {response.status_code}")
result = response.json()
print(f"Response: {json.dumps(result, indent=2)}")

job_id = result.get("job_id")
if not job_id:
    print("No job_id in response!")
    exit(1)

print(f"\nJob ID: {job_id}")
print("Waiting 10 seconds for processing...")
time.sleep(10)

# Get job details
print(f"\nFetching job details...")
job_response = requests.get(f"http://localhost:8001/api/jobs/{job_id}")
job_data = job_response.json()
print(f"Job Status: {job_data.get('status')}")
print(f"Job Details: {json.dumps(job_data, indent=2)}")

# Get progress events
print(f"\nFetching progress events...")
events_response = requests.get(f"http://localhost:8001/api/jobs/{job_id}/events")
events = events_response.json()

print(f"\nTotal Events: {len(events)}")
print("\n" + "="*80)
for idx, event in enumerate(events, 1):
    event_data = event.get("data", {})
    print(f"\nEvent {idx}:")
    print(f"  Type: {event.get('event_type')}")
    print(f"  Step: {event_data.get('step')}")
    print(f"  Status: {event_data.get('status')}")
    print(f"  Label: {event_data.get('label')}")
    print(f"  Message: {event_data.get('message')}")
    details = event_data.get('details', {})
    if details:
        print(f"  Progress: {details.get('progress', 'N/A')}%")
        print(f"  Details: {json.dumps(details, indent=4)}")
    print("-" * 80)
