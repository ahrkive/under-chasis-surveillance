"""
Edge Configuration — Raspberry Pi Side
=======================================
Loads settings from environment variables or .env file.
All capture, preprocessing, networking, and buffer parameters
are centralized here.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class EdgeConfig:
    """Configuration for the Raspberry Pi edge device."""

    # ── Identity ─────────────────────────────────────────────────────────
    bot_id: str = "bot-001"

    # ── Server Connection ────────────────────────────────────────────────
    server_ws_url: str = "ws://localhost:8000/ws/edge/bot-001"
    api_key: str = "change-me-to-a-secure-key"
    http_fallback_url: str = "http://localhost:8000/api/inspections/upload"

    # ── Camera Capture ───────────────────────────────────────────────────
    capture_interval_sec: float = 2.0
    image_quality: int = 85          # JPEG quality (1-100)
    image_width: int = 640           # Capture / resize width
    image_height: int = 480          # Capture / resize height
    camera_id: int = 0               # /dev/video<N> or CSI camera index

    # ── Preprocessing ────────────────────────────────────────────────────
    enable_undistortion: bool = False
    # Camera matrix and distortion coefficients (OpenCV format)
    # Set these from a calibration run; defaults are identity (no distortion)
    camera_matrix: list = field(default_factory=lambda: [
        [600, 0, 320],
        [0, 600, 240],
        [0, 0, 1]
    ])
    distortion_coeffs: list = field(default_factory=lambda: [0, 0, 0, 0, 0])
    brightness_alpha: float = 1.0    # Contrast multiplier (1.0 = no change)
    brightness_beta: float = 0.0     # Brightness offset (0 = no change)

    # ── Local Buffer ─────────────────────────────────────────────────────
    buffer_dir: str = "./buffer"
    max_buffer_size_mb: int = 500
    buffer_db_path: str = ""         # Auto-set to buffer_dir/outbox.db

    # ── Networking ───────────────────────────────────────────────────────
    ws_reconnect_base_delay: float = 1.0   # Initial reconnect delay (seconds)
    ws_reconnect_max_delay: float = 60.0   # Max reconnect delay (seconds)
    ws_ping_interval: float = 20.0         # WebSocket keepalive ping interval
    ws_ping_timeout: float = 10.0          # WebSocket ping response timeout
    http_timeout: float = 30.0             # HTTP fallback request timeout

    # ── Logging ──────────────────────────────────────────────────────────
    log_level: str = "INFO"

    def __post_init__(self):
        """Derive computed fields and ensure directories exist."""
        if not self.buffer_db_path:
            self.buffer_db_path = str(Path(self.buffer_dir) / "outbox.db")

        # Ensure buffer directory exists
        Path(self.buffer_dir).mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(cls) -> "EdgeConfig":
        """
        Load configuration from environment variables.
        Falls back to defaults for any unset variable.
        """
        def _bool(val: str) -> bool:
            return val.lower() in ("true", "1", "yes")

        kwargs = {}
        env_map = {
            "EDGE_BOT_ID": ("bot_id", str),
            "EDGE_SERVER_URL": ("server_ws_url", str),
            "EDGE_API_KEY": ("api_key", str),
            "EDGE_HTTP_FALLBACK_URL": ("http_fallback_url", str),
            "EDGE_CAPTURE_INTERVAL_SEC": ("capture_interval_sec", float),
            "EDGE_IMAGE_QUALITY": ("image_quality", int),
            "EDGE_IMAGE_WIDTH": ("image_width", int),
            "EDGE_IMAGE_HEIGHT": ("image_height", int),
            "EDGE_ENABLE_UNDISTORTION": ("enable_undistortion", _bool),
            "EDGE_BRIGHTNESS_ALPHA": ("brightness_alpha", float),
            "EDGE_BRIGHTNESS_BETA": ("brightness_beta", float),
            "EDGE_BUFFER_DIR": ("buffer_dir", str),
            "EDGE_MAX_BUFFER_SIZE_MB": ("max_buffer_size_mb", int),
            "LOG_LEVEL": ("log_level", str),
        }

        for env_var, (field_name, converter) in env_map.items():
            value = os.environ.get(env_var)
            if value is not None:
                try:
                    kwargs[field_name] = converter(value)
                except (ValueError, TypeError):
                    pass  # Keep default if conversion fails

        return cls(**kwargs)


# ── Singleton instance ───────────────────────────────────────────────────
_config: EdgeConfig | None = None


def get_config() -> EdgeConfig:
    """Get or create the singleton configuration instance."""
    global _config
    if _config is None:
        _config = EdgeConfig.from_env()
    return _config
