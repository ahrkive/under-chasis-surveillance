"""
Multi-Bot Edge Hardware Simulator
=================================
Simulates one or more Raspberry Pi mobile bots streaming undercarriage video frames
and vehicle license plate metadata over WebSocket to the backend.
"""

import os
import io
import time
import json
import random
import hashlib
import asyncio
import argparse
from PIL import Image, ImageDraw, ImageFont
import websockets

MOCK_PLATES = ["KA-01-MJ-4892", "MH-12-AB-1234", "DL-03-CB-9981", "TN-07-BX-5521"]


def generate_synthetic_undercarriage_frame(bot_id: str, frame_num: int, plate: str) -> bytes:
    """Generate synthetic undercarriage inspection image with overlay text."""
    width, height = 640, 480
    bg_color = (30, 35, 45) if frame_num % 2 == 0 else (45, 50, 60)
    img = Image.new("RGB", (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)

    # Draw simulated vehicle chassis rails
    draw.rectangle([100, 100, 540, 140], fill=(80, 85, 95))
    draw.rectangle([100, 340, 540, 380], fill=(80, 85, 95))
    draw.ellipse([260, 180, 380, 300], fill=(60, 65, 75))  # Exhaust / Differential

    # Overlay metadata banner
    draw.rectangle([0, 0, width, 40], fill=(15, 23, 42))
    draw.text((15, 12), f"BOT: {bot_id} | PLATE: {plate} | FRAME #{frame_num}", fill=(52, 211, 153))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


async def simulate_bot(bot_id: str, target_url: str, interval: float, api_key: str = "dev-secret-api-key-12345"):
    endpoint = f"{target_url}/{bot_id}" if not target_url.endswith(bot_id) else target_url
    print(f"🚀 Starting Edge Bot Simulator [{bot_id}] connecting to {endpoint}...")
    frame_seq = 0

    while True:
        try:
            headers = {"x-api-key": api_key}
            async with websockets.connect(endpoint, additional_headers=headers) as ws:
                print(f"✅ [{bot_id}] Connected to WebSocket Hub successfully.")

                while True:
                    frame_seq += 1
                    plate = random.choice(MOCK_PLATES)
                    img_bytes = generate_synthetic_undercarriage_frame(bot_id, frame_seq, plate)

                    # Send JSON header
                    header = {
                        "bot_id": bot_id,
                        "timestamp": time.time(),
                        "sequence": frame_seq,
                        "sha256": hashlib.sha256(img_bytes).hexdigest(),
                        "size": len(img_bytes),
                        "filename": f"{bot_id}_frame_{frame_seq}.jpg",
                        "license_plate": plate,
                    }
                    await ws.send(json.dumps(header))

                    # Send binary JPEG frame payload
                    await ws.send(img_bytes)
                    print(f"📸 [{bot_id}] Sent Frame #{frame_seq} ({len(img_bytes)} bytes) for Vehicle [{plate}]")

                    await asyncio.sleep(interval)
        except Exception as e:
            print(f"⚠️ [{bot_id}] Connection error: {e}. Retrying in 3s...")
            await asyncio.sleep(3.0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-Bot Hardware Simulator")
    parser.add_argument("--bot-id", type=str, default="bot-north-gate", help="Bot ID")
    parser.add_argument("--url", type=str, default="ws://localhost:8000/ws/pi", help="WebSocket URL")
    parser.add_argument("--interval", type=float, default=5.0, help="Stream interval seconds")
    args = parser.parse_args()

    asyncio.run(simulate_bot(args.bot_id, args.url, args.interval))
