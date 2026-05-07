"""
Industrial status indicator widget.
High-contrast display for detection status with optional flashing and audio feedback.
"""
from typing import Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt, QTimer, Signal, Property
from PySide6.QtGui import QPainter, QColor, QFont, QPaintEvent

from core.enums import DetectionStatus
from core.constants import COLOR_OK, COLOR_NG, COLOR_WARNING, COLOR_INFO, COLOR_READY, COLOR_RUNNING
from utils.logger import get_logger


class StatusIndicator(QWidget):
    """
    Industrial-grade status display widget.

    Features:
    - Large font display (60px+)
    - High contrast colors
    - Optional flashing animation for NG state
    - Status states: READY, RUNNING, OK, NG, WARNING, ERROR
    - Touch-friendly size
    """

    status_changed = Signal(str)

    def __init__(
        self,
        min_height: int = 100,
        font_size: int = 60,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)

        self._logger = get_logger(__name__)
        self._status = "READY"
        self._display_text = "READY"
        self._bg_color = QColor(COLOR_READY)
        self._text_color = QColor("#FFFFFF")
        self._font_size = font_size

        # Flash animation
        self._flashing = False
        self._flash_state = False
        self._flash_timer = QTimer()
        self._flash_timer.timeout.connect(self._on_flash)
        self._flash_interval = 500  # ms

        # Setup widget
        self.setMinimumHeight(min_height)
        self.setAutoFillBackground(True)

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

    def set_status(
        self,
        status: str,
        display_text: Optional[str] = None,
        flash: bool = False
    ) -> None:
        """
        Set the current status.

        Args:
            status: Status identifier (READY, RUNNING, OK, NG, WARNING, ERROR)
            display_text: Optional custom display text
            flash: Whether to flash (for alerts)
        """
        old_status = self._status
        self._status = status.upper()
        self._display_text = display_text or self._status

        # Update colors
        color_map = {
            'READY': (COLOR_READY, '#555555'),
            'RUNNING': (COLOR_RUNNING, '#FFFFFF'),
            'OK': (COLOR_OK, '#FFFFFF'),
            'NG': (COLOR_NG, '#FFFFFF'),
            'WARNING': (COLOR_WARNING, '#FFFFFF'),
            'ERROR': (COLOR_NG, '#FFFFFF'),
            'INFO': (COLOR_INFO, '#FFFFFF')
        }

        bg_color, text_color = color_map.get(self._status, (COLOR_READY, '#FFFFFF'))
        self._bg_color = QColor(bg_color)
        self._text_color = QColor(text_color)

        # Flash animation
        if flash and self._status in ['NG', 'ERROR']:
            self._flashing = True
            if not self._flash_timer.isActive():
                self._flash_timer.start(self._flash_interval)
        else:
            self._flashing = False
            self._flash_timer.stop()
            self._flash_state = False

        self.update()

        if old_status != self._status:
            self.status_changed.emit(self._status)

    def get_status(self) -> str:
        """Get current status."""
        return self._status

    def set_detection_status(self, status: DetectionStatus) -> None:
        """Set status from DetectionStatus enum."""
        if status == DetectionStatus.OK:
            self.set_status("OK")
        elif status == DetectionStatus.NG:
            self.set_status("NG", flash=True)
        else:
            self.set_status("READY")

    def set_ready(self) -> None:
        """Set to READY state."""
        self.set_status("READY")

    def set_running(self) -> None:
        """Set to RUNNING state."""
        self.set_status("RUNNING")

    def set_ok(self, display_text: str = "OK") -> None:
        """Set to OK state."""
        self.set_status("OK", display_text)

    def set_ng(self, display_text: Optional[str] = None) -> None:
        """Set to NG state with flashing."""
        self.set_status("NG", display_text or "NG", flash=True)

    def set_error(self, message: str = "ERROR") -> None:
        """Set to ERROR state with flashing."""
        self.set_status("ERROR", message, flash=True)

    def _on_flash(self) -> None:
        """Handle flash timer."""
        self._flash_state = not self._flash_state
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """Paint the status indicator."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Background
        bg_color = self._bg_color
        if self._flashing and self._flash_state:
            # Flash to brighter color
            bg_color = bg_color.lighter(150)

        painter.fillRect(self.rect(), bg_color)

        # Border
        border_color = QColor("#000000")
        painter.setPen(border_color)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(
            0, 0, self.width() - 1, self.height() - 1,
            8, 8
        )

        # Text
        painter.setPen(self._text_color)
        font = QFont("Arial", self._font_size, QFont.Bold)
        painter.setFont(font)

        painter.drawText(
            self.rect(),
            Qt.AlignCenter,
            self._display_text
        )
