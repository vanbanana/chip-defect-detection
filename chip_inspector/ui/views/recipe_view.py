"""
Recipe view - Recipe management interface.
Create, edit, duplicate, import, and export detection recipes.
"""
from typing import Optional, List

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMessageBox,
    QFileDialog, QInputDialog, QDialog, QFormLayout,
    QLineEdit, QTextEdit, QComboBox
)
from PySide6.QtCore import Qt, Signal

from core.models import Recipe
from utils.logger import get_logger
from services.config_service import ConfigService


class RecipeView(QWidget):
    """
    Recipe management view.

    Features:
    - List all recipes in a table
    - Create new recipe
    - Edit existing recipe
    - Duplicate recipe
    - Delete recipe
    - Import/Export recipes
    """

    # Signals
    recipe_changed = Signal(str)  # recipe_name

    def __init__(
        self,
        config_service: ConfigService,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)

        self._config = config_service
        self._logger = get_logger(__name__)

        self._recipes: List[Recipe] = []

        self._setup_ui()
        self._load_recipes()

    def _setup_ui(self) -> None:
        """Setup the recipe view UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Title
        title = QLabel("配方管理")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #00B0FF;")
        main_layout.addWidget(title)

        # Toolbar
        toolbar = self._create_toolbar()
        main_layout.addLayout(toolbar)

        # Recipe table
        self._table = self._create_recipe_table()
        main_layout.addWidget(self._table)

    def _create_toolbar(self) -> QHBoxLayout:
        """Create the toolbar."""
        layout = QHBoxLayout()

        btn_new = QPushButton("新建配方")
        btn_new.clicked.connect(self._on_new_recipe)
        layout.addWidget(btn_new)

        btn_edit = QPushButton("编辑")
        btn_edit.clicked.connect(self._on_edit_recipe)
        layout.addWidget(btn_edit)

        btn_duplicate = QPushButton("复制")
        btn_duplicate.clicked.connect(self._on_duplicate_recipe)
        layout.addWidget(btn_duplicate)

        btn_delete = QPushButton("删除")
        btn_delete.clicked.connect(self._on_delete_recipe)
        layout.addWidget(btn_delete)

        layout.addStretch()

        btn_import = QPushButton("导入")
        btn_import.clicked.connect(self._on_import_recipe)
        layout.addWidget(btn_import)

        btn_export = QPushButton("导出")
        btn_export.clicked.connect(self._on_export_recipe)
        layout.addWidget(btn_export)

        btn_refresh = QPushButton("刷新")
        btn_refresh.clicked.connect(self._load_recipes)
        layout.addWidget(btn_refresh)

        return layout

    def _create_recipe_table(self) -> QTableWidget:
        """Create the recipe table."""
        table = QTableWidget(0, 4)
        table.setHorizontalHeaderLabels(["名称", "算法", "描述", "修改时间"])

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

    def _load_recipes(self) -> None:
        """Load recipes from config service."""
        recipe_names = self._config.list_recipes()
        self._recipes = []

        for name in recipe_names:
            recipe = self._config.get_recipe(name)
            if recipe:
                self._recipes.append(recipe)

        self._populate_table()

    def _populate_table(self) -> None:
        """Populate the table with recipes."""
        self._table.setRowCount(0)

        for i, recipe in enumerate(self._recipes):
            row = self._table.rowCount()
            self._table.insertRow(row)

            self._table.setItem(row, 0, QTableWidgetItem(recipe.name))
            self._table.setItem(row, 1, QTableWidgetItem(recipe.algorithm))
            self._table.setItem(row, 2, QTableWidgetItem(recipe.description))

            time_str = ""
            if recipe.modified_at:
                time_str = recipe.modified_at.strftime("%Y-%m-%d %H:%M")
            self._table.setItem(row, 3, QTableWidgetItem(time_str))

    # Actions

    def _on_new_recipe(self) -> None:
        """Create a new recipe."""
        dialog = RecipeEditDialog(
            algorithms=self._config.get_available_algorithms(),
            config_service=self._config,
            parent=self
        )

        if dialog.exec() == QDialog.Accepted:
            try:
                name = dialog.get_name()
                algorithm = dialog.get_algorithm()
                description = dialog.get_description()
                parameters = dialog.get_parameters()

                self._config.create_recipe(name, algorithm, parameters, description)
                self._load_recipes()

                QMessageBox.information(self, "成功", f"配方 '{name}' 已创建")

            except Exception as e:
                QMessageBox.critical(self, "错误", f"创建失败: {str(e)}")

    def _on_edit_recipe(self) -> None:
        """Edit selected recipe."""
        row = self._table.currentRow()
        if row < 0 or row >= len(self._recipes):
            QMessageBox.warning(self, "警告", "请选择要编辑的配方")
            return

        recipe = self._recipes[row]

        dialog = RecipeEditDialog(
            algorithms=self._config.get_available_algorithms(),
            config_service=self._config,
            parent=self
        )
        dialog.set_recipe(recipe)

        if dialog.exec() == QDialog.Accepted:
            try:
                name = dialog.get_name()
                description = dialog.get_description()
                parameters = dialog.get_parameters()

                self._config.update_recipe(name, parameters, description)
                self._load_recipes()

                QMessageBox.information(self, "成功", f"配方 '{name}' 已更新")

            except Exception as e:
                QMessageBox.critical(self, "错误", f"更新失败: {str(e)}")

    def _on_duplicate_recipe(self) -> None:
        """Duplicate selected recipe."""
        row = self._table.currentRow()
        if row < 0 or row >= len(self._recipes):
            QMessageBox.warning(self, "警告", "请选择要复制的配方")
            return

        source = self._recipes[row]

        # Get new name
        new_name, ok = QInputDialog.getText(
            self, "复制配方", "新配方名称:", text=f"{source.name}_copy"
        )

        if ok and new_name:
            try:
                self._config.duplicate_recipe(source.name, new_name)
                self._load_recipes()

                QMessageBox.information(self, "成功", f"配方已复制为 '{new_name}'")

            except Exception as e:
                QMessageBox.critical(self, "错误", f"复制失败: {str(e)}")

    def _on_delete_recipe(self) -> None:
        """Delete selected recipe."""
        row = self._table.currentRow()
        if row < 0 or row >= len(self._recipes):
            QMessageBox.warning(self, "警告", "请选择要删除的配方")
            return

        recipe = self._recipes[row]

        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除配方 '{recipe.name}' 吗?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                self._config.delete_recipe(recipe.name)
                self._load_recipes()

                QMessageBox.information(self, "成功", f"配方 '{recipe.name}' 已删除")

            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除失败: {str(e)}")

    def _on_import_recipe(self) -> None:
        """Import a recipe from file."""
        path, _ = QFileDialog.getOpenFileName(
            self, "导入配方", "", "JSON (*.json)"
        )

        if path:
            try:
                name = self._config.import_recipe(path)
                self._load_recipes()

                QMessageBox.information(self, "成功", f"配方 '{name}' 已导入")

            except Exception as e:
                QMessageBox.critical(self, "错误", f"导入失败: {str(e)}")

    def _on_export_recipe(self) -> None:
        """Export selected recipe to file."""
        row = self._table.currentRow()
        if row < 0 or row >= len(self._recipes):
            QMessageBox.warning(self, "警告", "请选择要导出的配方")
            return

        recipe = self._recipes[row]

        path, _ = QFileDialog.getSaveFileName(
            self, "导出配方", f"{recipe.name}.json", "JSON (*.json)"
        )

        if path:
            try:
                self._config.export_recipe(recipe.name, path)

                QMessageBox.information(self, "成功", f"配方已导出到 {path}")

            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")


class RecipeEditDialog(QDialog):
    """Dialog for creating/editing a recipe."""

    def __init__(
        self,
        algorithms: List[dict],
        config_service,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)

        self._algorithms = algorithms
        self._config_service = config_service
        self._parameters: dict = {}

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the dialog UI."""
        self.setWindowTitle("配方编辑")
        self.resize(500, 400)

        layout = QFormLayout(self)

        # Name
        self._edit_name = QLineEdit()
        layout.addRow("配方名称:", self._edit_name)

        # Algorithm
        self._combo_algorithm = QComboBox()
        for algo in self._algorithms:
            self._combo_algorithm.addItem(algo['name'], algo['id'])
        self._combo_algorithm.currentIndexChanged.connect(self._on_algorithm_changed)
        layout.addRow("算法:", self._combo_algorithm)

        # Description
        self._edit_description = QTextEdit()
        self._edit_description.setMaximumHeight(80)
        layout.addRow("描述:", self._edit_description)

        # Parameters (will be populated based on algorithm)
        self._parameter_widget = QWidget()
        self._parameter_layout = QFormLayout(self._parameter_widget)
        layout.addRow("参数:", self._parameter_widget)

        # Buttons
        from PySide6.QtWidgets import QDialogButtonBox
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _on_algorithm_changed(self) -> None:
        """Handle algorithm selection change."""
        # Clear existing parameters
        while self._parameter_layout.count():
            item = self._parameter_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Load new parameters
        algo_id = self._combo_algorithm.currentData()
        definitions = self._config_service.get_algorithm_parameters(algo_id)

        self._parameter_inputs = {}

        for name, definition in definitions.items():
            if definition['type'] == 'int':
                from ui.widgets import SmartSlider
                slider = SmartSlider(
                    name=definition['display_name'],
                    min_val=definition['min'],
                    max_val=definition['max'],
                    init_val=definition['default'],
                    scale=definition.get('scale', 1.0)
                )
                self._parameter_layout.addRow(slider)
                self._parameter_inputs[name] = slider

    def set_recipe(self, recipe: Recipe) -> None:
        """Set the recipe data for editing."""
        self._edit_name.setText(recipe.name)
        self._edit_description.setPlainText(recipe.description)

        # Set algorithm
        for i in range(self._combo_algorithm.count()):
            if self._combo_algorithm.itemData(i) == recipe.algorithm:
                self._combo_algorithm.setCurrentIndex(i)
                break

        # Set parameters
        for name, value in recipe.parameters.items():
            if name in self._parameter_inputs:
                self._parameter_inputs[name].set_value(value)

    def get_name(self) -> str:
        """Get recipe name."""
        return self._edit_name.text()

    def get_algorithm(self) -> str:
        """Get algorithm ID."""
        return self._combo_algorithm.currentData()

    def get_description(self) -> str:
        """Get recipe description."""
        return self._edit_description.toPlainText()

    def get_parameters(self) -> dict:
        """Get parameter values."""
        return {
            name: slider.get_value()
            for name, slider in self._parameter_inputs.items()
        }
