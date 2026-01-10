import httpx
import json

def list_endpoints():
    try:
        response = httpx.get("http://localhost:9999/openapi.json")
        if response.status_code == 200:
            schema = response.json()
            paths = schema.get("paths", {})
            print("Available Endpoints:")
            for path in paths:
                print(f"- {path}")
        else:
            print(f"Failed to fetch schema: {response.status_code}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_endpoints()
