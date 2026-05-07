"""
HSV-based chip defect detection algorithm.
Detects dark/stain defects on chip surfaces using HSV color segmentation.
"""
import time
from pathlib import Path
from typing import Dict, Any, Optional

import cv2
import numpy as np
from PySide6.QtGui import QPixmap, QImage

from core.enums import DetectionStatus
from core.exceptions import AlgorithmError, ImageLoadError
from .base import BaseDetector, DetectionResult
from .registry import AlgorithmRegistry


class HSVDetector(BaseDetector):
    """
    HSV-based chip defect detector.

    Detection process:
    1. Chip localization: HSV color filtering to find chip region
    2. Safe zone definition: Erode chip contour by margin pixels
    3. Defect detection: Find dark areas within safe zone
    4. Decision: NG if total defect area > threshold
    """

    @property
    def algorithm_id(self) -> str:
        return "hsv_detector"

    @property
    def algorithm_name(self) -> str:
        return "HSV缺陷检测器"

    @property
    def algorithm_description(self) -> str:
        return "基于HSV色彩空间的芯片表面缺陷检测算法"

    def get_default_parameters(self) -> Dict[str, Any]:
        """Get default HSV detection parameters."""
        return {
            'h_min': 100,
            'h_max': 130,
            's_min': 90,
            'v_min': 50,
            'v_max': 255,
            's_max': 255,
            'stain_v_thresh': 100,
            'max_total_area': 150,
            'safe_margin': 15,
            'min_blob': 5
        }

    def get_parameter_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Get parameter definitions with validation rules."""
        return {
            'h_min': {
                'display_name': 'H 下限',
                'type': 'int',
                'min': 0,
                'max': 180,
                'default': 100,
                'step': 1,
                'unit': '',
                'description': '芯片检测色相下限',
                'color_code': '#FF6D00'
            },
            'h_max': {
                'display_name': 'H 上限',
                'type': 'int',
                'min': 0,
                'max': 180,
                'default': 130,
                'step': 1,
                'unit': '',
                'description': '芯片检测色相上限',
                'color_code': '#FF6D00'
            },
            's_min': {
                'display_name': 'S 下限',
                'type': 'int',
                'min': 0,
                'max': 255,
                'default': 90,
                'step': 1,
                'unit': '',
                'description': '芯片检测饱和度下限',
                'color_code': '#FF6D00'
            },
            'v_min': {
                'display_name': 'V 下限',
                'type': 'int',
                'min': 0,
                'max': 255,
                'default': 50,
                'step': 1,
                'unit': '',
                'description': '芯片检测明度下限',
                'color_code': '#FF6D00'
            },
            'v_max': {
                'display_name': 'V 上限',
                'type': 'int',
                'min': 0,
                'max': 255,
                'default': 255,
                'step': 1,
                'unit': '',
                'description': '芯片检测明度上限',
                'color_code': '#FF6D00'
            },
            's_max': {
                'display_name': 'S 上限',
                'type': 'int',
                'min': 0,
                'max': 255,
                'default': 255,
                'step': 1,
                'unit': '',
                'description': '芯片检测饱和度上限',
                'color_code': '#FF6D00'
            },
            'safe_margin': {
                'display_name': '边缘内缩',
                'type': 'int',
                'min': 0,
                'max': 50,
                'default': 15,
                'step': 1,
                'unit': 'px',
                'description': '安全区边缘内缩距离',
                'color_code': '#00B0FF'
            },
            'stain_v_thresh': {
                'display_name': '亮度阈值',
                'type': 'int',
                'min': 1,
                'max': 255,
                'default': 100,
                'step': 1,
                'unit': '',
                'description': '缺陷检测亮度阈值',
                'color_code': '#D50000'
            },
            'min_blob': {
                'display_name': '忽略噪点',
                'type': 'int',
                'min': 0,
                'max': 50,
                'default': 5,
                'step': 1,
                'unit': 'px²',
                'description': '最小噪点面积（忽略小于此值）',
                'color_code': '#D50000'
            },
            'max_total_area': {
                'display_name': '允许面积',
                'type': 'int',
                'min': 10,
                'max': 2000,
                'default': 150,
                'step': 10,
                'unit': 'px²',
                'description': '最大允许缺陷总面积',
                'color_code': '#D50000'
            }
        }

    def detect(self, image_path: str, **kwargs) -> DetectionResult:
        """
        Run HSV-based defect detection on an image.

        Args:
            image_path: Path to the image file
            **kwargs: Optional override parameters

        Returns:
            DetectionResult with status, images, and metadata

        Raises:
            ImageLoadError: If image cannot be loaded
            AlgorithmError: If detection fails
        """
        start_time = time.time()

        # Load image
        img = self._load_opencv_image(image_path)
        if img is None:
            raise ImageLoadError(f"Cannot load image: {image_path}")

        # Get parameters (kwargs override current settings)
        params = self.get_parameters()
        params.update(kwargs)

        # Run detection
        result = self._detect_internal(img, params)

        # Add timing
        processing_time = (time.time() - start_time) * 1000  # ms
        result.processing_time_ms = processing_time

        return result

    def _load_opencv_image(self, image_path: str) -> Optional[np.ndarray]:
        """Load an image using OpenCV."""
        try:
            arr = np.fromfile(image_path, np.uint8)
            img = cv2.imdecode(arr, -1)
            return img
        except Exception as e:
            raise ImageLoadError(f"Failed to load {image_path}: {str(e)}")

    def _detect_internal(self, img: np.ndarray, params: Dict[str, Any]) -> DetectionResult:
        """Internal detection logic."""
        h, w = img.shape[:2]
        vis = img.copy()

        # Convert to HSV
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # Step 1: Find chip region
        mask_chip = cv2.inRange(
            hsv,
            np.array([params['h_min'], params['s_min'], params['v_min']]),
            np.array([params['h_max'], params['s_max'], params['v_max']])
        )
        mask_chip = cv2.morphologyEx(
            mask_chip,
            cv2.MORPH_CLOSE,
            np.ones((7, 7), np.uint8)
        )

        contours, _ = cv2.findContours(
            mask_chip,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        # Step 2: Create safe zone
        mask_safe = np.zeros((h, w), np.uint8)

        if contours:
            max_contour = max(contours, key=cv2.contourArea)

            # Draw filled contour
            mask_solid = np.zeros((h, w), np.uint8)
            cv2.drawContours(mask_solid, [max_contour], -1, 255, -1)

            # Erode to create safe zone
            margin = int(params['safe_margin'])
            if margin > 0:
                mask_safe = cv2.erode(mask_solid, np.ones((margin, margin), np.uint8))
            else:
                mask_safe = mask_solid

            # Visualize chip boundary
            cv2.drawContours(vis, [max_contour], -1, (255, 0, 0), 2, cv2.LINE_AA)

            # Visualize safe zone
            safe_contours, _ = cv2.findContours(
                mask_safe,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )
            cv2.drawContours(vis, safe_contours, -1, (0, 255, 255), 1, cv2.LINE_AA)

        # Step 3: Find dark areas (defects)
        mask_dark = cv2.inRange(hsv[:, :, 2], 0, params['stain_v_thresh'])
        mask_final = cv2.bitwise_and(mask_dark, mask_dark, mask=mask_safe)

        defect_contours, _ = cv2.findContours(
            mask_final,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        # Step 4: Calculate defect area
        total_area = 0
        valid_defects = []

        for contour in defect_contours:
            area = cv2.contourArea(contour)
            if area >= params['min_blob']:
                total_area += area
                valid_defects.append(contour)

        # Step 5: Make decision
        is_ok = total_area <= params['max_total_area']
        status = DetectionStatus.OK if is_ok else DetectionStatus.NG

        # Visualize result
        if not is_ok:
            # Draw defects in red
            cv2.drawContours(vis, valid_defects, -1, (0, 0, 255), -1)
            cv2.drawContours(vis, valid_defects, -1, (0, 255, 255), 1)
            cv2.putText(
                vis,
                f"NG: {int(total_area)}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 0, 255),
                2
            )
        else:
            cv2.putText(
                vis,
                "PASS",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 255, 0),
                2
            )

        # Convert images to QPixmap
        original_pixmap = self._cv2_to_pixmap(img)
        result_pixmap = self._cv2_to_pixmap(vis)

        # Metadata
        metadata = {
            'defect_count': len(valid_defects),
            'image_size': (w, h),
            'chip_found': len(contours) > 0
        }

        return DetectionResult(
            status=status,
            defect_area=total_area,
            original_image=original_pixmap,
            result_image=result_pixmap,
            metadata=metadata
        )

    def _cv2_to_pixmap(self, img: np.ndarray) -> QPixmap:
        """Convert OpenCV image to QPixmap."""
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w, c = rgb.shape
        qimage = QImage(rgb.data, w, h, c * w, QImage.Format_RGB888)
        return QPixmap.fromImage(qimage)


# Register the algorithm
AlgorithmRegistry.register(HSVDetector)
