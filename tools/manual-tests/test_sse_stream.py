"""Manual helper to stream SSE events from a completed job."""

from pathlib import Path
import asyncio
import json

import httpx

async def test_sse():
    token_path = Path(__file__).parent / "test_token.txt"
    if not token_path.exists():
        raise FileNotFoundError("Missing test_token.txt. Run get_token.py first.")

    token = token_path.read_text(encoding="utf-8").strip()
    
    # Use the completed job ID
    job_id = "407a7d2d-12fb-4036-9927-fceffbe4c58c"
    url = f"http://localhost:8001/api/jobs/{job_id}/stream"
    
    print(f"Connecting to SSE stream: {url}")
    
    async with httpx.AsyncClient() as client:
        async with client.stream("GET", url, headers={"Authorization": f"Bearer {token}"}, timeout=30.0) as response:
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
            
            count = 0
            async for line in response.aiter_lines():
                if not line.strip():
                    continue
                    
                print(f"\n--- Event {count + 1} ---")
                print(line)
                
                if line.startswith("data:"):
                    try:
                        data = json.loads(line[5:].strip())
                        print(f"Event Type: {data.get('event_type')}")
                        if data.get('event_type') == 'analysis-progress':
                            print(f"  Step: {data.get('data', {}).get('step')}")
                            print(f"  Status: {data.get('data', {}).get('status')}")
                            print(f"  Message: {data.get('data', {}).get('message')}")
                    except Exception as e:
                        print(f"Failed to parse: {e}")
                
                count += 1
                if count >= 10:  # Get first 10 events
                    break
    
    print(f"\nReceived {count} events from SSE stream")

if __name__ == "__main__":
    asyncio.run(test_sse())
