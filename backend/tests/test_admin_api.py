"""
Creator & Guard Dual-Login Role API Test
========================================
Tests both Creator and Guard login workflows, permission checks,
telemetry stats, and model controls.
"""

import requests

BASE_URL = "http://localhost:8000"


def test_dual_roles():
    print("--- 1. Testing Creator Login (creator / creator123) ---")
    creator_resp = requests.post(f"{BASE_URL}/auth/login", json={
        "username": "creator",
        "password": "creator123"
    })
    assert creator_resp.status_code == 200, f"Creator login failed: {creator_resp.text}"
    creator_token = creator_resp.json()["access_token"]
    print("[OK] Creator logged in successfully!")

    creator_headers = {"Authorization": f"Bearer {creator_token}"}

    print("\n--- 2. Testing Creator Telemetry & System Stats ---")
    stats_resp = requests.get(f"{BASE_URL}/api/admin/stats", headers=creator_headers)
    assert stats_resp.status_code == 200, f"Stats failed: {stats_resp.text}"
    stats = stats_resp.json()
    print(f"[OK] System Telemetry:")
    print(f"   Storage: {stats['system']['storage_size_mb']} MB ({stats['system']['storage_provider']})")
    print(f"   Active Model: Version {stats['ai_model']['active_version']} ({stats['ai_model']['architecture']})")
    print(f"   Inspections Breakdown: {stats['inspections']['approved']} Approved / {stats['inspections']['rejected']} Rejected")

    print("\n--- 3. Testing Guard Login (guard / guard123) ---")
    guard_resp = requests.post(f"{BASE_URL}/auth/login", json={
        "username": "guard",
        "password": "guard123"
    })
    assert guard_resp.status_code == 200, f"Guard login failed: {guard_resp.text}"
    guard_token = guard_resp.json()["access_token"]
    print("[OK] Guard logged in successfully!")

    guard_headers = {"Authorization": f"Bearer {guard_token}"}

    print("\n--- 4. Testing Role Permission Isolation ---")
    guard_admin_resp = requests.get(f"{BASE_URL}/api/admin/stats", headers=guard_headers)
    assert guard_admin_resp.status_code == 403, "Security violation: Guard was able to access Creator endpoint!"
    print("[OK] Guard access to Creator Command Center properly FORBIDDEN (403 Access Denied)!")

    print("\n==========================================")
    print("  CREATOR & GUARD DUAL-LOGIN TESTS PASSED! ")
    print("==========================================")


if __name__ == "__main__":
    test_dual_roles()
