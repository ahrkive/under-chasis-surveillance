"""
Test Creator Dataset Gallery API
================================
Tests GET /api/admin/dataset-gallery endpoint and image file serving.
"""

import requests

BASE_URL = "http://localhost:8000"


def test_gallery():
    print("--- 1. Login as Creator ---")
    login_resp = requests.post(f"{BASE_URL}/auth/login", json={
        "username": "creator",
        "password": "creator123"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[OK] Token acquired.")

    print("\n--- 2. Fetching Dataset Gallery ---")
    gallery_resp = requests.get(f"{BASE_URL}/api/admin/dataset-gallery", headers=headers)
    assert gallery_resp.status_code == 200, f"Gallery failed: {gallery_resp.text}"
    gallery_data = gallery_resp.json()
    print(f"[OK] Total dataset images found: {gallery_data['total']}")

    if gallery_data["items"]:
        first_item = gallery_data["items"][0]
        print(f"   First Item ID:       {first_item['id']}")
        print(f"   Source:             {first_item['bot_id']}")
        print(f"   Decision:           {first_item['decision']}")
        print(f"   Image URL Endpoint: {first_item['image_url']}")

        print("\n--- 3. Fetching Raw Dataset Image File ---")
        img_resp = requests.get(f"{BASE_URL}{first_item['image_url']}", headers=headers)
        assert img_resp.status_code == 200, f"Image file fetch failed: {img_resp.status_code}"
        assert img_resp.headers["content-type"] == "image/jpeg"
        print(f"[OK] Image file retrieved successfully! Length: {len(img_resp.content)} bytes.")

    print("\n==========================================")
    print("  CREATOR DATASET GALLERY API PASSED!     ")
    print("==========================================")


if __name__ == "__main__":
    test_gallery()
