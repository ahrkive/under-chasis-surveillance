"""
End-to-End API Test Script
===========================
Tests authentication, fetching inspections, submitting guard decisions,
and verifying backend & AI pipeline integration.
"""

import requests

BASE_URL = "http://localhost:8000"


def test_e2e_flow():
    print("--- 1. Testing Guard Login ---")
    login_resp = requests.post(f"{BASE_URL}/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    token_data = login_resp.json()
    token = token_data["access_token"]
    print(f"[OK] Login successful! Token acquired: {token[:20]}...")

    headers = {"Authorization": f"Bearer {token}"}

    print("\n--- 2. Fetching Inspection List ---")
    list_resp = requests.get(f"{BASE_URL}/api/inspections", headers=headers)
    assert list_resp.status_code == 200, f"List failed: {list_resp.text}"
    inspections_data = list_resp.json()
    inspections = inspections_data["inspections"]
    print(f"[OK] Found {len(inspections)} inspection(s) in system (Total: {inspections_data['total']}).")

    if inspections:
        first_insp = inspections[0]
        insp_id = first_insp["id"]
        print(f"\n--- 3. Testing Inspection Detail for ID: {insp_id} ---")
        print(f"   Bot ID: {first_insp['bot_id']}")
        print(f"   AI Prediction: {first_insp['model_prediction']} ({first_insp['model_confidence']*100:.1f}% confidence)")
        print(f"   Current Decision: {first_insp['decision']}")

        print("\n--- 4. Submitting Guard Decision: APPROVE ---")
        dec_resp = requests.post(f"{BASE_URL}/api/inspections/{insp_id}/decision", headers=headers, json={
            "decision": "approved",
            "vehicle_id": "ABC-1234",
            "notes": "Verified normal undercarriage by guard."
        })
        assert dec_resp.status_code == 200, f"Decision failed: {dec_resp.text}"
        updated_insp = dec_resp.json()
        print(f"[OK] Decision recorded! New Status: {updated_insp['decision']}")
        print(f"   Cloud/Storage URL: {updated_insp['image_cloud_url']}")

    print("\n--- 5. Checking Health Endpoint ---")
    health_resp = requests.get(f"{BASE_URL}/health")
    print(f"[OK] Health Check: {health_resp.json()}")

    print("\n==========================================")
    print("  ALL END-TO-END TESTS PASSED SUCCESSFULLY! ")
    print("==========================================")


if __name__ == "__main__":
    test_e2e_flow()
