"""Create a test user and capture an auth token for manual API tests."""

from pathlib import Path
import json

import requests

# Create user (will fail if exists, that's OK)
print("Registering test user...")
response = requests.post(
    "http://localhost:8001/api/auth/register",
    json={
        "email": "test@example.com",
        "username": "testuser",
        "password": "testpassword123",
        "full_name": "Test User"
    }
)

# Now login regardless of whether register succeeded
print("Logging in...")
response = requests.post(
    "http://localhost:8001/api/auth/login",
    data={
        "username": "testuser",
        "password": "testpassword123"
    }
)

print(f"Auth Status: {response.status_code}")
result = response.json()
print(f"Response: {json.dumps(result, indent=2)}")

if "access_token" in result:
    token = result["access_token"]
    print(f"\nAccess Token: {token}")

    token_path = Path(__file__).parent / "test_token.txt"
    token_path.write_text(token, encoding="utf-8")
    print(f"Token saved to {token_path.name}")
else:
    print("\nNo access token received!")
