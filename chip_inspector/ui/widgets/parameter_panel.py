"""
Parameter panel widget for algorithm parameters.
Displays grouped parameters with color-coded categories.
"""
from typing import Dict, Any, List, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QScrollArea,
    QGridLayout, QLabel, QFrame
)
from PySide6.QtCore import Signal

from ui.widgets import SmartSlider
from core.constants import COLOR_OK, COLOR_NG, COLOR_WARNING, COLOR_INFO
from utils.logger import get_logger


class ParameterPanel(QWidget):
    """
    Scrollable panel for detection parameters.

    Features:
    - Grouped parameters by category
    - Color-coded categories
    - Auto-generated sliders from parameter definitions
    - Bidirectional value change signals
    """

    parameters_changed = Signal(dict)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._logger = get_logger(__name__)
        self._sliders: Dict[str, SmartSlider] = {}
        self._parameter_groups: Dict[str, List[str]] = {}

        # Setup UI
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the parameter panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        # Container widget
        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setSpacing(10)
        self._container_layout.addStretch()

        scroll.setWidget(self._container)
        layout.addWidget(scroll)

    def load_parameters(
        self,
        parameter_definitions: Dict[str, Dict[str, Any]],
        current_values: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Load parameters from definitions.

        Args:
            parameter_definitions: Dict mapping parameter names to definitions
            current_values: Current parameter values
        """
        # Block signals during loading to prevent unwanted emissions
        self.blockSignals(True)

        try:
            # Clear existing
            self._clear_parameters()

            # Group by color_code/category
            groups = self._group_parameters(parameter_definitions)

            # Create UI for each group
            for group_name, group_color, params in groups:
                group_box = self._create_parameter_group(
                    group_name, group_color, params,
                    parameter_definitions, current_values
                )
                self._container_layout.insertWidget(
                    self._container_layout.count() - 1,  # Before stretch
                    group_box
                )
        finally:
            # Re-enable signals
            self.blockSignals(False)

    def _group_parameters(
        self,
        definitions: Dict[str, Dict[str, Any]]
    ) -> List[tuple[str, str, List[str]]]:
        """Group parameters by their color_code/category."""
        groups = {}

        for name, definition in definitions.items():
            color_code = definition.get('color_code', '#555555')

            # Group name based on color
            if color_code == COLOR_OK:
                group_name = "芯片定位 (HSV)"
            elif color_code == COLOR_NG:
                group_name = "缺陷判定"
            elif color_code == COLOR_WARNING:
                group_name = "检测区域"
            elif color_code == COLOR_INFO:
                group_name = "图像处理"
            else:
                group_name = "其他参数"

            if group_name not in groups:
                groups[group_name] = (color_code, [])

            groups[group_name][1].append(name)

        # Convert to list
        return [
            (name, color, params)
            for name, (color, params) in groups.items()
        ]

    def _create_parameter_group(
        self,
        group_name: str,
        group_color: str,
        param_names: List[str],
        definitions: Dict[str, Dict[str, Any]],
        current_values: Optional[Dict[str, Any]]
    ) -> QGroupBox:
        """Create a parameter group box."""
        group = QGroupBox(group_name)
        layout = QVBoxLayout(group)
        layout.setSpacing(5)

        # Style
        group.setStyleSheet(f"""
            QGroupBox {{
                border: 1px solid #333;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 15px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: {group_color};
            }}
        """)

        # Add parameters
        for param_name in param_names:
            definition = definitions[param_name]
            slider = self._create_slider(param_name, definition, current_values)

            self._sliders[param_name] = slider
            layout.addWidget(slider)

        return group

    def _create_slider(
        self,
        param_name: str,
        definition: Dict[str, Any],
        current_values: Optional[Dict[str, Any]]
    ) -> SmartSlider:
        """Create a slider for a parameter."""
        display_name = definition.get('display_name', param_name)
        min_val = definition.get('min', 0)
        max_val = definition.get('max', 255)
        default_val = definition.get('default', min_val)

        # Get current value or default
        if current_values and param_name in current_values:
            init_val = current_values[param_name]
        else:
            init_val = default_val

        # Create slider
        slider = SmartSlider(
            name=display_name,
            min_val=min_val,
            max_val=max_val,
            init_val=init_val,
            scale=definition.get('scale', 1.0)
        )

        # Connect signal
        slider.value_changed.connect(
            lambda v, n=param_name: self._on_parameter_changed(n, v)
        )

        return slider

    def _on_parameter_changed(self, name: str, value: float) -> None:
        """Handle parameter value change."""
        params = self.get_parameters()
        self.parameters_changed.emit(params)

    def get_parameters(self) -> Dict[str, Any]:
        """Get current parameter values."""
        return {
            name: slider.get_value()
            for name, slider in self._sliders.items()
        }

    def set_parameters(self, params: Dict[str, Any]) -> None:
        """Set parameter values."""
        for name, value in params.items():
            if name in self._sliders:
                self._sliders[name].set_value(value)

    def _clear_parameters(self) -> None:
        """Clear all existing parameters."""
        # Remove all widgets except stretch
        while self._container_layout.count() > 1:
            item = self._container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._sliders.clear()
