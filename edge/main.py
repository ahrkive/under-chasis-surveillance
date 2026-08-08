"""
Edge Main — Entry Point for Raspberry Pi Inspection Bot
========================================================
Orchestrates: Camera Capture → Preprocessing → Buffer → Transmission

Runs two concurrent async tasks:
1. Capture loop: captures frames at configured interval → preprocesses → enqueues
2. Transmitter loop: drains buffer queue → sends to server

Handles graceful shutdown on SIGINT/SIGTERM.
"""

import asyncio
import logging
import signal
import sys
import time
from pathlib import Path

import numpy as np

# Add edge directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import get_config, EdgeConfig
from capture import CameraCapture
from preprocess import ImagePreprocessor
from buffer import ImageBuffer
from transmitter import ImageTransmitter


def setup_logging(level: str = "INFO") -> None:
    """Configure structured logging."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-7s | %(name)-20s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("edge.log", mode="a"),
        ],
    )


logger = logging.getLogger("edge.main")


class InspectionBot:
    """
    Main orchestrator for the inspection bot edge device.

    Manages the capture → preprocess → buffer → transmit pipeline
    as concurrent async tasks.
    """

    def __init__(self, config: EdgeConfig):
        self.config = config
        self._shutdown_event = asyncio.Event()

        # Initialize components
        self.camera = CameraCapture(
            width=config.image_width,
            height=config.image_height,
            jpeg_quality=config.image_quality,
            camera_id=config.camera_id,
        )

        self.preprocessor = ImagePreprocessor(
            target_width=config.image_width,
            target_height=config.image_height,
            alpha=config.brightness_alpha,
            beta=config.brightness_beta,
            enable_undistortion=config.enable_undistortion,
            camera_matrix=np.array(config.camera_matrix) if config.enable_undistortion else None,
            distortion_coeffs=np.array(config.distortion_coeffs) if config.enable_undistortion else None,
        )

        self.buffer = ImageBuffer(
            buffer_dir=config.buffer_dir,
            db_path=config.buffer_db_path,
            max_size_mb=config.max_buffer_size_mb,
        )

        self.transmitter = ImageTransmitter(
            config=config,
            buffer=self.buffer,
        )

    async def capture_loop(self) -> None:
        """
        Continuous capture loop: capture → preprocess → enqueue to buffer.
        Runs at the configured capture interval.
        """
        logger.info(
            "Capture loop started. Interval: %.1fs",
            self.config.capture_interval_sec,
        )
        capture_count = 0

        while not self._shutdown_event.is_set():
            loop_start = time.monotonic()

            try:
                # Capture a frame
                frame = self.camera.capture_frame()
                if frame is None:
                    logger.warning("Skipping frame: capture returned None.")
                    await asyncio.sleep(1.0)
                    continue

                # Preprocess
                processed = self.preprocessor.process(frame)

                # Encode to JPEG
                jpeg_data = self.preprocessor.encode_jpeg(
                    processed, quality=self.config.image_quality
                )

                # Enqueue to local buffer
                entry = self.buffer.enqueue(jpeg_data, bot_id=self.config.bot_id)
                capture_count += 1

                if capture_count % 10 == 0:
                    logger.info(
                        "Capture stats: count=%d, buffer_queue=%d, buffer_size=%.1fMB",
                        capture_count,
                        self.buffer.queue_size(),
                        self.buffer.total_size_bytes() / (1024 * 1024),
                    )

            except Exception as e:
                logger.error("Capture loop error: %s", e, exc_info=True)

            # Maintain consistent capture interval
            elapsed = time.monotonic() - loop_start
            sleep_time = max(0, self.config.capture_interval_sec - elapsed)
            try:
                await asyncio.wait_for(
                    self._shutdown_event.wait(), timeout=sleep_time
                )
                break  # Shutdown event was set
            except asyncio.TimeoutError:
                pass  # Normal: timeout means we should capture next frame

        logger.info("Capture loop stopped. Total captures: %d", capture_count)

    async def buffer_cleanup_loop(self) -> None:
        """Periodically clean up old sent entries from the buffer."""
        while not self._shutdown_event.is_set():
            try:
                self.buffer.cleanup_sent(max_age_hours=24)
            except Exception as e:
                logger.error("Buffer cleanup error: %s", e)

            # Run cleanup every hour
            try:
                await asyncio.wait_for(
                    self._shutdown_event.wait(), timeout=3600
                )
                break
            except asyncio.TimeoutError:
                pass

    async def run(self) -> None:
        """
        Start all concurrent tasks and run until shutdown.
        """
        logger.info("=" * 60)
        logger.info("INSPECTION BOT STARTING")
        logger.info("  Bot ID:     %s", self.config.bot_id)
        logger.info("  Server:     %s", self.config.server_ws_url)
        logger.info("  Resolution: %dx%d", self.config.image_width, self.config.image_height)
        logger.info("  Interval:   %.1fs", self.config.capture_interval_sec)
        logger.info("  Buffer:     %s", self.config.buffer_dir)
        logger.info("=" * 60)

        # Start camera
        self.camera.start()

        # Create concurrent tasks
        tasks = [
            asyncio.create_task(self.capture_loop(), name="capture"),
            asyncio.create_task(self.transmitter.start(), name="transmitter"),
            asyncio.create_task(self.buffer_cleanup_loop(), name="cleanup"),
        ]

        try:
            # Wait until any task completes (usually means an error)
            # or shutdown event is set
            done, pending = await asyncio.wait(
                tasks, return_when=asyncio.FIRST_COMPLETED
            )

            # Check for exceptions in completed tasks
            for task in done:
                if task.exception():
                    logger.error(
                        "Task '%s' failed: %s",
                        task.get_name(),
                        task.exception(),
                    )

        except asyncio.CancelledError:
            logger.info("Main run cancelled.")

        finally:
            await self.shutdown(tasks)

    async def shutdown(self, tasks: list = None) -> None:
        """Graceful shutdown: stop all components in order."""
        logger.info("Initiating graceful shutdown...")

        self._shutdown_event.set()

        # Stop transmitter first (flush pending sends)
        await self.transmitter.stop()

        # Cancel remaining tasks
        if tasks:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

        # Stop camera
        self.camera.stop()

        # Close buffer DB
        self.buffer.close()

        logger.info("Shutdown complete.")


def main():
    """Entry point."""
    # Load configuration
    config = get_config()
    setup_logging(config.log_level)

    # Create bot instance
    bot = InspectionBot(config)

    # Set up signal handlers for graceful shutdown
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def signal_handler(sig):
        logger.info("Received signal %s. Shutting down...", sig)
        bot._shutdown_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            signal.signal(sig, lambda s, f, _sig=sig: signal_handler(_sig))

    try:
        loop.run_until_complete(bot.run())
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received.")
        loop.run_until_complete(bot.shutdown())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
