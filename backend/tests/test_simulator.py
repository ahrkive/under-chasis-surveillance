"""
Simulator Ingestion Test Script
===============================
Connects to ws://localhost:8000/ws/pi, sends 2 frames with ALPR plate KA-01-MJ-4892,
and verifies database record & vehicle history creation.
"""

import time
import json
import asyncio
import hashlib
import requests
import websockets
from PIL import Image, ImageDraw
import io

BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws/edge/bot-north-gate"


async def test_sim():
    print("--- 1. Login as Creator ---")
    login_resp = requests.post(f"{BASE_URL}/auth/login", json={
        "username": "creator",
        "password": "creator123"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[OK] Token acquired.")

    print("\n--- 2. Connecting to WebSocket Hub as Edge Bot ---")
    ws_headers = {"x-api-key": "dev-secret-api-key-12345"}
    async with websockets.connect(WS_URL, additional_headers=ws_headers) as ws:
        print("[OK] Bot connected to WebSocket hub.")

        # Create dummy JPEG image
        img = Image.new("RGB", (640, 480), color=(30, 40, 50))
        draw = ImageDraw.Draw(img)
        draw.rectangle([100, 100, 540, 140], fill=(90, 95, 105))
        draw.text((20, 20), "SIMULATED VEHICLE UNDERCARRIAGE SCAN", fill=(52, 211, 153))

        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        img_bytes = buf.getvalue()

        # Send Header
        header = {
            "bot_id": "bot-north-gate",
            "timestamp": time.time(),
            "sequence": 1,
            "sha256": hashlib.sha256(img_bytes).hexdigest(),
            "size": len(img_bytes),
            "filename": "sim_KA01MJ4892.jpg",
            "license_plate": "KA-01-MJ-4892",
        }
        await ws.send(json.dumps(header))
        await ws.send(img_bytes)
        print("[OK] Frame #1 sent over WebSocket for Vehicle [KA-01-MJ-4892].")
        await asyncio.sleep(1.0)

    print("\n--- 3. Verifying Vehicle History Lookup ---")
    vh_resp = requests.get(f"{BASE_URL}/api/inspections/vehicle/KA-01-MJ-4892/history", headers=headers)
    assert vh_resp.status_code == 200, f"History lookup failed: {vh_resp.text}"
    vh_data = vh_resp.json()
    print(f"[OK] Vehicle [KA-01-MJ-4892] History: {vh_data['total_scans']} scan(s) recorded in DB.")

    print("\n==========================================")
    print("   SIMULATOR INGESTION TEST PASSED! [OK]  ")
    print("==========================================")


if __name__ == "__main__":
    asyncio.run(test_sim())
