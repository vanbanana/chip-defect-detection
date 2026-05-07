"""
Smart slider widgets with integrated input controls.
Combines slider and spinbox with bidirectional synchronization.
"""
from typing import Optional
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSlider, QSpinBox, QDoubleSpinBox, QComboBox
from PySide6.QtCore import Qt, Signal

from utils.logger import get_logger


class NoWheelSlider(QSlider):
    """Slider that ignores mouse wheel events."""
    def wheelEvent(self, event):
        event.ignore()


class NoWheelSpinBox(QSpinBox):
    """Spinbox that ignores mouse wheel events."""
    def wheelEvent(self, event):
        event.ignore()


class NoWheelDoubleSpinBox(QDoubleSpinBox):
    """Double spinbox that ignores mouse wheel events."""
    def wheelEvent(self, event):
        event.ignore()


class NoWheelComboBox(QComboBox):
    """Combobox that ignores mouse wheel events."""
    def wheelEvent(self, event):
        event.ignore()


class SmartSlider(QWidget):
    """
    Combined slider and spinbox with bidirectional sync.

    Features:
    - Slider and spinbox always synchronized
    - Optional decimal scaling for float parameters
    - Configurable min/max/step values
    - Label display
    - Scroll-safe (ignores mouse wheel)
    """

    value_changed = Signal(float)

    def __init__(
        self,
        name: str,
        min_val: float,
        max_val: float,
        init_val: float,
        scale: float = 1.0,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)

        self._logger = get_logger(__name__)
        self._scale = scale
        self._is_float = scale != 1.0

        # Setup layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(8)

        # Label
        self._label = QLabel(name)
        self._label.setFixedWidth(80)
        self._label.setStyleSheet("color: #AAA; font-weight: bold;")
        layout.addWidget(self._label)

        # Slider
        self._slider = NoWheelSlider(Qt.Horizontal)
        self._slider.setRange(int(min_val), int(max_val))
        self._slider.setValue(int(init_val))
        self._slider.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self._slider)

        # Spinbox
        if self._is_float:
            self._spin = NoWheelDoubleSpinBox()
            self._spin.setDecimals(1)
            self._spin.setSingleStep(0.1)
            self._spin.setRange(min_val * scale, max_val * scale)
        else:
            self._spin = NoWheelSpinBox()
            self._spin.setRange(int(min_val), int(max_val))

        self._spin.setFixedWidth(60)
        self._spin.setValue(init_val * scale)
        self._spin.setKeyboardTracking(False)
        layout.addWidget(self._spin)

        # Connect signals
        self._slider.valueChanged.connect(self._on_slider_changed)
        self._spin.valueChanged.connect(self._on_spin_changed)

    def _on_slider_changed(self, value: int) -> None:
        """Handle slider value change."""
        real_value = value * self._scale

        # Update spinbox if different
        if abs(self._spin.value() - real_value) > 0.0001:
            self._spin.blockSignals(True)
            self._spin.setValue(real_value)
            self._spin.blockSignals(False)

        self.value_changed.emit(real_value)

    def _on_spin_changed(self, value: float) -> None:
        """Handle spinbox value change."""
        slider_value = int(value / self._scale) if self._scale != 1.0 else int(value)

        # Update slider if different
        if self._slider.value() != slider_value:
            self._slider.blockSignals(True)
            self._slider.setValue(slider_value)
            self._slider.blockSignals(False)

        self.value_changed.emit(value)

    def get_value(self) -> float:
        """Get current value."""
        return self._spin.value()

    def set_value(self, value: float) -> None:
        """Set current value."""
        self._spin.setValue(value)

    def set_range(self, min_val: float, max_val: float) -> None:
        """Update min/max range."""
        self._slider.setRange(int(min_val), int(max_val))

        if self._is_float:
            self._spin.setRange(min_val * self._scale, max_val * self._scale)
        else:
            self._spin.setRange(int(min_val), int(max_val))

    def set_enabled(self, enabled: bool) -> None:
        """Enable/disable the widget."""
        self._slider.setEnabled(enabled)
        self._spin.setEnabled(enabled)
        self._label.setEnabled(enabled)

    def block_signals(self, block: bool) -> None:
        """Block all signals."""
        self._slider.blockSignals(block)
        self._spin.blockSignals(block)
