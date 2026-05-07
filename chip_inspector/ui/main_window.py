"""
Main application window.
Orchestrates all views and services for the chip inspection application.
"""
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget,
    QMessageBox, QStatusBar, QLabel
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction

from ui.views import ProductionView, GalleryView, RecipeView, LogsView
from core.models import InspectionResult
from core.constants import APP_NAME, APP_VERSION, APP_DISPLAY_NAME
from utils.logger import get_logger, setup_logging
from services.config_service import ConfigService
from services.detection_service import DetectionService
from services.result_service import ResultService
from services.export_service import ExportService


class MainWindow(QMainWindow):
    """
    Main application window.

    Features:
    - Tabbed interface (Production, Gallery, Recipe, Logs)
    - Service orchestration
    - Menu bar with actions
    - Status bar with info
    - Window state persistence
    """

    # Signals
    about_to_close = Signal()

    def __init__(self):
        super().__init__()

        self._logger = get_logger(__name__)

        # Initialize services
        self._init_services()

        # Setup UI
        self._setup_ui()
        self._create_menu_bar()
        self._create_status_bar()

        # Load settings
        self._load_settings()

        # Log startup
        self._logger.info(f"{APP_DISPLAY_NAME} v{APP_VERSION} started")

    def _init_services(self) -> None:
        """Initialize all services."""
        # Config service
        self._config = ConfigService()

        # Result service (needs database)
        self._results = ResultService()

        # Detection service
        self._detection = DetectionService(self._config, self._results)

        # Export service
        self._export = ExportService()

    def _setup_ui(self) -> None:
        """Setup the main window UI."""
        self.setWindowTitle(f"{APP_DISPLAY_NAME} v{APP_VERSION}")
        self.resize(1600, 950)
        self.setMinimumSize(1200, 700)

        # Apply stylesheet
        self._apply_stylesheet()

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Tab widget
        self._tabs = QTabWidget()
        self._tabs.setTabPosition(QTabWidget.North)
        main_layout.addWidget(self._tabs)

        # Create views
        self._create_views()

    def _create_views(self) -> None:
        """Create all tab views."""
        # Create views first (order matters for signal connections)
        self._gallery_view = GalleryView(self._results)

        self._production_view = ProductionView(
            self._config,
            self._detection,
            self._results
        )
        self._production_view.inspection_completed.connect(self._on_inspection_completed)
        self._production_view.batch_started.connect(self._gallery_view.start_batch_mode)
        self._production_view.batch_completed.connect(self._gallery_view.end_batch_mode)

        self._recipe_view = RecipeView(self._config)
        self._recipe_view.recipe_changed.connect(self._on_recipe_changed)

        self._logs_view = LogsView(self._results)

        # Add tabs in desired order (Production first = default)
        self._tabs.addTab(self._production_view, "生产运行 (RUN)")
        self._tabs.addTab(self._gallery_view, "结果图库 (GALLERY)")
        self._tabs.addTab(self._recipe_view, "配方管理 (RECIPE)")
        self._tabs.addTab(self._logs_view, "系统日志 (LOGS)")

    def _create_menu_bar(self) -> None:
        """Create the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("文件 (&F)")

        action_open_folder = QAction("打开文件夹 (&O)", self)
        action_open_folder.setShortcut("Ctrl+O")
        action_open_folder.triggered.connect(self._on_open_folder)
        file_menu.addAction(action_open_folder)

        file_menu.addSeparator()

        action_export_csv = QAction("导出 CSV (&C)", self)
        action_export_csv.triggered.connect(self._on_export_csv)
        file_menu.addAction(action_export_csv)

        action_export_excel = QAction("导出 Excel (&E)", self)
        action_export_excel.triggered.connect(self._on_export_excel)
        file_menu.addAction(action_export_excel)

        file_menu.addSeparator()

        action_exit = QAction("退出 (&X)", self)
        action_exit.setShortcut("Alt+F4")
        action_exit.triggered.connect(self.close)
        file_menu.addAction(action_exit)

        # Edit menu
        edit_menu = menubar.addMenu("编辑 (&E)")

        action_preferences = QAction("首选项 (&P)", self)
        action_preferences.setShortcut("Ctrl+,")
        action_preferences.triggered.connect(self._on_preferences)
        edit_menu.addAction(action_preferences)

        # View menu
        view_menu = menubar.addMenu("视图 (&V)")

        action_refresh = QAction("刷新 (&R)", self)
        action_refresh.setShortcut("F5")
        action_refresh.triggered.connect(self._on_refresh)
        view_menu.addAction(action_refresh)

        # Tools menu
        tools_menu = menubar.addMenu("工具 (&T)")

        action_backup_db = QAction("备份数据库 (&B)", self)
        action_backup_db.triggered.connect(self._on_backup_database)
        tools_menu.addAction(action_backup_db)

        action_vacuum_db = QAction("清理数据库 (&V)", self)
        action_vacuum_db.triggered.connect(self._on_vacuum_database)
        tools_menu.addAction(action_vacuum_db)

        # Help menu
        help_menu = menubar.addMenu("帮助 (&H)")

        action_about = QAction("关于 (&A)", self)
        action_about.triggered.connect(self._on_about)
        help_menu.addAction(action_about)

    def _create_status_bar(self) -> None:
        """Create the status bar."""
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)

        # Status message
        self._status_label = QLabel("就绪")
        self._status_bar.addWidget(self._status_label)

        # Database info
        self._db_label = QLabel()
        self._status_bar.addPermanentWidget(self._db_label)

        # Update db info
        self._update_db_info()

    def _apply_stylesheet(self) -> None:
        """Apply the industrial theme stylesheet."""
        # Load stylesheet from file
        style_path = Path(__file__).parent / "styles" / "industrial.qss"

        if style_path.exists():
            with open(style_path, 'r', encoding='utf-8') as f:
                stylesheet = f.read()
        else:
            # Fallback inline stylesheet
            stylesheet = """
            QMainWindow, QWidget {
                background-color: #121212;
                color: #E0E0E0;
            }
            """

        self.setStyleSheet(stylesheet)

    # Settings persistence

    def _load_settings(self) -> None:
        """Load application settings."""
        settings = self._config.get_app_settings()

        # Window geometry
        self.resize(settings.window_width, settings.window_height)

        if settings.window_maximized:
            self.showMaximized()

        if settings.window_position:
            self.move(*settings.window_position)

    def _save_settings(self) -> None:
        """Save application settings."""
        from services.config_service import AppSettings

        settings = AppSettings()
        settings.window_width = self.width()
        settings.window_height = self.height()
        settings.window_maximized = self.isMaximized()

        if not self.isMaximized():
            settings.window_position = (self.x(), self.y())

        self._config.update_app_settings(**settings.to_dict())

    # Event handlers

    def _on_inspection_completed(self, result: InspectionResult) -> None:
        """Handle inspection completion."""
        # Add to gallery
        self._gallery_view.add_result(result)

        # Update status
        status_text = f"检测完成: {result.image_name} - {result.get_status_display()}"
        self._status_label.setText(status_text)

    def _on_recipe_changed(self, recipe_name: str) -> None:
        """Handle recipe change."""
        self._status_label.setText(f"当前配方: {recipe_name}")

    def _on_open_folder(self) -> None:
        """Handle open folder menu action."""
        # Switch to production tab and trigger load
        self._tabs.setCurrentWidget(self._production_view)
        self._production_view.load_folder("")

    def _on_export_csv(self) -> None:
        """Handle export CSV action."""
        self._tabs.setCurrentWidget(self._gallery_view)
        # Trigger export via gallery view

    def _on_export_excel(self) -> None:
        """Handle export Excel action."""
        self._tabs.setCurrentWidget(self._gallery_view)
        # Trigger export via gallery view

    def _on_preferences(self) -> None:
        """Handle preferences action."""
        QMessageBox.information(self, "首选项", "首选项对话框尚未实现")

    def _on_refresh(self) -> None:
        """Handle refresh action."""
        current_tab = self._tabs.currentWidget()

        if isinstance(current_tab, GalleryView):
            current_tab.refresh()
        elif isinstance(current_tab, LogsView):
            current_tab.refresh()
        elif isinstance(current_tab, RecipeView):
            current_tab._load_recipes()

        self._update_db_info()

    def _on_backup_database(self) -> None:
        """Handle database backup."""
        try:
            from PySide6.QtWidgets import QFileDialog

            path, _ = QFileDialog.getSaveFileName(
                self, "备份数据库", "backup.db", "Database (*.db)"
            )

            if path:
                backup_path = self._results.backup_database(path)
                QMessageBox.information(self, "成功", f"数据库已备份到:\n{backup_path}")
                self._update_db_info()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"备份失败: {str(e)}")

    def _on_vacuum_database(self) -> None:
        """Handle database vacuum."""
        reply = QMessageBox.question(
            self, "确认清理",
            "确定要清理数据库吗？\n这将回收数据库空间。",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                self._results.vacuum_database()
                QMessageBox.information(self, "成功", "数据库已清理")
                self._update_db_info()

            except Exception as e:
                QMessageBox.critical(self, "错误", f"清理失败: {str(e)}")

    def _on_about(self) -> None:
        """Handle about dialog."""
        QMessageBox.about(
            self,
            f"关于 {APP_NAME}",
            f"""
            <h2>{APP_DISPLAY_NAME}</h2>
            <p>版本: {APP_VERSION}</p>
            <p>工业级芯片缺陷检测系统</p>
            <hr>
            <p>功能特点:</p>
            <ul>
            <li>HSV色彩空间缺陷检测</li>
            <li>批量处理支持</li>
            <li>配方管理系统</li>
            <li>结果数据导出</li>
            <li>系统日志记录</li>
            </ul>
            <p>© 2024 Industrial Vision Solutions</p>
            """
        )

    def _update_db_info(self) -> None:
        """Update database info in status bar."""
        try:
            info = self._results.get_database_info()
            self._db_label.setText(
                f"检测: {info['inspections_total']} | "
                f"配方: {info['recipes_count']} | "
                f"日志: {info['events_count']}"
            )
        except:
            self._db_label.setText("数据库离线")

    # Window events

    def closeEvent(self, event) -> None:
        """Handle window close event."""
        self.about_to_close.emit()

        # Save settings
        self._save_settings()

        # Confirm if batch is running
        if self._detection.status.value != 0:  # Not IDLE
            reply = QMessageBox.question(
                self, "确认退出",
                "检测任务正在运行，确定要退出吗？",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.No:
                event.ignore()
                return

            # Stop detection
            self._detection.stop()

        event.accept()
        self._logger.info("Application closed")
