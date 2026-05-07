"""
Configuration service - Business logic for configuration management.
Provides high-level configuration operations with validation and logging.
"""
from typing import Dict, Any, List, Optional
from pathlib import Path

from config.settings import Settings, AppSettings, RecipeConfig
from config.validation import ConfigValidator
from core.exceptions import ConfigurationError, ValidationError
from core.models import Recipe, DetectionConfig
from algorithms.registry import AlgorithmRegistry
from utils.logger import get_logger


class ConfigService:
    """
    High-level configuration service.

    Features:
    - Recipe CRUD operations
    - Application settings management
    - Parameter validation
    - Algorithm integration
    """

    def __init__(self, config_dir: Optional[str] = None):
        self._logger = get_logger(__name__)
        self._settings = Settings(config_dir)
        self._validator = ConfigValidator()
        self._current_recipe: Optional[RecipeConfig] = None

    # Application Settings

    def get_app_settings(self) -> AppSettings:
        """Get application settings."""
        return self._settings.get_app_settings()

    def update_app_settings(self, **kwargs) -> None:
        """Update application settings."""
        settings = self.get_app_settings()

        for key, value in kwargs.items():
            if hasattr(settings, key):
                setattr(settings, key, value)

        # Validate
        result = self._validator.validate_app_settings(settings.to_dict())
        if not result.is_valid:
            raise ValidationError(f"Invalid settings: {', '.join(result.errors)}")

        self._settings.save_app_settings(settings)
        self._logger.info("Application settings updated")

    def add_recent_folder(self, folder_path: str) -> None:
        """Add a folder to recent folders list."""
        settings = self.get_app_settings()

        # Remove if already exists
        if folder_path in settings.recent_folders:
            settings.recent_folders.remove(folder_path)

        # Add to front
        settings.recent_folders.insert(0, folder_path)

        # Trim to max
        if len(settings.recent_folders) > settings.max_recent_folders:
            settings.recent_folders = settings.recent_folders[:settings.max_recent_folders]

        self._settings.save_app_settings(settings)

    def get_recent_folders(self) -> List[str]:
        """Get list of recent folders."""
        return self.get_app_settings().recent_folders

    # Recipe Management

    def list_recipes(self) -> List[str]:
        """Get list of all recipe names."""
        return self._settings.list_recipes()

    def get_recipe(self, name: str) -> Optional[Recipe]:
        """Get a recipe by name."""
        recipe_config = self._settings.get_recipe(name)
        if recipe_config is None:
            return None

        return Recipe(
            name=recipe_config.name,
            algorithm=recipe_config.algorithm,
            parameters=recipe_config.parameters,
            description=recipe_config.description
        )

    def get_current_recipe(self) -> Optional[RecipeConfig]:
        """Get the currently active recipe."""
        if self._current_recipe is None:
            current_name = self.get_app_settings().current_recipe
            self._current_recipe = self._settings.get_recipe(current_name)

            # If still None, use the first available recipe as default
            if self._current_recipe is None:
                recipes = self.list_recipes()
                if recipes:
                    self._current_recipe = self._settings.get_recipe(recipes[0])
                    # Update settings to remember this choice
                    if self._current_recipe:
                        self.update_app_settings(current_recipe=recipes[0])

        return self._current_recipe

    def create_recipe(
        self,
        name: str,
        algorithm: str,
        parameters: Dict[str, Any],
        description: str = ""
    ) -> Recipe:
        """Create a new recipe."""
        # Validate algorithm exists
        if algorithm not in AlgorithmRegistry.list_algorithms():
            raise ConfigurationError(f"Unknown algorithm: {algorithm}")

        # Validate parameters against algorithm definition
        algo_instance = AlgorithmRegistry.create_instance(algorithm)
        definitions = algo_instance.get_parameter_definitions()
        result = self._validator.validate_parameters(parameters, definitions)

        if not result.is_valid:
            raise ValidationError(f"Invalid parameters: {', '.join(result.errors)}")

        # Create and save
        recipe_config = RecipeConfig(
            name=name,
            algorithm=algorithm,
            parameters=parameters,
            description=description
        )

        self._settings.save_recipe(recipe_config)
        self._logger.info(f"Recipe created: {name}")

        return Recipe(
            name=name,
            algorithm=algorithm,
            parameters=parameters,
            description=description
        )

    def update_recipe(
        self,
        name: str,
        parameters: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None
    ) -> None:
        """Update an existing recipe."""
        recipe_config = self._settings.get_recipe(name)
        if recipe_config is None:
            raise ConfigurationError(f"Recipe not found: {name}")

        if parameters is not None:
            # Validate parameters
            algo_instance = AlgorithmRegistry.create_instance(recipe_config.algorithm)
            definitions = algo_instance.get_parameter_definitions()
            result = self._validator.validate_parameters(parameters, definitions)

            if not result.is_valid:
                raise ValidationError(f"Invalid parameters: {', '.join(result.errors)}")

            recipe_config.parameters = parameters

        if description is not None:
            recipe_config.description = description

        self._settings.save_recipe(recipe_config)
        self._logger.info(f"Recipe updated: {name}")

    def delete_recipe(self, name: str) -> None:
        """Delete a recipe."""
        self._settings.delete_recipe(name)
        self._logger.info(f"Recipe deleted: {name}")

    def duplicate_recipe(self, source_name: str, new_name: str) -> Recipe:
        """Duplicate an existing recipe."""
        source = self._settings.get_recipe(source_name)
        if source is None:
            raise ConfigurationError(f"Source recipe not found: {source_name}")

        new_recipe = RecipeConfig(
            name=new_name,
            algorithm=source.algorithm,
            parameters=source.parameters.copy(),
            description=f"Copy of {source_name}"
        )

        self._settings.save_recipe(new_recipe)
        self._logger.info(f"Recipe duplicated: {source_name} -> {new_name}")

        return Recipe(
            name=new_name,
            algorithm=new_recipe.algorithm,
            parameters=new_recipe.parameters,
            description=new_recipe.description
        )

    def set_current_recipe(self, name: str) -> None:
        """Set the current active recipe."""
        if name not in self.list_recipes():
            raise ConfigurationError(f"Recipe not found: {name}")

        self._current_recipe = self._settings.get_recipe(name)
        self.update_app_settings(current_recipe=name)
        self._logger.info(f"Current recipe set to: {name}")

    def import_recipe(self, source_path: str) -> str:
        """Import a recipe from file."""
        name = self._settings.import_recipe(source_path)
        self._logger.info(f"Recipe imported: {name}")
        return name

    def export_recipe(self, name: str, dest_path: str) -> None:
        """Export a recipe to file."""
        self._settings.export_recipe(name, dest_path)

    # Algorithm Integration

    def get_available_algorithms(self) -> List[Dict[str, str]]:
        """Get information about available algorithms."""
        return AlgorithmRegistry.get_all_info()

    def get_algorithm_parameters(self, algorithm_id: str) -> Dict[str, Dict[str, Any]]:
        """Get parameter definitions for an algorithm."""
        algo = AlgorithmRegistry.create_instance(algorithm_id)
        return algo.get_parameter_definitions()

    def create_detector(self, algorithm_id: Optional[str] = None) -> Any:
        """
        Create a detector instance.

        Args:
            algorithm_id: Algorithm ID, or None for current recipe's algorithm

        Returns:
            Detector instance
        """
        if algorithm_id is None:
            current = self.get_current_recipe()
            if current is None:
                algorithm_id = "hsv_detector"
            else:
                algorithm_id = current.algorithm

        return AlgorithmRegistry.create_instance(algorithm_id)

    # Configuration Conversion

    def recipe_to_detection_config(self, recipe: Recipe) -> DetectionConfig:
        """Convert a Recipe to DetectionConfig."""
        return DetectionConfig.from_dict(recipe.parameters)

    def detection_config_to_recipe(
        self,
        config: DetectionConfig,
        name: str,
        description: str = ""
    ) -> Recipe:
        """Convert DetectionConfig to Recipe."""
        return Recipe(
            name=name,
            algorithm="hsv_detector",
            parameters=config.to_dict(),
            description=description
        )
