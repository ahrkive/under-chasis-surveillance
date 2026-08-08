"""
Camera Capture Service
======================
Handles image acquisition from the Raspberry Pi Camera Module v2 (IMX219)
using Picamera2 (libcamera backend).

Falls back to OpenCV VideoCapture for development/testing on non-Pi hardware.
"""

import io
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Try importing Picamera2 (only available on Raspberry Pi) ─────────────
_USE_PICAMERA2 = False
try:
    from picamera2 import Picamera2
    from libcamera import controls  # noqa: F401
    _USE_PICAMERA2 = True
    logger.info("Picamera2 available — using hardware-accelerated capture.")
except ImportError:
    logger.warning(
        "Picamera2 not available. Falling back to OpenCV VideoCapture. "
        "This is expected on non-Pi development machines."
    )

import cv2
import numpy as np


class CameraCapture:
    """
    Captures JPEG-compressed frames from the Pi camera.

    Uses Picamera2 on Raspberry Pi hardware; falls back to OpenCV
    VideoCapture on development machines.
    """

    def __init__(
        self,
        width: int = 640,
        height: int = 480,
        jpeg_quality: int = 85,
        camera_id: int = 0,
    ):
        self.width = width
        self.height = height
        self.jpeg_quality = jpeg_quality
        self.camera_id = camera_id

        self._picam: Optional["Picamera2"] = None
        self._cv_cap: Optional[cv2.VideoCapture] = None
        self._is_running = False
        self._frame_count = 0

    def start(self) -> None:
        """Initialize and start the camera."""
        if self._is_running:
            logger.warning("Camera already running.")
            return

        if _USE_PICAMERA2:
            self._start_picamera2()
        else:
            self._start_opencv()

        self._is_running = True
        self._frame_count = 0
        logger.info(
            "Camera started: %dx%d, JPEG quality=%d, backend=%s",
            self.width, self.height, self.jpeg_quality,
            "Picamera2" if _USE_PICAMERA2 else "OpenCV"
        )

    def _start_picamera2(self) -> None:
        """Initialize Picamera2 with optimized settings for undercarriage capture."""
        self._picam = Picamera2(self.camera_id)

        # Configure for still image capture (high quality, controlled exposure)
        config = self._picam.create_still_configuration(
            main={"size": (self.width, self.height), "format": "RGB888"},
            buffer_count=2,
        )
        self._picam.configure(config)

        # Set controls for consistent capture in variable lighting
        self._picam.set_controls({
            "AwbEnable": True,          # Auto white balance
            "AeEnable": True,           # Auto exposure
            "AfMode": 0,               # Manual focus (fixed for undercarriage distance)
            "ExposureTime": 0,          # 0 = auto
            "AnalogueGain": 1.0,        # Base gain; auto-exposure will adjust
            "Brightness": 0.1,          # Slight brightness boost for dark undercarriages
            "Contrast": 1.2,            # Slight contrast boost
        })

        self._picam.start()
        # Allow auto-exposure to settle
        time.sleep(2.0)
        logger.info("Picamera2 initialized and auto-exposure settled.")

    def _start_opencv(self) -> None:
        """Initialize OpenCV VideoCapture as fallback."""
        self._cv_cap = cv2.VideoCapture(self.camera_id)
        if not self._cv_cap.isOpened():
            raise RuntimeError(
                f"Failed to open camera {self.camera_id} via OpenCV. "
                "Ensure a camera is connected or set EDGE_CAMERA_ID correctly."
            )
        self._cv_cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self._cv_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        logger.info("OpenCV VideoCapture initialized on device %d.", self.camera_id)

    def capture_frame(self) -> Optional[np.ndarray]:
        """
        Capture a single frame as a NumPy array (BGR format for OpenCV,
        converted from RGB for Picamera2).

        Returns:
            np.ndarray: Captured frame in BGR format, or None if capture failed.
        """
        if not self._is_running:
            logger.error("Camera not started. Call start() first.")
            return None

        try:
            if _USE_PICAMERA2:
                # Picamera2 returns RGB; convert to BGR for consistency
                rgb_frame = self._picam.capture_array()
                frame = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)
            else:
                ret, frame = self._cv_cap.read()
                if not ret or frame is None:
                    logger.warning("OpenCV capture returned empty frame.")
                    return None

            self._frame_count += 1
            return frame

        except Exception as e:
            logger.error("Frame capture failed: %s", e, exc_info=True)
            return None

    def capture_jpeg(self) -> Optional[bytes]:
        """
        Capture a frame and compress it to JPEG bytes.

        Returns:
            bytes: JPEG-compressed image data, or None if capture failed.
        """
        frame = self.capture_frame()
        if frame is None:
            return None

        try:
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality]
            success, buffer = cv2.imencode(".jpg", frame, encode_params)
            if not success:
                logger.error("JPEG encoding failed.")
                return None
            return buffer.tobytes()

        except Exception as e:
            logger.error("JPEG encoding error: %s", e, exc_info=True)
            return None

    def stop(self) -> None:
        """Release camera resources."""
        if not self._is_running:
            return

        try:
            if _USE_PICAMERA2 and self._picam:
                self._picam.stop()
                self._picam.close()
                self._picam = None
            elif self._cv_cap:
                self._cv_cap.release()
                self._cv_cap = None
        except Exception as e:
            logger.error("Error stopping camera: %s", e, exc_info=True)
        finally:
            self._is_running = False
            logger.info(
                "Camera stopped. Total frames captured: %d", self._frame_count
            )

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def frame_count(self) -> int:
        return self._frame_count

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False
