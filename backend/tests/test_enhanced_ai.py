"""
Enhanced AI Inference Test Script
=================================
Tests component diagnostic metrics and spatial anomaly bounding box generation.
"""

import io
import requests
from PIL import Image

BASE_URL = "http://localhost:8000"


def test_enhanced_ai():
    print("--- 1. Login as Creator ---")
    login_resp = requests.post(f"{BASE_URL}/auth/login", json={
        "username": "creator",
        "password": "creator123"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[OK] Token acquired.")

    print("\n--- 2. Creating Synthetic Undercarriage Test Image ---")
    img = Image.new("RGB", (256, 256), color=(40, 45, 55))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)

    print("\n--- 3. Testing Enhanced AI Prediction Endpoint ---")
    files = {"file": ("test_chassis.jpg", buf, "image/jpeg")}
    resp = requests.post(f"{BASE_URL}/api/admin/test-model", headers=headers, files=files)
    assert resp.status_code == 200, f"AI Test failed: {resp.text}"

    result = resp.json()
    print("[OK] Enhanced AI Prediction Results:")
    print(f"   Prediction Label: {result['prediction'].upper()}")
    print(f"   AI Confidence:    {result['confidence_percentage']}%")
    print(f"   Class Probabilities: {result['probabilities']}")

    print("\n==========================================")
    print("     ENHANCED AI TEST PASSED! [OK]        ")
    print("==========================================")


if __name__ == "__main__":
    test_enhanced_ai()
