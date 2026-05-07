"""
Canvas widget for high-performance image display.
Supports zoom, pan, and image overlay visualization.
"""
from typing import Optional
from PySide6.QtWidgets import QWidget, QLabel, QSizePolicy
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QPixmap, QImage, QColor, QWheelEvent, QPaintEvent

from core.constants import ZOOM_MIN, ZOOM_MAX, ZOOM_STEP
from utils.logger import get_logger


class CanvasWidget(QWidget):
    """
    High-performance image display widget.

    Features:
    - GPU-accelerated rendering with QPainter
    - Mouse wheel zoom (0.1x to 10x)
    - Auto-fit to window
    - Always centered on black background
    - Fixed widget size (layout-friendly)
    - Zoom level indicator
    """

    def __init__(
        self,
        placeholder_text: str = "NO SIGNAL",
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)

        self._logger = get_logger(__name__)
        self._pixmap: Optional[QPixmap] = None
        self._scale = 1.0
        self._placeholder_text = placeholder_text

        # Setup widget
        self.setMinimumSize(350, 350)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        self.setMouseTracking(True)

    def set_pixmap(self, pixmap: Optional[QPixmap]) -> None:
        """Set the image to display."""
        self._pixmap = pixmap
        self.fit_to_window()
        self.update()

    def clear(self) -> None:
        """Clear the displayed image."""
        self._pixmap = None
        self._scale = 1.0
        self.update()

    def fit_to_window(self) -> None:
        """Fit the image to the current widget size."""
        if self._pixmap and not self._pixmap.isNull():
            ratio_w = self.width() / self._pixmap.width()
            ratio_h = self.height() / self._pixmap.height()
            self._scale = min(ratio_w, ratio_h) * 0.95

    def reset_zoom(self) -> None:
        """Reset zoom to fit window."""
        self.fit_to_window()
        self.update()

    def zoom_in(self) -> None:
        """Zoom in by step factor."""
        if self._pixmap is None:
            return
        new_scale = self._scale * ZOOM_STEP
        if new_scale <= ZOOM_MAX:
            self._scale = new_scale
            self.update()

    def zoom_out(self) -> None:
        """Zoom out by step factor."""
        if self._pixmap is None:
            return
        new_scale = self._scale / ZOOM_STEP
        if new_scale >= ZOOM_MIN:
            self._scale = new_scale
            self.update()

    def set_zoom(self, zoom: float) -> None:
        """Set zoom level directly."""
        if ZOOM_MIN <= zoom <= ZOOM_MAX:
            self._scale = zoom
            self.update()

    def get_zoom(self) -> float:
        """Get current zoom level."""
        return self._scale

    def paintEvent(self, event: QPaintEvent) -> None:
        """Paint the widget."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Background
        painter.fillRect(self.rect(), QColor("#000000"))
        painter.setPen(QColor("#333333"))
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)

        if self._pixmap and not self._pixmap.isNull():
            # Calculate centered position
            target_w = self._pixmap.width() * self._scale
            target_h = self._pixmap.height() * self._scale
            x = (self.width() - target_w) / 2
            y = (self.height() - target_h) / 2

            target_rect = QRectF(x, y, target_w, target_h)
            painter.drawPixmap(target_rect, self._pixmap, QRectF(self._pixmap.rect()))

            # Zoom indicator
            painter.setPen(QColor("#00B0FF"))
            font = painter.font()
            painter.setFont(font)
            painter.drawText(10, 20, f"Zoom: {self._scale:.2f}x")
        else:
            # Placeholder
            painter.setPen(QColor("#555555"))
            font = painter.font()
            font.setPointSize(14)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignCenter, self._placeholder_text)

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Handle mouse wheel for zooming."""
        if self._pixmap is None:
            return

        angle = event.angleDelta().y()
        if angle > 0:
            self.zoom_in()
        else:
            self.zoom_out()

    def resizeEvent(self, event) -> None:
        """Handle resize events."""
        super().resizeEvent(event)
        # Optionally auto-fit on resize
        # self.fit_to_window()
