"""
WebSocket Hub — Real-Time Image Pipeline
==========================================

Two WebSocket endpoints:
1. /ws/edge/{bot_id}  — Pi bots push images here (API key auth)
2. /ws/guard           — Guard UIs connect here to receive images (JWT auth)

Flow:
  Pi → /ws/edge → create inspection → run inference → push to all /ws/guard clients
"""

import asyncio
import base64
import json
import logging
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import verify_edge_api_key, get_ws_user
from app.config import get_settings
from app.database import get_session_factory
from app.inspections.service import InspectionService
from app.inspections.schemas import ImageHeader, GuardPushMessage

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Connected Guard WebSockets ───────────────────────────────────────────
# Maps WebSocket connection → Guard metadata dict {id, username, full_name, role, connected_at}
_guard_connections: Dict[WebSocket, dict] = {}
_guard_lock = asyncio.Lock()


async def broadcast_to_guards(message: dict) -> None:
    """Send a message to all connected guard UIs."""
    global _guard_connections
    async with _guard_lock:
        disconnected = set()
        for ws in list(_guard_connections.keys()):
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.add(ws)
        for ws in disconnected:
            _guard_connections.pop(ws, None)
        if disconnected:
            logger.info("Cleaned up %d disconnected guard clients.", len(disconnected))


# ── Edge WebSocket (Pi → Server) ────────────────────────────────────────

@router.websocket("/ws/edge/{bot_id}")
async def edge_websocket(websocket: WebSocket, bot_id: str):
    """
    WebSocket endpoint for edge devices (Raspberry Pi bots).

    Protocol:
    1. Receive text frame: JSON header (ImageHeader schema)
    2. Receive binary frame: Raw JPEG bytes
    3. Send text frame: ACK {status: "ok", inspection_id: "..."}
    """
    # Authenticate via API key in headers or query params
    api_key = websocket.headers.get("x-api-key") or websocket.query_params.get("api_key", "")
    if not api_key and get_settings().environment == "development":
        api_key = get_settings().edge_api_key

    if not verify_edge_api_key(api_key):
        logger.warning("Edge WS auth failed for bot_id=%s", bot_id)
        await websocket.close(code=4001, reason="Invalid API key")
        return

    await websocket.accept()
    logger.info("Edge bot connected: %s", bot_id)

    # Import inference service (lazy to avoid circular imports)
    inference_service = None
    try:
        from app.inference.service import get_inference_service
        inference_service = get_inference_service()
    except Exception:
        logger.info("Inference service not available yet. Skipping model predictions.")

    session_factory = get_session_factory()

    try:
        while True:
            # Step 1: Receive JSON header
            header_raw = await websocket.receive_text()
            header = ImageHeader.model_validate_json(header_raw)

            # Step 2: Receive binary image data
            image_data = await websocket.receive_bytes()

            # Validate size matches header
            if len(image_data) != header.size:
                logger.warning(
                    "Image size mismatch: header=%d, actual=%d",
                    header.size, len(image_data),
                )

            logger.info(
                "Received image from %s: seq=%d, size=%d bytes",
                bot_id, header.sequence, len(image_data),
            )

            # Step 3: Run inference (if model available)
            model_prediction = None
            model_confidence = None
            model_version = None

            if inference_service and inference_service.is_loaded:
                try:
                    result = await inference_service.predict(image_data)
                    model_prediction = result["prediction"]
                    model_confidence = result["confidence"]
                    model_version = result["model_version"]
                    logger.info(
                        "Inference: %s (%.1f%% confidence, model v%d)",
                        model_prediction,
                        model_confidence * 100,
                        model_version,
                    )
                except Exception as e:
                    logger.error("Inference failed: %s", e)

            # Step 4: Create inspection record
            async with session_factory() as db:
                inspection = await InspectionService.create_inspection(
                    db=db,
                    image_data=image_data,
                    bot_id=bot_id,
                    timestamp=header.timestamp,
                    sha256=header.sha256,
                    filename=header.filename,
                    model_prediction=model_prediction,
                    model_confidence=model_confidence,
                    model_version=model_version,
                )

                # Step 5: Push to guard UIs
                image_b64 = base64.b64encode(image_data).decode("utf-8")
                guard_msg = GuardPushMessage(
                    type="new_image",
                    inspection_id=inspection.id,
                    image_data_b64=image_b64,
                    model_prediction=model_prediction,
                    model_confidence=model_confidence,
                    model_version=model_version,
                )
                await broadcast_to_guards(guard_msg.model_dump())

            # Step 6: Send ACK to Pi
            ack = {"status": "ok", "inspection_id": inspection.id}
            await websocket.send_text(json.dumps(ack))

    except WebSocketDisconnect:
        logger.info("Edge bot disconnected: %s", bot_id)
    except Exception as e:
        logger.error("Edge WebSocket error for %s: %s", bot_id, e, exc_info=True)
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


# ── Guard WebSocket (Server → Guard UI) ─────────────────────────────────

@router.websocket("/ws/guard")
async def guard_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for guard UI clients.

    Authentication via JWT token in query parameter: ?token=<jwt>
    Receives real-time image pushes and decision confirmations.
    """
    session_factory = get_session_factory()

    # Authenticate guard
    async with session_factory() as db:
        guard = await get_ws_user(websocket, db)

    if not guard:
        logger.warning("Guard WS auth failed.")
        await websocket.close(code=4001, reason="Authentication required")
        return

    await websocket.accept()
    logger.info("Guard connected: %s (%s)", guard.username, guard.full_name)

    # Register this connection for broadcasts + tracking active guards
    import time
    async with _guard_lock:
        _guard_connections[websocket] = {
            "id": guard.id,
            "username": guard.username,
            "full_name": guard.full_name,
            "role": guard.role,
            "connected_at": time.time(),
        }

    try:
        # Keep connection alive; guard sends decisions via REST API
        # but we listen for any client messages (e.g., ping, typing indicators)
        while True:
            msg = await websocket.receive_text()
            # Handle any guard-initiated messages if needed
            try:
                data = json.loads(msg)
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        logger.info("Guard disconnected: %s", guard.username)
    except Exception as e:
        logger.error("Guard WebSocket error: %s", e, exc_info=True)
    finally:
        async with _guard_lock:
            _guard_connections.pop(websocket, None)
        try:
            await websocket.close()
        except Exception:
            pass


def get_connected_guard_count() -> int:
    """Return the number of connected guard clients."""
    return len(_guard_connections)


def get_active_guards_list() -> list[dict]:
    """Return detailed list of currently connected/logged-in guards."""
    return list(_guard_connections.values())
