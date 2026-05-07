"""
Production view - Main detection interface.
Industrial design for production environment.
"""
from typing import Optional, List, Dict, Any
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QLabel, QGroupBox, QGridLayout, QPushButton,
    QProgressBar, QComboBox, QFileDialog, QMessageBox,
    QFrame
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPainter, QColor, QFont, QPen

from ui.widgets import (
    CanvasWidget, ParameterPanel, NoWheelComboBox
)
from core.models import InspectionResult, BatchProgress
from core.enums import DetectionStatus
from core.constants import COLOR_OK, COLOR_NG
from utils.logger import get_logger
from services.config_service import ConfigService
from services.detection_service import DetectionService
from services.result_service import ResultService


class PassRateDisplay(QWidget):
    """
    Industrial pass rate display widget.
    Shows dynamic pass rate percentage with color coding.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._pass_rate = 0.0
        self._total = 0
        self._ok = 0
        self._ng = 0
        self.setMinimumHeight(80)

    def update_stats(self, total: int, ok: int, ng: int) -> None:
        """Update statistics."""
        self._total = total
        self._ok = ok
        self._ng = ng
        self._pass_rate = (ok / total * 100) if total > 0 else 0.0
        self.update()

    def paintEvent(self, event) -> None:
        """Paint the pass rate display."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()

        # Determine color based on pass rate
        if self._pass_rate >= 95:
            bar_color = QColor("#00E676")  # Green
        elif self._pass_rate >= 85:
            bar_color = QColor("#FFC107")  # Yellow
        else:
            bar_color = QColor("#F44336")  # Red

        # Background
        painter.fillRect(rect, QColor("#1E1E1E"))

        # Border
        painter.setPen(QPen(QColor("#444"), 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(rect.adjusted(1, 1, -1, -1))

        # Pass rate bar
        if self._total > 0:
            bar_width = int(rect.width() * self._pass_rate / 100)
            bar_rect = rect.adjusted(2, 2, -2, -2)
            bar_rect.setWidth(bar_width)
            painter.fillRect(bar_rect, bar_color)

        # Text
        painter.setPen(QColor("#FFFFFF"))
        font = QFont("Arial", 28, QFont.Bold)
        painter.setFont(font)

        text = f"{self._pass_rate:.1f}%"
        painter.drawText(rect, Qt.AlignCenter, text)

        # Subtitle text
        if self._total > 0:
            font2 = QFont("Arial", 11)
            painter.setFont(font2)
            painter.setPen(QColor("#AAAAAA"))
            sub_text = f"良品率  |  总数:{self._total}  合格:{self._ok}  不良:{self._ng}"
            sub_rect = rect.adjusted(0, 35, 0, 0)
            painter.drawText(sub_rect, Qt.AlignCenter, sub_text)


class ResultStatusOverlay(QWidget):
    """
    Compact status badge for result image.
    Small unobtrusive status indicator in corner of image.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._status = None
        self._defect_area = 0.0
        self._cached_text = ""
        self._cached_color = QColor()
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.raise_()
        self.setFixedSize(80, 50)

    def set_status(self, status: DetectionStatus, defect_area: float = 0.0) -> None:
        """Set the detection status - only updates if changed."""
        # Only update if status changed or defect area changed significantly
        if self._status == status and abs(self._defect_area - defect_area) < 1.0:
            return

        self._status = status
        self._defect_area = defect_area

        # Cache color and text
        if status == DetectionStatus.OK:
            self._cached_color = QColor(COLOR_OK)
            self._cached_text = "OK"
        elif status == DetectionStatus.NG:
            self._cached_color = QColor(COLOR_NG)
            self._cached_text = "NG"
        else:
            self.hide()
            return

        if not self.isVisible():
            self.show()
        self.update()

    def paintEvent(self, event) -> None:
        """Paint the compact status badge."""
        if not self._cached_text:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()

        # Background - small compact badge
        painter.setBrush(QColor("#1E1E1E"))
        painter.setPen(QPen(self._cached_color, 2))
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 4, 4)

        # Status text
        painter.setPen(self._cached_color)
        font = QFont("Arial", 18, QFont.Bold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, self._cached_text)


class ProductionView(QWidget):
    """
    Production/detection view - Industrial design.

    Features:
    - Side-by-side original and result image display
    - Result status overlay on image
    - Dynamic pass rate display
    - Real-time parameter adjustment
    - Batch folder processing
    - Navigation between images
    - Statistics display
    - Recipe selection
    """

    # Signals
    inspection_completed = Signal(object)
    batch_started = Signal()
    batch_completed = Signal()
    recipe_changed = Signal(str)

    def __init__(
        self,
        config_service: ConfigService,
        detection_service: DetectionService,
        result_service: ResultService,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)

        self._config = config_service
        self._detection = detection_service
        self._results = result_service
        self._logger = get_logger(__name__)

        # State
        self._current_images: List[str] = []
        self._current_index: int = 0
        self._current_result: Optional[InspectionResult] = None
        self._is_running_batch = False
        self._pending_params: Optional[Dict[str, Any]] = None

        # Debounce timer for parameter changes
        self._param_timer = QTimer()
        self._param_timer.setSingleShot(True)
        self._param_timer.timeout.connect(self._on_param_timer_timeout)

        # Setup UI
        self._setup_ui()
        self._load_recipes()

    def _setup_ui(self) -> None:
        """Setup the production view UI - Industrial layout."""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # Left side: Image display
        self._setup_image_display(main_layout)

        # Right side: Control panel
        self._setup_control_panel(main_layout)

    def _setup_image_display(self, parent_layout: QHBoxLayout) -> None:
        """Setup side-by-side image display."""
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(3)

        # Original image container
        orig_container = QWidget()
        orig_layout = QVBoxLayout(orig_container)
        orig_layout.setContentsMargins(0, 0, 0, 0)
        orig_layout.setSpacing(2)

        # Header
        orig_label = QLabel("原始图像")
        orig_label.setAlignment(Qt.AlignCenter)
        orig_label.setStyleSheet(
            "background-color: #2D2D2D; color: #AAAAAA; "
            "font-weight: bold; font-size: 12px; padding: 4px; "
            "border: 1px solid #444; border-bottom: none;"
        )
        orig_label.setFixedHeight(30)
        orig_layout.addWidget(orig_label)

        # Canvas
        self._view_original = CanvasWidget("等待加载...")
        self._view_original.setMinimumSize(350, 280)
        self._view_original.setStyleSheet(
            "border: 1px solid #444; background-color: #1A1A1A;"
        )
        orig_layout.addWidget(self._view_original)

        splitter.addWidget(orig_container)

        # Result image container with overlay
        res_container = QWidget()
        res_layout = QVBoxLayout(res_container)
        res_layout.setContentsMargins(0, 0, 0, 0)
        res_layout.setSpacing(2)

        # Header
        res_label = QLabel("检测结果")
        res_label.setAlignment(Qt.AlignCenter)
        res_label.setStyleSheet(
            "background-color: #2D2D2D; color: #AAAAAA; "
            "font-weight: bold; font-size: 12px; padding: 4px; "
            "border: 1px solid #444; border-bottom: none;"
        )
        res_label.setFixedHeight(30)
        res_layout.addWidget(res_label)

        # Canvas with overlay container
        canvas_container = QWidget()
        canvas_layout = QVBoxLayout(canvas_container)
        canvas_layout.setContentsMargins(0, 0, 0, 0)

        self._view_result = CanvasWidget("等待加载...")
        self._view_result.setMinimumSize(350, 280)
        self._view_result.setStyleSheet(
            "border: 1px solid #444; background-color: #1A1A1A;"
        )
        canvas_layout.addWidget(self._view_result)

        # Status overlay - positioned in top-right corner
        self._result_overlay = ResultStatusOverlay(self._view_result)
        self._result_overlay.hide()

        res_layout.addWidget(canvas_container)

        splitter.addWidget(res_container)

        # Set splitter sizes (50:50)
        splitter.setSizes([1, 1])

        parent_layout.addWidget(splitter, 3)

    def _setup_control_panel(self, parent_layout: QHBoxLayout) -> None:
        """Setup the right control panel."""
        ctrl_panel = QWidget()
        ctrl_panel.setFixedWidth(380)
        ctrl_layout = QVBoxLayout(ctrl_panel)
        ctrl_layout.setContentsMargins(0, 0, 0, 0)
        ctrl_layout.setSpacing(6)

        # Pass rate display
        self._pass_rate_display = PassRateDisplay()
        ctrl_layout.addWidget(self._pass_rate_display)

        # Statistics panel
        stats_panel = self._create_stats_panel()
        ctrl_layout.addWidget(stats_panel)

        # Production controls
        prod_panel = self._create_production_controls()
        ctrl_layout.addWidget(prod_panel)

        # File and recipe controls
        file_panel = self._create_file_controls()
        ctrl_layout.addWidget(file_panel)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFixedHeight(2)
        separator.setStyleSheet("background-color: #333;")
        ctrl_layout.addWidget(separator)

        # Parameter section
        param_label = QLabel("检测参数配置")
        param_label.setStyleSheet(
            "background-color: #2D2D2D; color: #00B0FF; "
            "font-weight: bold; font-size: 11px; padding: 6px 10px; "
            "border: 1px solid #444;"
        )
        ctrl_layout.addWidget(param_label)

        self._parameter_panel = ParameterPanel()
        self._parameter_panel.parameters_changed.connect(self._on_parameters_changed)
        ctrl_layout.addWidget(self._parameter_panel, 1)

        parent_layout.addWidget(ctrl_panel)

    def _create_stats_panel(self) -> QGroupBox:
        """Create statistics panel."""
        box = QGroupBox("批次统计")
        box.setStyleSheet("""
            QGroupBox {
                border: 1px solid #444;
                border-radius: 3px;
                margin-top: 8px;
                padding-top: 12px;
                background-color: #1E1E1E;
                font-weight: bold;
                font-size: 11px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #AAAAAA;
            }
        """)
        layout = QGridLayout(box)
        layout.setSpacing(4)

        self._label_total = QLabel("0")
        self._label_total.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._label_total.setStyleSheet("color: #FFFFFF; font-size: 16px; font-weight: bold;")

        self._label_ok = QLabel("0")
        self._label_ok.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._label_ok.setStyleSheet(f"color: {COLOR_OK}; font-size: 16px; font-weight: bold;")

        self._label_ng = QLabel("0")
        self._label_ng.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._label_ng.setStyleSheet(f"color: {COLOR_NG}; font-size: 16px; font-weight: bold;")

        layout.addWidget(QLabel("检测总数:"), 0, 0)
        layout.addWidget(self._label_total, 0, 1)
        layout.addWidget(QLabel("合格数:"), 0, 2)
        layout.addWidget(self._label_ok, 0, 3)
        layout.addWidget(QLabel("不良数:"), 1, 0)
        layout.addWidget(self._label_ng, 1, 1)

        return box

    def _create_production_controls(self) -> QGroupBox:
        """Create production control panel."""
        box = QGroupBox("生产操作")
        box.setStyleSheet("""
            QGroupBox {
                border: 1px solid #444;
                border-radius: 3px;
                margin-top: 8px;
                padding-top: 12px;
                background-color: #1E1E1E;
                font-weight: bold;
                font-size: 11px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #AAAAAA;
            }
        """)
        layout = QVBoxLayout(box)
        layout.setSpacing(6)

        # Main operation buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)

        self._btn_run = QPushButton("开始检测")
        self._btn_run.setMinimumHeight(42)
        self._btn_run.setStyleSheet("""
            QPushButton {
                background-color: #1976D2;
                color: #FFFFFF;
                border: none;
                font-weight: bold;
                font-size: 14px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #2196F3;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
            QPushButton:disabled {
                background-color: #424242;
                color: #757575;
            }
        """)
        self._btn_run.clicked.connect(self._on_run_batch)
        btn_layout.addWidget(self._btn_run)

        self._btn_stop = QPushButton("停止")
        self._btn_stop.setMinimumHeight(42)
        self._btn_stop.setEnabled(False)
        self._btn_stop.setStyleSheet("""
            QPushButton {
                background-color: #D32F2F;
                color: #FFFFFF;
                border: none;
                font-weight: bold;
                font-size: 14px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #F44336;
            }
            QPushButton:pressed {
                background-color: #B71C1C;
            }
            QPushButton:disabled {
                background-color: #424242;
                color: #757575;
            }
        """)
        self._btn_stop.clicked.connect(self._on_stop_batch)
        btn_layout.addWidget(self._btn_stop)

        layout.addLayout(btn_layout)

        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(8)
        self._progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1A1A1A;
                border: 1px solid #444;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #1976D2;
                border-radius: 1px;
            }
        """)
        layout.addWidget(self._progress_bar)

        return box

    def _create_file_controls(self) -> QGroupBox:
        """Create file and recipe controls."""
        box = QGroupBox("配置与文件")
        box.setStyleSheet("""
            QGroupBox {
                border: 1px solid #444;
                border-radius: 3px;
                margin-top: 8px;
                padding-top: 12px;
                background-color: #1E1E1E;
                font-weight: bold;
                font-size: 11px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #AAAAAA;
            }
        """)
        layout = QVBoxLayout(box)
        layout.setSpacing(6)

        # Recipe selection
        recipe_layout = QHBoxLayout()
        recipe_layout.setSpacing(6)
        recipe_layout.addWidget(QLabel("当前配方:"))

        self._combo_recipe = NoWheelComboBox()
        self._combo_recipe.setMinimumHeight(30)
        self._combo_recipe.currentIndexChanged.connect(self._on_recipe_changed)
        recipe_layout.addWidget(self._combo_recipe, 1)

        btn_save = QPushButton("保存")
        btn_save.setMinimumHeight(30)
        btn_save.clicked.connect(self._on_save_recipe)
        recipe_layout.addWidget(btn_save)

        layout.addLayout(recipe_layout)

        # Load folder button
        btn_load = QPushButton("加载图像文件夹")
        btn_load.setMinimumHeight(36)
        btn_load.clicked.connect(self._on_load_folder)
        layout.addWidget(btn_load)

        # Navigation
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(6)

        btn_prev = QPushButton("< 上一张")
        btn_prev.setMinimumHeight(30)
        btn_prev.clicked.connect(self._on_prev_image)
        nav_layout.addWidget(btn_prev)

        self._label_file = QLabel("未加载")
        self._label_file.setAlignment(Qt.AlignCenter)
        self._label_file.setStyleSheet(
            "color: #AAAAAA; background-color: #1A1A1A; "
            "padding: 4px; border: 1px solid #444; border-radius: 2px;"
        )
        nav_layout.addWidget(self._label_file, 1)

        btn_next = QPushButton("下一张 >")
        btn_next.setMinimumHeight(30)
        btn_next.clicked.connect(self._on_next_image)
        nav_layout.addWidget(btn_next)

        layout.addLayout(nav_layout)

        return box

    # Recipe management

    def _load_recipes(self) -> None:
        """Load recipe list into combo box."""
        recipes = self._config.list_recipes()

        self._combo_recipe.blockSignals(True)
        self._combo_recipe.clear()
        self._combo_recipe.addItems(recipes)

        current = self._config.get_current_recipe()
        if current and recipes:
            if current.name in recipes:
                self._combo_recipe.setCurrentText(current.name)
            else:
                self._combo_recipe.setCurrentIndex(0)
                self._on_recipe_changed(0)
        elif recipes:
            self._combo_recipe.setCurrentIndex(0)
            self._on_recipe_changed(0)

        self._combo_recipe.blockSignals(False)
        self._load_current_parameters()

    def _load_current_parameters(self) -> None:
        """Load parameters for current recipe."""
        recipe = self._config.get_current_recipe()
        if recipe is None:
            return

        algo = self._config.create_detector()
        definitions = algo.get_parameter_definitions()
        self._parameter_panel.load_parameters(definitions, recipe.parameters)

    def cleanup(self) -> None:
        """Cleanup resources."""
        if hasattr(self, '_param_timer'):
            self._param_timer.stop()

    def _on_recipe_changed(self, index: int) -> None:
        """Handle recipe selection change."""
        recipe_name = self._combo_recipe.currentText()
        self._config.set_current_recipe(recipe_name)
        self._load_current_parameters()

        if self._current_images:
            self._run_single_detection()

        self.recipe_changed.emit(recipe_name)

    def _on_save_recipe(self) -> None:
        """Handle save recipe button."""
        from PySide6.QtWidgets import QInputDialog

        current_name = self._combo_recipe.currentText()
        name, ok = QInputDialog.getText(
            self, "保存配方", "配方名称:", text=current_name
        )

        if ok and name:
            params = self._parameter_panel.get_parameters()

            if name in self._config.list_recipes():
                self._config.update_recipe(name, parameters=params)
            else:
                recipe = self._config.get_current_recipe()
                algo = recipe.algorithm if recipe else "hsv_detector"
                self._config.create_recipe(name, algo, params)

            self._load_recipes()
            self._combo_recipe.setCurrentText(name)

    # File operations

    def _on_load_folder(self) -> None:
        """Handle load folder button."""
        folder = QFileDialog.getExistingDirectory(self, "选择图像文件夹")
        if folder:
            self.load_folder(folder)

    def load_folder(self, folder_path: str) -> None:
        """Load images from a folder."""
        from utils.image_utils import get_image_files

        self._current_images = get_image_files(folder_path)

        if self._current_images:
            self._current_index = 0
            self._run_single_detection()

            QMessageBox.information(
                self, "就绪", f"已加载 {len(self._current_images)} 张图像"
            )
        else:
            QMessageBox.warning(self, "警告", "未找到图像文件")

    def _on_prev_image(self) -> None:
        """Handle previous image button."""
        if self._current_images and self._current_index > 0:
            self._current_index -= 1
            self._run_single_detection()

    def _on_next_image(self) -> None:
        """Handle next image button."""
        if self._current_images and self._current_index < len(self._current_images) - 1:
            self._current_index += 1
            self._run_single_detection()

    # Detection

    def _on_parameters_changed(self, params: Dict[str, Any]) -> None:
        """Handle parameter changes - debounced for performance."""
        # Store pending params and restart timer
        self._pending_params = params
        self._param_timer.start(150)  # 150ms debounce

    def _on_param_timer_timeout(self) -> None:
        """Handle parameter change timer timeout."""
        if self._pending_params and self._current_images and not self._is_running_batch:
            self._run_single_detection(preview_params=self._pending_params)
            self._pending_params = None

    def _run_single_detection(self, preview_params: Optional[Dict[str, Any]] = None) -> None:
        """Run detection on current image."""
        if not self._current_images:
            return

        image_path = self._current_images[self._current_index]
        self._label_file.setText(
            f"{Path(image_path).name} [{self._current_index + 1}/{len(self._current_images)}]"
        )

        try:
            if preview_params:
                result = self._detection.preview_detection(image_path, preview_params)
            else:
                result = self._detection.detect_single(image_path, save_result=False)

            self._current_result = result
            self._display_result(result)

        except Exception as e:
            self._logger.error(f"Detection failed: {str(e)}")
            self._result_overlay.hide()

    def _display_result(self, result: InspectionResult) -> None:
        """Display detection result."""
        # Update images
        if result.original_image:
            self._view_original.set_pixmap(result.original_image)
        if result.result_image:
            self._view_result.set_pixmap(result.result_image)

        # Position and show status overlay
        self._position_overlay()
        self._result_overlay.set_status(result.status, result.defect_area)
        self._result_overlay.show()
        self._result_overlay.raise_()

    def _position_overlay(self) -> None:
        """Position the status overlay in top-right corner of result canvas."""
        canvas_size = self._view_result.size()
        # Position in top-right with margin
        x = canvas_size.width() - 90
        y = 5
        self._result_overlay.move(x, y)

    # Batch processing

    def _on_run_batch(self) -> None:
        """Handle run batch button."""
        if not self._current_images:
            QMessageBox.warning(self, "警告", "请先加载图像文件夹")
            return

        self._is_running_batch = True
        self._btn_run.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._result_overlay.hide()

        self.batch_started.emit()

        try:
            results = self._detection.detect_batch(
                image_paths=self._current_images,
                progress_callback=self._on_batch_progress,
                result_callback=self._on_batch_result,
                save_results=True
            )

            self._on_batch_complete(results)

        except Exception as e:
            self._logger.error(f"Batch failed: {str(e)}")
            QMessageBox.critical(self, "错误", f"批量检测失败: {str(e)}")

        finally:
            self._is_running_batch = False
            self._btn_run.setEnabled(True)
            self._btn_stop.setEnabled(False)

    def _on_stop_batch(self) -> None:
        """Handle stop button."""
        self._detection.stop()

    def _on_batch_progress(self, progress: BatchProgress) -> None:
        """Handle batch progress updates."""
        self._progress_bar.setValue(progress.progress_percent)

        # Update statistics
        self._label_total.setText(str(progress.completed))
        self._label_ok.setText(str(progress.ok_count))
        self._label_ng.setText(str(progress.ng_count))

        # Update pass rate display
        self._pass_rate_display.update_stats(
            progress.completed, progress.ok_count, progress.ng_count
        )

    def _on_batch_result(self, result: InspectionResult) -> None:
        """Handle individual result during batch - no UI updates for performance."""
        self._current_result = result
        # Skip all UI updates during batch for maximum performance
        # Only update statistics through progress_callback
        self.inspection_completed.emit(result)

    def _on_batch_complete(self, results: List[InspectionResult]) -> None:
        """Handle batch completion."""
        self.batch_completed.emit()

        if results:
            stats = self._results.get_batch_statistics(results)
            QMessageBox.information(
                self,
                "检测完成",
                f"批量检测完成\n\n"
                f"检测总数: {stats['total']}\n"
                f"合格数量: {stats['ok_count']}\n"
                f"不良数量: {stats['ng_count']}\n"
                f"良品率: {stats['pass_rate']:.2f}%"
            )
