import httpx
import asyncio
import json

# --- Configuration ---
BASE_URL = "https://planform-backend.onrender.com"  # Your FastAPI app's address
PLAN_ENDPOINT_URL = f"{BASE_URL}/plan"

# !!! IMPORTANT: Replace with a VALID apiKey from an agency in YOUR development database !!!
AGENCY_API_KEY = "d135b96f6b3439f06cf5dd14a37b26b92d7ac0b9fb60729e514a5330018d52f0"

async def send_plan_request():
    payload = {
        "apiKey": AGENCY_API_KEY,
        "websiteUrl": "https://www.mattkarlson.com", # Or any other URL, or None
        "email": "manual.test.client@example.com",
        "name": "Manual Test Client",
        # Add any other known fields from your ClientResponses schema
        # You can also add arbitrary key-value pairs to test the 'extra' fields handling
        "projectGoal": "To manually test the plan endpoint",
        "preferredContactMethod": "email",
        "budgetRange": "1000-5000",
        "targetAudience": "developers"
    }

    print(f"Sending request to: {PLAN_ENDPOINT_URL}")
    print(f"Payload:\n{json.dumps(payload, indent=2)}\n")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client: # Increased timeout for potentially long operations
            response = await client.post(PLAN_ENDPOINT_URL, json=payload)

        print(f"Response Status Code: {response.status_code}")
        try:
            response_data = response.json()
            
            # Create a copy to modify for printing, excluding screenshotBase64
            data_to_print = response_data.copy()
            if "screenshotBase64" in data_to_print:
                del data_to_print["screenshotBase64"]
            
            print(f"Response Data (excluding screenshotBase64):{json.dumps(data_to_print, indent=2)}")
            
            # You can add specific checks here based on expected response
            if "planId" in response_data:
                print(f"\nSUCCESS: Plan created with ID: {response_data['planId']}")
            if "clientId" in response_data and response_data['clientId']:
                print(f"SUCCESS: Client involved with ID: {response_data['clientId']}")

        except json.JSONDecodeError:
            print(f"Response Content (not JSON):\n{response.text}")

    except httpx.ConnectError as e:
        print(f"Connection Error: Could not connect to {BASE_URL}.")
        print("Please ensure your FastAPI application is running.")
        print(f"Details: {e}")
    except Exception as e:
        print(f"An unexpected error occurred:")
        print(f"Error Type: {type(e)}")
        print(f"Error Details: {repr(e)}")
        # If the exception has a response attribute (like httpx.HTTPStatusError), print its content
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response Status Code (from exception): {e.response.status_code}")
            try:
                print(f"Response Content (from exception): {e.response.text}")
            except Exception as ex_resp:
                print(f"Could not get response text from exception: {ex_resp}")

if __name__ == "__main__":
    if AGENCY_API_KEY == "YOUR_VALID_AGENCY_API_KEY_HERE":
        print("ERROR: Please update the AGENCY_API_KEY in the script with a valid key!")
    else:
        asyncio.run(send_plan_request()) 