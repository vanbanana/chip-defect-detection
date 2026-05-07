"""
Configuration settings management.
Handles loading and saving of application configuration.
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict

from core.constants import (
    DEFAULT_CONFIG_DIR, DEFAULT_RECIPE_DIR, APP_NAME,
    DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT
)
from core.exceptions import ConfigurationError
from utils.logger import get_logger


@dataclass
class AppSettings:
    """Application-wide settings."""

    # Window settings
    window_width: int = DEFAULT_WINDOW_WIDTH
    window_height: int = DEFAULT_WINDOW_HEIGHT
    window_maximized: bool = False
    window_position: Optional[tuple] = None  # (x, y)

    # Recent files
    recent_folders: List[str] = field(default_factory=list)
    max_recent_folders: int = 10

    # Current settings
    current_recipe: str = "默认配置"
    current_algorithm: str = "hsv_detector"

    # Display settings
    status_font_size: int = 60
    show_preview_images: bool = True
    auto_fit_images: bool = True

    # Export settings
    default_export_format: str = "csv"
    export_include_images: bool = False

    # Logging
    log_level: str = "INFO"
    log_to_database: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AppSettings':
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class RecipeConfig:
    """Detection recipe configuration."""

    name: str
    algorithm: str
    parameters: Dict[str, Any]
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'name': self.name,
            'algorithm': self.algorithm,
            'description': self.description,
            'parameters': self.parameters
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RecipeConfig':
        """Create from dictionary."""
        return cls(
            name=data.get('name', 'Unnamed'),
            algorithm=data.get('algorithm', 'hsv_detector'),
            description=data.get('description', ''),
            parameters=data.get('parameters', {})
        )


class Settings:
    """
    Centralized settings manager.

    Handles:
    - Application settings (window size, recent files, etc.)
    - Recipe configurations (detection parameters)
    - Settings persistence (JSON files)
    """

    def __init__(self, config_dir: Optional[str] = None):
        self._logger = get_logger(__name__)
        self._config_dir = Path(config_dir or DEFAULT_CONFIG_DIR)
        self._recipe_dir = self._config_dir / "recipes"

        # Ensure directories exist
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._recipe_dir.mkdir(parents=True, exist_ok=True)

        # Settings
        self._app_settings: Optional[AppSettings] = None
        self._recipe_cache: Dict[str, RecipeConfig] = {}

    def get_app_settings(self) -> AppSettings:
        """Get application settings, loading from file if needed."""
        if self._app_settings is None:
            self._app_settings = self._load_app_settings()
        return self._app_settings

    def save_app_settings(self, settings: AppSettings) -> None:
        """Save application settings to file."""
        settings_path = self._config_dir / "app_settings.json"

        try:
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump(settings.to_dict(), f, indent=4, ensure_ascii=False)

            self._app_settings = settings
            self._logger.info(f"Settings saved to {settings_path}")
        except Exception as e:
            raise ConfigurationError(f"Failed to save settings: {str(e)}")

    def _load_app_settings(self) -> AppSettings:
        """Load application settings from file."""
        settings_path = self._config_dir / "app_settings.json"

        if not settings_path.exists():
            return AppSettings()

        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return AppSettings.from_dict(data)
        except Exception as e:
            self._logger.warning(f"Failed to load settings: {str(e)}, using defaults")
            return AppSettings()

    # Recipe management

    def list_recipes(self) -> List[str]:
        """List all available recipe names."""
        self._refresh_recipe_cache()
        return sorted(self._recipe_cache.keys())

    def get_recipe(self, name: str) -> Optional[RecipeConfig]:
        """Get a recipe by name."""
        self._refresh_recipe_cache()
        return self._recipe_cache.get(name)

    def save_recipe(self, recipe: RecipeConfig) -> None:
        """Save a recipe to file."""
        from utils.validators import validate_recipe_name

        # Validate name
        is_valid, error = validate_recipe_name(recipe.name)
        if not is_valid:
            raise ConfigurationError(f"Invalid recipe name: {error}")

        # Save to file
        recipe_path = self._recipe_dir / f"{recipe.name}.json"

        try:
            with open(recipe_path, 'w', encoding='utf-8') as f:
                json.dump(recipe.to_dict(), f, indent=4, ensure_ascii=False)

            # Update cache
            self._recipe_cache[recipe.name] = recipe
            self._logger.info(f"Recipe saved: {recipe.name}")
        except Exception as e:
            raise ConfigurationError(f"Failed to save recipe: {str(e)}")

    def delete_recipe(self, name: str) -> None:
        """Delete a recipe."""
        recipe_path = self._recipe_dir / f"{name}.json"

        if not recipe_path.exists():
            raise ConfigurationError(f"Recipe not found: {name}")

        try:
            recipe_path.unlink()
            self._recipe_cache.pop(name, None)
            self._logger.info(f"Recipe deleted: {name}")
        except Exception as e:
            raise ConfigurationError(f"Failed to delete recipe: {str(e)}")

    def _refresh_recipe_cache(self) -> None:
        """Refresh the recipe cache from disk."""
        self._recipe_cache.clear()

        for recipe_file in self._recipe_dir.glob("*.json"):
            try:
                with open(recipe_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                recipe = RecipeConfig.from_dict(data)
                self._recipe_cache[recipe.name] = recipe
            except Exception as e:
                self._logger.warning(f"Failed to load recipe {recipe_file}: {str(e)}")

    def import_recipe(self, source_path: str) -> str:
        """
        Import a recipe from an external file.

        Args:
            source_path: Path to recipe JSON file

        Returns:
            Name of the imported recipe
        """
        source = Path(source_path)
        if not source.exists():
            raise ConfigurationError(f"File not found: {source_path}")

        try:
            with open(source, 'r', encoding='utf-8') as f:
                data = json.load(f)

            recipe = RecipeConfig.from_dict(data)
            self.save_recipe(recipe)
            return recipe.name
        except Exception as e:
            raise ConfigurationError(f"Failed to import recipe: {str(e)}")

    def export_recipe(self, name: str, dest_path: str) -> None:
        """
        Export a recipe to an external file.

        Args:
            name: Recipe name
            dest_path: Destination file path
        """
        recipe = self.get_recipe(name)
        if recipe is None:
            raise ConfigurationError(f"Recipe not found: {name}")

        try:
            with open(dest_path, 'w', encoding='utf-8') as f:
                json.dump(recipe.to_dict(), f, indent=4, ensure_ascii=False)
            self._logger.info(f"Recipe exported: {name} -> {dest_path}")
        except Exception as e:
            raise ConfigurationError(f"Failed to export recipe: {str(e)}")
