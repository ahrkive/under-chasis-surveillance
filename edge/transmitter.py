"""
Image Transmitter — WebSocket Client + HTTP Fallback
=====================================================
Drains the local buffer queue and transmits images to the backend server.

Protocol (WebSocket, binary-efficient):
1. Send text frame: JSON header {bot_id, timestamp, seq, sha256, size}
2. Send binary frame: Raw JPEG bytes
3. Wait for text frame: Server ACK {status: "ok", inspection_id: "..."}

If WebSocket fails, falls back to HTTP POST multipart upload.
Implements exponential backoff on connection failures.
"""

import asyncio
import json
import logging
import time
from typing import Optional

import aiohttp

from buffer import ImageBuffer, BufferEntry
from config import EdgeConfig

logger = logging.getLogger(__name__)


class ImageTransmitter:
    """
    Asynchronous image transmitter that drains the local buffer queue
    and sends images to the backend over WebSocket (preferred) or HTTP (fallback).
    """

    def __init__(self, config: EdgeConfig, buffer: ImageBuffer):
        self.config = config
        self.buffer = buffer

        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._sequence_number: int = 0
        self._reconnect_delay: float = config.ws_reconnect_base_delay
        self._is_running: bool = False
        self._stats = {
            "sent_ws": 0,
            "sent_http": 0,
            "failed": 0,
            "reconnects": 0,
        }

    async def start(self) -> None:
        """Start the transmitter loop."""
        self._is_running = True
        self._session = aiohttp.ClientSession()
        logger.info("Transmitter started. Server: %s", self.config.server_ws_url)

        try:
            while self._is_running:
                await self._transmit_loop()
        except asyncio.CancelledError:
            logger.info("Transmitter cancelled.")
        finally:
            await self._cleanup()

    async def _transmit_loop(self) -> None:
        """Main transmit loop: connect, drain queue, handle disconnects."""
        # Try WebSocket connection
        connected = await self._connect_ws()

        if connected:
            self._reconnect_delay = self.config.ws_reconnect_base_delay
            await self._drain_queue_ws()
        else:
            # WebSocket failed — try HTTP fallback for any queued images
            await self._drain_queue_http()

            # Backoff before next reconnect attempt
            logger.info(
                "Reconnecting in %.1fs... (attempt %d)",
                self._reconnect_delay, self._stats["reconnects"] + 1,
            )
            await asyncio.sleep(self._reconnect_delay)
            self._reconnect_delay = min(
                self._reconnect_delay * 2,
                self.config.ws_reconnect_max_delay,
            )
            self._stats["reconnects"] += 1

    async def _connect_ws(self) -> bool:
        """Attempt to establish a WebSocket connection to the server."""
        try:
            headers = {
                "X-Api-Key": self.config.api_key,
                "X-Bot-Id": self.config.bot_id,
            }
            self._ws = await self._session.ws_connect(
                self.config.server_ws_url,
                headers=headers,
                heartbeat=self.config.ws_ping_interval,
                receive_timeout=self.config.ws_ping_timeout,
            )
            logger.info("WebSocket connected to %s", self.config.server_ws_url)
            return True

        except Exception as e:
            logger.warning("WebSocket connection failed: %s", e)
            self._ws = None
            return False

    async def _drain_queue_ws(self) -> None:
        """Send all queued images over WebSocket."""
        while self._is_running:
            entries = self.buffer.peek(count=1)
            if not entries:
                # No images to send; wait briefly then check again
                await asyncio.sleep(0.5)
                continue

            entry = entries[0]
            image_data = self.buffer.get_image_data(entry)
            if image_data is None:
                continue  # Entry was cleaned up (missing file)

            success = await self._send_ws(entry, image_data)
            if success:
                self.buffer.mark_sent(entry.id)
                self._stats["sent_ws"] += 1
                logger.info(
                    "Sent via WS: %s (%d bytes) | Queue: %d remaining",
                    entry.filename, entry.size_bytes, self.buffer.queue_size(),
                )
            else:
                self.buffer.mark_failed(entry.id)
                self._stats["failed"] += 1
                # WebSocket likely broken; exit to reconnect
                break

    async def _send_ws(self, entry: BufferEntry, image_data: bytes) -> bool:
        """
        Send a single image over WebSocket using the binary protocol.

        Returns:
            True if the server acknowledged successfully.
        """
        if self._ws is None or self._ws.closed:
            return False

        try:
            self._sequence_number += 1

            # Step 1: Send JSON header (text frame)
            header = {
                "bot_id": self.config.bot_id,
                "timestamp": entry.created_at,
                "sequence": self._sequence_number,
                "sha256": entry.sha256,
                "size": entry.size_bytes,
                "filename": entry.filename,
            }
            await self._ws.send_str(json.dumps(header))

            # Step 2: Send image data (binary frame)
            await self._ws.send_bytes(image_data)

            # Step 3: Wait for server ACK (with timeout)
            try:
                ack_msg = await asyncio.wait_for(
                    self._ws.receive(), timeout=10.0
                )
                if ack_msg.type == aiohttp.WSMsgType.TEXT:
                    ack = json.loads(ack_msg.data)
                    if ack.get("status") == "ok":
                        return True
                    else:
                        logger.warning("Server NACK: %s", ack)
                        return False
                elif ack_msg.type in (
                    aiohttp.WSMsgType.CLOSE,
                    aiohttp.WSMsgType.CLOSING,
                    aiohttp.WSMsgType.CLOSED,
                    aiohttp.WSMsgType.ERROR,
                ):
                    logger.warning("WebSocket closed during ACK wait.")
                    return False
            except asyncio.TimeoutError:
                logger.warning("ACK timeout for %s", entry.filename)
                return False

        except Exception as e:
            logger.error("WebSocket send error: %s", e, exc_info=True)
            return False

    async def _drain_queue_http(self) -> None:
        """
        Fallback: send queued images via HTTP POST multipart upload.
        Only attempts a batch (max 5) to avoid blocking the reconnect loop.
        """
        entries = self.buffer.peek(count=5)
        if not entries:
            return

        for entry in entries:
            image_data = self.buffer.get_image_data(entry)
            if image_data is None:
                continue

            success = await self._send_http(entry, image_data)
            if success:
                self.buffer.mark_sent(entry.id)
                self._stats["sent_http"] += 1
                logger.info("Sent via HTTP fallback: %s", entry.filename)
            else:
                self.buffer.mark_failed(entry.id)
                self._stats["failed"] += 1
                break  # Server likely unreachable; stop trying

    async def _send_http(self, entry: BufferEntry, image_data: bytes) -> bool:
        """Send a single image via HTTP POST multipart/form-data."""
        try:
            headers = {
                "X-Api-Key": self.config.api_key,
                "X-Bot-Id": self.config.bot_id,
            }
            data = aiohttp.FormData()
            data.add_field(
                "image",
                image_data,
                filename=entry.filename,
                content_type="image/jpeg",
            )
            data.add_field("sha256", entry.sha256)
            data.add_field("timestamp", str(entry.created_at))
            data.add_field("bot_id", self.config.bot_id)

            async with self._session.post(
                self.config.http_fallback_url,
                headers=headers,
                data=data,
                timeout=aiohttp.ClientTimeout(total=self.config.http_timeout),
            ) as resp:
                if resp.status == 200:
                    return True
                else:
                    body = await resp.text()
                    logger.warning(
                        "HTTP fallback failed: status=%d, body=%s",
                        resp.status, body[:200],
                    )
                    return False

        except Exception as e:
            logger.warning("HTTP fallback error: %s", e)
            return False

    async def stop(self) -> None:
        """Gracefully stop the transmitter."""
        self._is_running = False

        if self._ws and not self._ws.closed:
            await self._ws.close()

        logger.info(
            "Transmitter stopped. Stats: sent_ws=%d, sent_http=%d, failed=%d, reconnects=%d",
            self._stats["sent_ws"],
            self._stats["sent_http"],
            self._stats["failed"],
            self._stats["reconnects"],
        )

    async def _cleanup(self) -> None:
        """Clean up resources."""
        if self._ws and not self._ws.closed:
            await self._ws.close()
        if self._session and not self._session.closed:
            await self._session.close()

    @property
    def stats(self) -> dict:
        return self._stats.copy()
