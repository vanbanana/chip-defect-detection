"""
Gallery view - Result history and analysis.
Industrial data analysis for production management.
"""
from typing import Optional, List
from datetime import datetime, timedelta

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QPushButton, QAbstractItemView, QMessageBox,
    QFileDialog, QGroupBox, QGridLayout, QDateEdit,
    QFrame, QSplitter
)
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QColor

from ui.widgets import CanvasWidget, NoWheelComboBox
from core.models import InspectionResult
from core.enums import DetectionStatus
from core.constants import COLOR_OK, COLOR_NG
from utils.logger import get_logger
from services.result_service import ResultService
from services.export_service import ExportService


class StatisticsPanel(QGroupBox):
    """
    Industrial statistics panel.
    Shows comprehensive production statistics.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("统计分析", parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the statistics panel."""
        self.setStyleSheet("""
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

        layout = QGridLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(8, 12, 8, 8)

        # Create labels
        self._label_total_count = QLabel("0")
        self._label_total_count.setStyleSheet("color: #FFFFFF; font-size: 18px; font-weight: bold;")
        self._label_total_count.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self._label_ok_count = QLabel("0")
        self._label_ok_count.setStyleSheet(f"color: {COLOR_OK}; font-size: 18px; font-weight: bold;")
        self._label_ok_count.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self._label_ng_count = QLabel("0")
        self._label_ng_count.setStyleSheet(f"color: {COLOR_NG}; font-size: 18px; font-weight: bold;")
        self._label_ng_count.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self._label_pass_rate = QLabel("0.0%")
        self._label_pass_rate.setStyleSheet("color: #00B0FF; font-size: 18px; font-weight: bold;")
        self._label_pass_rate.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self._label_avg_defect = QLabel("0")
        self._label_avg_defect.setStyleSheet("color: #FFA726; font-size: 18px; font-weight: bold;")
        self._label_avg_defect.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self._label_max_defect = QLabel("0")
        self._label_max_defect.setStyleSheet("color: #EF5350; font-size: 18px; font-weight: bold;")
        self._label_max_defect.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Row 1
        layout.addWidget(QLabel("检测总数:"), 0, 0)
        layout.addWidget(self._label_total_count, 0, 1)
        layout.addWidget(QLabel("合格数:"), 0, 2)
        layout.addWidget(self._label_ok_count, 0, 3)

        # Row 2
        layout.addWidget(QLabel("不良数:"), 1, 0)
        layout.addWidget(self._label_ng_count, 1, 1)
        layout.addWidget(QLabel("良品率:"), 1, 2)
        layout.addWidget(self._label_pass_rate, 1, 3)

        # Row 3
        layout.addWidget(QLabel("平均缺陷:"), 2, 0)
        layout.addWidget(self._label_avg_defect, 2, 1)
        layout.addWidget(QLabel("最大缺陷:"), 2, 2)
        layout.addWidget(self._label_max_defect, 2, 3)

    def update_statistics(self, results: List[InspectionResult]) -> None:
        """Update statistics from results."""
        if not results:
            self._reset()
            return

        total = len(results)
        ok_count = sum(1 for r in results if r.is_ok)
        ng_count = total - ok_count
        pass_rate = (ok_count / total * 100) if total > 0 else 0

        ng_results = [r for r in results if r.is_ng]
        avg_defect = sum(r.defect_area for r in ng_results) / len(ng_results) if ng_results else 0
        max_defect = max((r.defect_area for r in results), default=0)

        self._label_total_count.setText(str(total))
        self._label_ok_count.setText(str(ok_count))
        self._label_ng_count.setText(str(ng_count))
        self._label_pass_rate.setText(f"{pass_rate:.2f}%")
        self._label_avg_defect.setText(f"{int(avg_defect)}")
        self._label_max_defect.setText(f"{int(max_defect)}")

    def _reset(self) -> None:
        """Reset all labels."""
        self._label_total_count.setText("0")
        self._label_ok_count.setText("0")
        self._label_ng_count.setText("0")
        self._label_pass_rate.setText("0.0%")
        self._label_avg_defect.setText("0")
        self._label_max_defect.setText("0")


class GalleryView(QWidget):
    """
    Gallery view for production data analysis.

    Features:
    - Comprehensive result table
    - Statistical analysis panel
    - Date range filtering
    - Status filtering
    - Image preview
    - Data export
    """

    # Signals
    result_selected = Signal(object)

    def __init__(
        self,
        result_service: ResultService,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)

        self._results = result_service
        self._export = ExportService()
        self._logger = get_logger(__name__)

        self._all_results: List[InspectionResult] = []
        self._filtered_results: List[InspectionResult] = []
        self._batch_mode = False  # Batch mode flag
        self._pending_results: List[InspectionResult] = []  # Pending results in batch mode

        self._setup_ui()
        self._load_results()

    def _setup_ui(self) -> None:
        """Setup the gallery view UI - Industrial layout."""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # Left side: Data panel
        left_splitter = QSplitter(Qt.Vertical)
        left_splitter.setHandleWidth(3)

        # Filter and statistics panel
        top_panel = QWidget()
        top_layout = QVBoxLayout(top_panel)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(6)

        # Filter bar
        filter_panel = self._create_filter_panel()
        top_layout.addWidget(filter_panel)

        # Statistics panel
        self._stats_panel = StatisticsPanel()
        top_layout.addWidget(self._stats_panel)

        left_splitter.addWidget(top_panel)

        # Results table
        self._table = self._create_result_table()
        left_splitter.addWidget(self._table)

        # Set splitter sizes
        left_splitter.setSizes([200, 400])

        main_layout.addWidget(left_splitter, 2)

        # Right side: Preview
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(2)

        # Header
        preview_label = QLabel("图像预览")
        preview_label.setAlignment(Qt.AlignCenter)
        preview_label.setStyleSheet(
            "background-color: #2D2D2D; color: #AAAAAA; "
            "font-weight: bold; font-size: 12px; padding: 4px; "
            "border: 1px solid #444; border-bottom: none;"
        )
        preview_label.setFixedHeight(30)
        right_layout.addWidget(preview_label)

        # Canvas
        self._view_preview = CanvasWidget("选择记录查看预览")
        self._view_preview.setMinimumSize(400, 320)
        self._view_preview.setStyleSheet(
            "border: 1px solid #444; background-color: #1A1A1A;"
        )
        right_layout.addWidget(self._view_preview)

        # Result info panel
        info_panel = self._create_result_info_panel()
        right_layout.addWidget(info_panel)

        main_layout.addWidget(right_panel, 1)

    def _create_filter_panel(self) -> QGroupBox:
        """Create the filter panel."""
        box = QGroupBox("数据筛选")
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
        layout.setSpacing(6)
        layout.setContentsMargins(8, 12, 8, 8)

        # Status filter
        layout.addWidget(QLabel("状态:"), 0, 0)
        self._combo_filter = NoWheelComboBox()
        self._combo_filter.setMinimumHeight(28)
        self._combo_filter.addItems(["全部记录", "仅合格", "仅不合格"])
        self._combo_filter.currentIndexChanged.connect(self._on_filter_changed)
        layout.addWidget(self._combo_filter, 0, 1)

        # Recipe filter
        layout.addWidget(QLabel("配方:"), 0, 2)
        self._combo_recipe = NoWheelComboBox()
        self._combo_recipe.setMinimumHeight(28)
        self._combo_recipe.addItem("全部配方")
        self._combo_recipe.currentIndexChanged.connect(self._on_filter_changed)
        layout.addWidget(self._combo_recipe, 0, 3)

        # Date range
        layout.addWidget(QLabel("日期:"), 1, 0)
        self._date_start = QDateEdit()
        self._date_start.setMinimumHeight(28)
        self._date_start.setCalendarPopup(True)
        self._date_start.setDate(QDate.currentDate().addDays(-7))
        self._date_start.dateChanged.connect(self._on_filter_changed)
        layout.addWidget(self._date_start, 1, 1)

        self._date_end = QDateEdit()
        self._date_end.setMinimumHeight(28)
        self._date_end.setCalendarPopup(True)
        self._date_end.setDate(QDate.currentDate())
        self._date_end.dateChanged.connect(self._on_filter_changed)
        layout.addWidget(self._date_end, 1, 2)

        # Action buttons row
        btn_refresh = QPushButton("刷新")
        btn_refresh.setMinimumHeight(28)
        btn_refresh.clicked.connect(self.refresh)
        layout.addWidget(btn_refresh, 1, 3)

        # Data management buttons
        btn_clear = QPushButton("清除数据")
        btn_clear.setMinimumHeight(28)
        btn_clear.setStyleSheet("QPushButton { background-color: #D32F2F; color: white; }")
        btn_clear.clicked.connect(self._on_clear_data)
        layout.addWidget(btn_clear, 2, 0)

        btn_export_csv = QPushButton("导出CSV")
        btn_export_csv.setMinimumHeight(28)
        btn_export_csv.clicked.connect(self._on_export_csv)
        layout.addWidget(btn_export_csv, 2, 1)

        btn_export_excel = QPushButton("导出Excel")
        btn_export_excel.setMinimumHeight(28)
        btn_export_excel.clicked.connect(self._on_export_excel)
        layout.addWidget(btn_export_excel, 2, 2)

        btn_refresh2 = QPushButton("刷新显示")
        btn_refresh2.setMinimumHeight(28)
        btn_refresh2.clicked.connect(self.refresh)
        layout.addWidget(btn_refresh2, 2, 3)

        return box

    def _create_result_table(self) -> QTableWidget:
        """Create the results table."""
        table = QTableWidget(0, 6)
        table.setHorizontalHeaderLabels([
            "状态", "文件名", "配方", "缺陷面积",
            "检测时间", "处理时长"
        ])

        # Configure table
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)

        # Industrial styling
        table.setStyleSheet("""
            QTableWidget {
                background-color: #1A1A1A;
                border: 1px solid #444;
                gridline-color: #333;
                color: #CCCCCC;
                font-size: 11px;
            }
            QHeaderView::section {
                background-color: #2D2D2D;
                color: #00B0FF;
                border: none;
                border-bottom: 2px solid #00B0FF;
                padding: 6px 8px;
                font-weight: bold;
                font-size: 11px;
            }
            QTableWidget::item:selected {
                background-color: #1976D2;
                color: white;
            }
            QTableWidget::item:hover {
                background-color: #2A2A2A;
            }
            QScrollBar:vertical {
                background-color: #1A1A1A;
                width: 12px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background-color: #444;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #555;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        table.itemClicked.connect(self._on_table_click)

        return table

    def _create_result_info_panel(self) -> QGroupBox:
        """Create result info panel."""
        box = QGroupBox("详细信息")
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
        layout.setContentsMargins(8, 12, 8, 8)

        self._info_status = QLabel("-")
        self._info_status.setStyleSheet("color: #AAAAAA; font-size: 13px; font-weight: bold;")
        layout.addWidget(QLabel("检测结果:"), 0, 0)
        layout.addWidget(self._info_status, 0, 1)

        self._info_area = QLabel("-")
        self._info_area.setStyleSheet("color: #AAAAAA; font-size: 13px;")
        layout.addWidget(QLabel("缺陷面积:"), 0, 2)
        layout.addWidget(self._info_area, 0, 3)

        self._info_recipe = QLabel("-")
        self._info_recipe.setStyleSheet("color: #AAAAAA; font-size: 13px;")
        layout.addWidget(QLabel("使用配方:"), 1, 0)
        layout.addWidget(self._info_recipe, 1, 1)

        self._info_time = QLabel("-")
        self._info_time.setStyleSheet("color: #AAAAAA; font-size: 13px;")
        layout.addWidget(QLabel("检测时间:"), 1, 2)
        layout.addWidget(self._info_time, 1, 3)

        self._info_duration = QLabel("-")
        self._info_duration.setStyleSheet("color: #AAAAAA; font-size: 13px;")
        layout.addWidget(QLabel("处理时长:"), 2, 0)
        layout.addWidget(self._info_duration, 2, 1)

        self._info_path = QLabel("-")
        self._info_path.setStyleSheet("color: #AAAAAA; font-size: 12px;")
        self._info_path.setWordWrap(True)
        layout.addWidget(QLabel("文件路径:"), 2, 2, 1, 2)
        layout.addWidget(self._info_path, 3, 0, 1, 4)

        # Export buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)

        btn_csv = QPushButton("导出CSV")
        btn_csv.setMinimumHeight(30)
        btn_csv.clicked.connect(self._on_export_csv)
        btn_layout.addWidget(btn_csv)

        btn_excel = QPushButton("导出Excel")
        btn_excel.setMinimumHeight(30)
        btn_excel.clicked.connect(self._on_export_excel)
        btn_layout.addWidget(btn_excel)

        layout.addLayout(btn_layout, 4, 0, 1, 4)

        return box

    # Data loading

    def _load_results(self) -> None:
        """Load results from database."""
        self._all_results = self._results.get_recent_inspectons(limit=2000)

        # Update recipe filter
        recipes = set(r.recipe_name for r in self._all_results)
        current_recipe = self._combo_recipe.currentText()
        self._combo_recipe.blockSignals(True)
        self._combo_recipe.clear()
        self._combo_recipe.addItem("全部配方")
        self._combo_recipe.addItems(sorted(recipes))
        if current_recipe:
            index = self._combo_recipe.findText(current_recipe)
            if index >= 0:
                self._combo_recipe.setCurrentIndex(index)
        self._combo_recipe.blockSignals(False)

        self._apply_filter()

    def refresh(self) -> None:
        """Refresh the results."""
        self._load_results()

    def add_result(self, result: InspectionResult) -> None:
        """Add a new result to the gallery."""
        if self._batch_mode:
            # Batch mode: just collect, don't update UI
            self._pending_results.append(result)
            self._all_results.insert(0, result)
        else:
            # Normal mode: immediate update
            self._all_results.insert(0, result)
            self._apply_filter()

    def start_batch_mode(self) -> None:
        """Enter batch mode - defer UI updates."""
        self._batch_mode = True
        self._pending_results = []

    def end_batch_mode(self) -> None:
        """Exit batch mode and update UI once."""
        self._batch_mode = False
        if self._pending_results:
            self._apply_filter()
            self._pending_results = []

    # Filtering

    def _on_filter_changed(self) -> None:
        """Handle filter change."""
        self._apply_filter()

    def _apply_filter(self) -> None:
        """Apply current filter to results."""
        status_filter = self._combo_filter.currentIndex()
        recipe_filter = self._combo_recipe.currentText()

        # Convert QDate to datetime at start and end of day
        start_qdate = self._date_start.date()
        end_qdate = self._date_end.date()

        date_start = datetime(start_qdate.year(), start_qdate.month(), start_qdate.day(), 0, 0, 0)
        date_end = datetime(end_qdate.year(), end_qdate.month(), end_qdate.day(), 23, 59, 59)

        filtered = []

        for result in self._all_results:
            # Status filter
            if status_filter == 1 and not result.is_ok:
                continue
            if status_filter == 2 and not result.is_ng:
                continue

            # Recipe filter
            if recipe_filter != "全部配方" and result.recipe_name != recipe_filter:
                continue

            # Date filter
            if result.timestamp < date_start or result.timestamp > date_end:
                continue

            filtered.append(result)

        self._filtered_results = filtered
        self._populate_table()
        self._stats_panel.update_statistics(filtered)

    def _populate_table(self) -> None:
        """Populate the table with filtered results."""
        self._table.setRowCount(0)

        for i, result in enumerate(self._filtered_results):
            row = self._table.rowCount()
            self._table.insertRow(row)

            # Status
            status_item = QTableWidgetItem("合格" if result.is_ok else "NG")
            if result.is_ok:
                status_item.setForeground(QColor(COLOR_OK))
            else:
                status_item.setForeground(QColor(COLOR_NG))
            status_item.setData(Qt.UserRole, i)
            self._table.setItem(row, 0, status_item)

            # File name
            self._table.setItem(row, 1, QTableWidgetItem(result.image_name))

            # Recipe
            self._table.setItem(row, 2, QTableWidgetItem(result.recipe_name))

            # Defect area
            area_text = str(int(result.defect_area)) if result.defect_area > 0 else "-"
            self._table.setItem(row, 3, QTableWidgetItem(area_text))

            # Timestamp
            time_str = result.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            self._table.setItem(row, 4, QTableWidgetItem(time_str))

            # Processing time
            duration = f"{result.processing_time_ms:.0f}ms"
            self._table.setItem(row, 5, QTableWidgetItem(duration))

    # Selection

    def _on_table_click(self, item) -> None:
        """Handle table item click."""
        row = item.row()
        status_item = self._table.item(row, 0)
        index = status_item.data(Qt.UserRole)

        if index < len(self._filtered_results):
            result = self._filtered_results[index]

            # Display preview
            if result.result_image:
                self._view_preview.set_pixmap(result.result_image)

            # Update info panel
            self._update_info_panel(result)

            # Emit signal
            self.result_selected.emit(result)

    def _update_info_panel(self, result: InspectionResult) -> None:
        """Update the info panel with result details."""
        if result.is_ok:
            self._info_status.setText("合格 OK")
            self._info_status.setStyleSheet(f"color: {COLOR_OK}; font-size: 13px; font-weight: bold;")
        else:
            self._info_status.setText("不合格 NG")
            self._info_status.setStyleSheet(f"color: {COLOR_NG}; font-size: 13px; font-weight: bold;")

        self._info_area.setText(f"{int(result.defect_area)} px²")
        self._info_recipe.setText(result.recipe_name)
        self._info_time.setText(result.timestamp.strftime("%Y-%m-%d %H:%M:%S"))
        self._info_duration.setText(f"{result.processing_time_ms:.1f} ms")
        self._info_path.setText(result.image_path)

    def _on_clear_data(self) -> None:
        """Handle clear data button - clear all detection results."""
        reply = QMessageBox.question(
            self,
            "确认清除",
            "确定要清除所有检测数据吗？\n此操作将删除数据库中的所有检测记录，不可恢复。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                # Clear all inspection data from database
                count = self._results.clear_all_inspections()
                self._all_results = []
                self._filtered_results = []
                self._table.setRowCount(0)
                self._stats_panel._reset()
                self._clear_preview()

                QMessageBox.information(
                    self, "完成", f"已清除 {count} 条检测记录"
                )
            except Exception as e:
                QMessageBox.critical(self, "错误", f"清除失败: {str(e)}")

    def _clear_preview(self) -> None:
        """Clear the preview area."""
        self._view_preview.clear()
        self._info_status.setText("-")
        self._info_status.setStyleSheet("color: #AAAAAA; font-size: 13px;")
        self._info_area.setText("-")
        self._info_area.setStyleSheet("color: #AAAAAA; font-size: 13px;")
        self._info_recipe.setText("-")
        self._info_time.setText("-")
        self._info_duration.setText("-")
        self._info_path.setText("-")

    # Export

    def _on_export_csv(self) -> None:
        """Handle CSV export."""
        if not self._filtered_results:
            QMessageBox.warning(self, "警告", "无数据可导出")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "导出CSV", "inspection_report.csv", "CSV (*.csv)"
        )

        if path:
            try:
                count = self._export.export_to_csv(self._filtered_results, path)
                QMessageBox.information(self, "成功", f"已导出 {count} 条记录")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")

    def _on_export_excel(self) -> None:
        """Handle Excel export."""
        if not self._filtered_results:
            QMessageBox.warning(self, "警告", "无数据可导出")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "导出Excel", "inspection_report.xlsx", "Excel (*.xlsx)"
        )

        if path:
            try:
                count = self._export.export_to_excel(self._filtered_results, path)
                QMessageBox.information(self, "成功", f"已导出 {count} 条记录")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
