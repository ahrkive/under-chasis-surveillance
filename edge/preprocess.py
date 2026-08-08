"""
Image Preprocessing Pipeline
=============================
Applies preprocessing to captured frames before transmission:
- Resize (if camera output differs from target)
- Brightness / contrast normalization
- Optional lens undistortion
- CLAHE adaptive histogram equalization (for undercarriage low-light)
"""

import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """
    Preprocessing pipeline for undercarriage images.

    Designed for the challenging conditions under a vehicle:
    low/uneven lighting, reflections, oil/dirt on surfaces.
    """

    def __init__(
        self,
        target_width: int = 640,
        target_height: int = 480,
        alpha: float = 1.0,
        beta: float = 0.0,
        enable_undistortion: bool = False,
        camera_matrix: np.ndarray | None = None,
        distortion_coeffs: np.ndarray | None = None,
        enable_clahe: bool = True,
        clahe_clip_limit: float = 2.0,
        clahe_grid_size: tuple = (8, 8),
    ):
        """
        Args:
            target_width: Output image width.
            target_height: Output image height.
            alpha: Contrast control (1.0 = no change, >1 = more contrast).
            beta: Brightness offset (0 = no change, >0 = brighter).
            enable_undistortion: Whether to apply lens undistortion.
            camera_matrix: 3x3 camera intrinsic matrix (from calibration).
            distortion_coeffs: Distortion coefficients (from calibration).
            enable_clahe: Whether to apply adaptive histogram equalization.
            clahe_clip_limit: CLAHE clip limit (higher = more contrast).
            clahe_grid_size: CLAHE tile grid size.
        """
        self.target_width = target_width
        self.target_height = target_height
        self.alpha = alpha
        self.beta = beta
        self.enable_undistortion = enable_undistortion
        self.enable_clahe = enable_clahe

        # Prepare undistortion maps (computed once for efficiency)
        self._undistort_map1 = None
        self._undistort_map2 = None
        if enable_undistortion and camera_matrix is not None:
            self._camera_matrix = np.array(camera_matrix, dtype=np.float64)
            self._distortion_coeffs = np.array(distortion_coeffs, dtype=np.float64)
            self._prepare_undistortion_maps()
        elif enable_undistortion:
            logger.warning(
                "Undistortion enabled but no camera matrix provided. Disabling."
            )
            self.enable_undistortion = False

        # Prepare CLAHE instance
        self._clahe = None
        if enable_clahe:
            self._clahe = cv2.createCLAHE(
                clipLimit=clahe_clip_limit,
                tileGridSize=clahe_grid_size,
            )

        logger.info(
            "Preprocessor initialized: %dx%d, alpha=%.2f, beta=%.1f, "
            "undistort=%s, CLAHE=%s",
            target_width, target_height, alpha, beta,
            enable_undistortion, enable_clahe,
        )

    def _prepare_undistortion_maps(self) -> None:
        """Pre-compute undistortion remap tables for fast application."""
        h, w = self.target_height, self.target_width
        new_camera_matrix, _ = cv2.getOptimalNewCameraMatrix(
            self._camera_matrix,
            self._distortion_coeffs,
            (w, h),
            alpha=1,  # Keep all pixels
            newImgSize=(w, h),
        )
        self._undistort_map1, self._undistort_map2 = cv2.initUndistortRectifyMap(
            self._camera_matrix,
            self._distortion_coeffs,
            None,
            new_camera_matrix,
            (w, h),
            cv2.CV_16SC2,
        )
        logger.info("Undistortion maps pre-computed.")

    def process(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply the full preprocessing pipeline to a frame.

        Args:
            frame: Input BGR image (NumPy array).

        Returns:
            Preprocessed BGR image.
        """
        if frame is None or frame.size == 0:
            raise ValueError("Empty frame received for preprocessing.")

        result = frame.copy()

        # Step 1: Resize if dimensions differ
        h, w = result.shape[:2]
        if w != self.target_width or h != self.target_height:
            result = cv2.resize(
                result,
                (self.target_width, self.target_height),
                interpolation=cv2.INTER_AREA if w > self.target_width else cv2.INTER_LINEAR,
            )

        # Step 2: Lens undistortion
        if self.enable_undistortion and self._undistort_map1 is not None:
            result = cv2.remap(
                result,
                self._undistort_map1,
                self._undistort_map2,
                cv2.INTER_LINEAR,
            )

        # Step 3: Brightness / contrast adjustment
        if self.alpha != 1.0 or self.beta != 0.0:
            result = cv2.convertScaleAbs(result, alpha=self.alpha, beta=self.beta)

        # Step 4: CLAHE (Adaptive Histogram Equalization)
        # Applied to the L channel in LAB color space to normalize
        # lighting without distorting colors
        if self.enable_clahe and self._clahe is not None:
            result = self._apply_clahe(result)

        return result

    def _apply_clahe(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply CLAHE on the L channel of LAB color space.
        This normalizes lighting while preserving color information —
        crucial for undercarriage images with uneven illumination.
        """
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)
        l_channel = self._clahe.apply(l_channel)
        lab = cv2.merge([l_channel, a_channel, b_channel])
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    def encode_jpeg(self, frame: np.ndarray, quality: int = 85) -> bytes:
        """
        Encode a preprocessed frame to JPEG bytes.

        Args:
            frame: Preprocessed BGR image.
            quality: JPEG compression quality (1-100).

        Returns:
            JPEG-compressed image as bytes.
        """
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
        success, buffer = cv2.imencode(".jpg", frame, encode_params)
        if not success:
            raise RuntimeError("JPEG encoding failed.")
        return buffer.tobytes()
