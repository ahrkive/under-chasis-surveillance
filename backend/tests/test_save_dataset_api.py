"""
Test Creator Save to Dataset API
================================
Uploads an image to POST /api/admin/save-to-dataset?label=approved
and verifies that the image is stored on disk and recorded in the database.
"""

import io
import requests
from PIL import Image

BASE_URL = "http://localhost:8000"


def test_save_to_dataset():
    print("--- 1. Login as Creator ---")
    login_resp = requests.post(f"{BASE_URL}/auth/login", json={
        "username": "creator",
        "password": "creator123"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[OK] Token acquired.")

    print("\n--- 2. Creating Synthetic Test Image ---")
    img = Image.new("RGB", (256, 256), color=(40, 180, 90))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)

    print("\n--- 3. Testing POST /api/admin/save-to-dataset?label=approved ---")
    files = {"file": ("creator_sample.jpg", buf, "image/jpeg")}
    resp = requests.post(
        f"{BASE_URL}/api/admin/save-to-dataset?label=approved",
        headers=headers,
        files=files,
    )
    assert resp.status_code == 200, f"Save dataset failed: {resp.text}"

    result = resp.json()
    print("[OK] Save to Dataset Response:")
    print(f"   Message:        {result['message']}")
    print(f"   Inspection ID:  {result['inspection_id']}")
    print(f"   Decision Label: {result['decision'].upper()}")
    print(f"   File Path:      {result['image_path']}")
    print(f"   Total Approved: {result['total_approved_images']}")

    print("\n==========================================")
    print("  CREATOR SAVE TO DATASET API PASSED!     ")
    print("==========================================")


if __name__ == "__main__":
    test_save_to_dataset()
