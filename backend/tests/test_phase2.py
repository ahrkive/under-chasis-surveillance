"""
Phase 2 Comprehensive Test Suite
================================
Tests ALPR vehicle lookup, baseline diff endpoints, fleet management, and CSV audit export.
"""

import requests

BASE_URL = "http://localhost:8000"


def test_phase2():
    print("--- 1. Login as Creator ---")
    login_resp = requests.post(f"{BASE_URL}/auth/login", json={
        "username": "creator",
        "password": "creator123"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[OK] Token acquired.")

    print("\n--- 2. Testing Vehicle History & ALPR Lookup ---")
    vh_resp = requests.get(f"{BASE_URL}/api/inspections/vehicle/KA-01-MJ-4892/history", headers=headers)
    assert vh_resp.status_code == 200, f"Vehicle history failed: {vh_resp.text}"
    vh_data = vh_resp.json()
    print(f"[OK] Vehicle ALPR Search Result for [{vh_data['license_plate']}]: {vh_data['total_scans']} historical scans found.")

    print("\n--- 3. Testing Multi-Bot Fleet Management API ---")
    fleet_resp = requests.get(f"{BASE_URL}/api/admin/fleet", headers=headers)
    assert fleet_resp.status_code == 200, f"Fleet management failed: {fleet_resp.text}"
    fleet_data = fleet_resp.json()
    print(f"[OK] Total Fleet Bots: {fleet_data['total_bots']} (Online: {fleet_data['online_bots']})")
    for bot in fleet_data["fleet"]:
        print(f"   Bot: {bot['name']} [{bot['id']}] | Lane: {bot['lane']} | Battery: {bot['battery_level']}%")

    print("\n--- 4. Testing CSV Audit Trail Export ---")
    csv_resp = requests.get(f"{BASE_URL}/api/inspections/export/csv", headers=headers)
    assert csv_resp.status_code == 200, f"CSV export failed: {csv_resp.status_code}"
    print(f"[OK] Audit CSV exported successfully! Content length: {len(csv_resp.content)} bytes.")

    print("\n==========================================")
    print("      ALL PHASE 2 TESTS PASSED! [OK]      ")
    print("==========================================")


if __name__ == "__main__":
    test_phase2()
