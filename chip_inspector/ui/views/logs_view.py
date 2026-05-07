"""
Logs view - System event log viewer.
View and filter system events with export capability.
"""
from typing import Optional, List
from datetime import datetime, timedelta

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QPushButton, QAbstractItemView,
    QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from ui.widgets import NoWheelComboBox
from core.models import SystemEvent
from core.enums import SystemEventType
from utils.logger import get_logger
from services.result_service import ResultService


class LogsView(QWidget):
    """
    System event log viewer.

    Features:
    - Display system events in a table
    - Filter by event type (INFO, WARNING, ERROR)
    - Export logs to file
    - Clear old logs
    """

    def __init__(
        self,
        result_service: ResultService,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)

        self._results = result_service
        self._logger = get_logger(__name__)

        self._events: List[SystemEvent] = []

        self._setup_ui()
        self._load_events()

    def _setup_ui(self) -> None:
        """Setup the logs view UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Title
        title = QLabel("系统日志")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #00B0FF;")
        main_layout.addWidget(title)

        # Toolbar
        toolbar = self._create_toolbar()
        main_layout.addLayout(toolbar)

        # Events table
        self._table = self._create_events_table()
        main_layout.addWidget(self._table)

    def _create_toolbar(self) -> QHBoxLayout:
        """Create the toolbar."""
        layout = QHBoxLayout()

        # Type filter
        layout.addWidget(QLabel("类型:"))

        self._combo_type = NoWheelComboBox()
        self._combo_type.addItems(["全部", "INFO", "WARNING", "ERROR", "DEBUG"])
        self._combo_type.currentIndexChanged.connect(self._on_filter_changed)
        layout.addWidget(self._combo_type)

        layout.addStretch()

        # Export button
        btn_export = QPushButton("导出日志")
        btn_export.clicked.connect(self._on_export)
        layout.addWidget(btn_export)

        # Clear button
        btn_clear = QPushButton("清除旧日志")
        btn_clear.clicked.connect(self._on_clear_old)
        layout.addWidget(btn_clear)

        # Refresh button
        btn_refresh = QPushButton("刷新")
        btn_refresh.clicked.connect(self._load_events)
        layout.addWidget(btn_refresh)

        return layout

    def _create_events_table(self) -> QTableWidget:
        """Create the events table."""
        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(["时间", "类型", "类别", "消息", "详情"])

        # Configure
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setAlternatingRowColors(True)

        # Style
        table.setStyleSheet("""
            QTableWidget {
                background-color: #1E1E1E;
                border: 1px solid #333;
                gridline-color: #333;
                alternate-background-color: #252525;
            }
            QHeaderView::section {
                background-color: #2D2D2D;
                color: #AAA;
                border: none;
                padding: 4px;
                font-weight: bold;
            }
            QTableWidget::item:selected {
                background-color: #004C8C;
                color: white;
            }
        """)

        return table

    # Data loading

    def _load_events(self) -> None:
        """Load events from database."""
        # Get filter
        filter_type = self._combo_type.currentText()
        event_type = None if filter_type == "全部" else filter_type

        self._events = self._results.get_recent_events(
            limit=1000,
            event_type=event_type
        )

        self._populate_table()

    def _on_filter_changed(self) -> None:
        """Handle filter change."""
        self._load_events()

    def _populate_table(self) -> None:
        """Populate the table with events."""
        self._table.setRowCount(0)

        for event in self._events:
            row = self._table.rowCount()
            self._table.insertRow(row)

            # Timestamp
            time_str = event.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            self._table.setItem(row, 0, QTableWidgetItem(time_str))

            # Event type (color coded)
            type_item = QTableWidgetItem(event.event_type)
            if event.event_type == "ERROR":
                type_item.setForeground(QColor("#FF1744"))
            elif event.event_type == "WARNING":
                type_item.setForeground(QColor("#FF9800"))
            elif event.event_type == "INFO":
                type_item.setForeground(QColor("#00B0FF"))

            self._table.setItem(row, 1, type_item)

            # Category
            self._table.setItem(row, 2, QTableWidgetItem(event.event_category))

            # Message
            self._table.setItem(row, 3, QTableWidgetItem(event.message))

            # Details
            details = event.details or ""
            if len(details) > 50:
                details = details[:50] + "..."
            self._table.setItem(row, 4, QTableWidgetItem(details))

    # Actions

    def _on_export(self) -> None:
        """Export logs to file."""
        if not self._events:
            QMessageBox.warning(self, "警告", "无日志可导出")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "导出日志", "logs.txt", "Text (*.txt)"
        )

        if path:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write("=" * 80 + "\n")
                    f.write("系统日志导出\n")
                    f.write(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("=" * 80 + "\n\n")

                    for event in self._events:
                        f.write(f"[{event.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] ")
                        f.write(f"[{event.event_type}] ")
                        f.write(f"[{event.event_category}] ")
                        f.write(f"{event.message}\n")

                        if event.details:
                            f.write(f"  详情: {event.details}\n")
                        f.write("\n")

                QMessageBox.information(self, "成功", f"已导出 {len(self._events)} 条日志")

            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")

    def _on_clear_old(self) -> None:
        """Clear old logs."""
        reply = QMessageBox.question(
            self, "确认清除",
            "确定要清除30天前的日志吗?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                count = self._results.clear_old_events(30)
                self._load_events()

                QMessageBox.information(self, "成功", f"已清除 {count} 条旧日志")

            except Exception as e:
                QMessageBox.critical(self, "错误", f"清除失败: {str(e)}")

    def refresh(self) -> None:
        """Refresh the logs."""
        self._load_events()

    def add_event(self, event: SystemEvent) -> None:
        """Add a new event to the log."""
        self._events.insert(0, event)

        # Check filter
        filter_type = self._combo_type.currentText()
        if filter_type == "全部" or filter_type == event.event_type:
            # Add to table
            row = self._table.rowCount()
            self._table.insertRow(0, row)

            time_str = event.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            self._table.setItem(0, 0, QTableWidgetItem(time_str))
            self._table.setItem(0, 1, QTableWidgetItem(event.event_type))
            self._table.setItem(0, 2, QTableWidgetItem(event.event_category))
            self._table.setItem(0, 3, QTableWidgetItem(event.message))
            self._table.setItem(0, 4, QTableWidgetItem(event.details or ""))

            # Limit rows
            if self._table.rowCount() > 1000:
                self._table.removeRow(1000)
