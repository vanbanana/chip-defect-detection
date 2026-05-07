"""
Configuration validation utilities.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from core.exceptions import ConfigurationError


@dataclass
class ValidationResult:
    """Result of configuration validation."""
    is_valid: bool
    errors: List[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class ConfigValidator:
    """Validator for configuration data."""

    @staticmethod
    def validate_app_settings(settings: Dict[str, Any]) -> ValidationResult:
        """Validate application settings."""
        errors = []
        warnings = []

        # Window size validation
        if settings.get('window_width', 0) < 800:
            errors.append("Window width too small (min 800px)")

        if settings.get('window_height', 0) < 600:
            errors.append("Window height too small (min 600px)")

        # Log level validation
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        log_level = settings.get('log_level', 'INFO')
        if log_level not in valid_levels:
            errors.append(f"Invalid log level: {log_level}")

        # Export format validation
        valid_formats = ['csv', 'excel', 'json']
        export_format = settings.get('default_export_format', 'csv')
        if export_format not in valid_formats:
            errors.append(f"Invalid export format: {export_format}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    @staticmethod
    def validate_recipe_config(config: Dict[str, Any]) -> ValidationResult:
        """Validate recipe configuration."""
        errors = []
        warnings = []

        # Required fields
        if 'name' not in config or not config['name']:
            errors.append("Recipe name is required")

        if 'algorithm' not in config:
            errors.append("Algorithm is required")
        elif config['algorithm'] not in ['hsv_detector']:  # Add more as available
            warnings.append(f"Unknown algorithm: {config['algorithm']}")

        if 'parameters' not in config:
            errors.append("Parameters are required")
        elif not isinstance(config['parameters'], dict):
            errors.append("Parameters must be a dictionary")

        # Validate parameter ranges for HSV detector
        if config.get('algorithm') == 'hsv_detector':
            params = config.get('parameters', {})
            ConfigValidator._validate_hsv_parameters(params, errors)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    @staticmethod
    def _validate_hsv_parameters(params: Dict[str, Any], errors: List[str]):
        """Validate HSV-specific parameters."""
        validations = {
            'h_min': (0, 180),
            'h_max': (0, 180),
            's_min': (0, 255),
            's_max': (0, 255),
            'v_min': (0, 255),
            'v_max': (0, 255),
            'stain_v_thresh': (1, 255),
            'max_total_area': (10, 2000),
            'min_blob': (0, 50),
            'safe_margin': (0, 50)
        }

        for param, (min_val, max_val) in validations.items():
            if param in params:
                value = params[param]
                if not isinstance(value, (int, float)):
                    errors.append(f"Parameter {param} must be a number")
                elif value < min_val or value > max_val:
                    errors.append(f"Parameter {param} out of range [{min_val}, {max_val}]")

    @staticmethod
    def validate_parameters(
        params: Dict[str, Any],
        definitions: Dict[str, Dict[str, Any]]
    ) -> ValidationResult:
        """
        Validate parameters against their definitions.

        Args:
            params: Parameter values to validate
            definitions: Parameter definitions with constraints

        Returns:
            ValidationResult with any errors found
        """
        errors = []

        for name, definition in definitions.items():
            # Required parameters
            if definition.get('required', False) and name not in params:
                errors.append(f"Missing required parameter: {name}")
                continue

            if name not in params:
                continue

            value = params[name]

            # Type validation
            param_type = definition.get('type')
            if param_type == 'int':
                if not isinstance(value, int):
                    try:
                        int(value)
                    except (ValueError, TypeError):
                        errors.append(f"{name}: must be an integer")
            elif param_type == 'float':
                if not isinstance(value, (int, float)):
                    try:
                        float(value)
                    except (ValueError, TypeError):
                        errors.append(f"{name}: must be a number")

            # Range validation
            if 'min' in definition and value < definition['min']:
                errors.append(f"{name}: value {value} below minimum {definition['min']}")

            if 'max' in definition and value > definition['max']:
                errors.append(f"{name}: value {value} above maximum {definition['max']}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors
        )
