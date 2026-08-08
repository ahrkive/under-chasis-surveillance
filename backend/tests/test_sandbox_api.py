"""
Test Creator AI Sandbox Inference API
=====================================
Uploads a synthetic JPEG image to POST /api/admin/test-model
and verifies predictions, confidence, and class probabilities.
"""

import io
import requests
from PIL import Image

BASE_URL = "http://localhost:8000"


def test_sandbox():
    print("--- 1. Login as Creator ---")
    login_resp = requests.post(f"{BASE_URL}/auth/login", json={
        "username": "creator",
        "password": "creator123"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[OK] Token acquired.")

    print("\n--- 2. Creating Synthetic Test Image ---")
    img = Image.new("RGB", (300, 300), color=(100, 50, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)

    print("\n--- 3. Testing POST /api/admin/test-model ---")
    files = {"file": ("test_car.jpg", buf, "image/jpeg")}
    resp = requests.post(f"{BASE_URL}/api/admin/test-model", headers=headers, files=files)
    assert resp.status_code == 200, f"Sandbox test failed: {resp.text}"

    result = resp.json()
    print("[OK] Model Sandbox Inference Result:")
    print(f"   Filename:     {result['filename']}")
    print(f"   Prediction:   {result['prediction'].upper()}")
    print(f"   Confidence:   {result['confidence_percentage']}%")
    print(f"   Probabilities: OK={result['probabilities']['ok']*100:.1f}%, Suspicious={result['probabilities']['suspicious']*100:.1f}%")
    print(f"   Architecture: {result['architecture']} (v{result['model_version']})")

    print("\n==========================================")
    print("  AI TESTING SANDBOX API TEST PASSED!      ")
    print("==========================================")


if __name__ == "__main__":
    test_sandbox()
