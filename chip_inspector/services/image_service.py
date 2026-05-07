"""
Image service - Image processing utilities.
"""
from typing import Optional, List, Dict, Any
from pathlib import Path
import cv2
import numpy as np
from PySide6.QtGui import QPixmap, QImage

from core.exceptions import ImageLoadError
from utils.logger import get_logger


class ImageService:
    """Service for image loading and processing operations."""

    def __init__(self):
        self._logger = get_logger(__name__)

    def load_opencv_image(self, image_path: str) -> Optional[np.ndarray]:
        """
        Load an image using OpenCV.

        Args:
            image_path: Path to image file

        Returns:
            OpenCV image or None if failed
        """
        try:
            arr = np.fromfile(image_path, np.uint8)
            img = cv2.imdecode(arr, -1)
            return img
        except Exception as e:
            self._logger.error(f"Failed to load image {image_path}: {str(e)}")
            return None

    def opencv_to_pixmap(self, img: np.ndarray) -> Optional[QPixmap]:
        """
        Convert OpenCV image to QPixmap.

        Args:
            img: OpenCV image (BGR format)

        Returns:
            QPixmap or None if failed
        """
        try:
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            h, w, c = rgb.shape
            qimage = QImage(rgb.data, w, h, c * w, QImage.Format_RGB888)
            return QPixmap.fromImage(qimage)
        except Exception as e:
            self._logger.error(f"Failed to convert image: {str(e)}")
            return None

    def get_image_info(self, image_path: str) -> Optional[Dict[str, Any]]:
        """
        Get information about an image file.

        Args:
            image_path: Path to image

        Returns:
            Dict with image info or None
        """
        try:
            path = Path(image_path)
            if not path.exists():
                return None

            # Get file info
            info = {
                'name': path.stem,
                'full_name': path.name,
                'size_bytes': path.stat().st_size,
                'extension': path.suffix,
                'path': str(path)
            }

            # Try to get image dimensions
            img = self.load_opencv_image(image_path)
            if img is not None:
                info['width'] = img.shape[1]
                info['height'] = img.shape[0]
                info['channels'] = img.shape[2] if len(img.shape) > 2 else 1

            return info

        except Exception as e:
            self._logger.error(f"Failed to get image info: {str(e)}")
            return None

    def validate_image(self, image_path: str) -> tuple[bool, Optional[str]]:
        """
        Validate an image file.

        Args:
            image_path: Path to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        path = Path(image_path)

        if not path.exists():
            return False, "File does not exist"

        if not path.is_file():
            return False, "Path is not a file"

        # Check extension
        valid_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
        if path.suffix.lower() not in valid_extensions:
            return False, f"Invalid image format: {path.suffix}"

        # Try to load
        img = self.load_opencv_image(image_path)
        if img is None:
            return False, "Failed to load image"

        return True, None

    def resize_image(
        self,
        img: np.ndarray,
        max_width: Optional[int] = None,
        max_height: Optional[int] = None,
        maintain_aspect: bool = True
    ) -> np.ndarray:
        """
        Resize an image.

        Args:
            img: OpenCV image
            max_width: Maximum width
            max_height: Maximum height
            maintain_aspect: Whether to maintain aspect ratio

        Returns:
            Resized image
        """
        h, w = img.shape[:2]

        # Calculate new size
        if maintain_aspect:
            if max_width and w > max_width:
                ratio = max_width / w
                h = int(h * ratio)
                w = max_width
            if max_height and h > max_height:
                ratio = max_height / h
                w = int(w * ratio)
                h = max_height
        else:
            if max_width:
                w = max_width
            if max_height:
                h = max_height

        return cv2.resize(img, (w, h))

    def create_thumbnail(
        self,
        image_path: str,
        size: tuple[int, int] = (150, 150)
    ) -> Optional[QPixmap]:
        """
        Create a thumbnail of an image.

        Args:
            image_path: Path to source image
            size: Thumbnail size (width, height)

        Returns:
            Thumbnail QPixmap or None
        """
        img = self.load_opencv_image(image_path)
        if img is None:
            return None

        resized = self.resize_image(img, size[0], size[1], maintain_aspect=True)
        return self.opencv_to_pixmap(resized)
