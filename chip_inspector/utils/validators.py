"""
Validation utility functions.
"""
from typing import Dict, Any, List, Optional


def validate_parameters(
    params: Dict[str, Any],
    definitions: Dict[str, Dict[str, Any]]
) -> tuple[bool, List[str]]:
    """
    Validate parameters against their definitions.

    Args:
        params: Parameter values to validate
        definitions: Parameter definitions with constraints

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []

    for name, definition in definitions.items():
        if name not in params:
            if definition.get('required', False):
                errors.append(f"Missing required parameter: {name}")
            continue

        value = params[name]
        param_type = definition.get('type')

        # Type validation
        if param_type == 'int':
            if not isinstance(value, int):
                try:
                    value = int(value)
                except (ValueError, TypeError):
                    errors.append(f"Parameter '{name}' must be an integer")
                    continue
        elif param_type == 'float':
            if not isinstance(value, (int, float)):
                try:
                    value = float(value)
                except (ValueError, TypeError):
                    errors.append(f"Parameter '{name}' must be a number")
                    continue

        # Range validation
        min_val = definition.get('min')
        max_val = definition.get('max')

        if min_val is not None and value < min_val:
            errors.append(
                f"Parameter '{name}' ({value}) below minimum ({min_val})"
            )

        if max_val is not None and value > max_val:
            errors.append(
                f"Parameter '{name}' ({value}) above maximum ({max_val})"
            )

    return len(errors) == 0, errors


def validate_image_path(image_path: str) -> tuple[bool, Optional[str]]:
    """
    Validate an image file path.

    Args:
        image_path: Path to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    from pathlib import Path
    from core.constants import IMAGE_EXTENSIONS

    if not image_path:
        return False, "Image path is empty"

    path = Path(image_path)

    if not path.exists():
        return False, f"File does not exist: {image_path}"

    if not path.is_file():
        return False, f"Path is not a file: {image_path}"

    if path.suffix.lower() not in IMAGE_EXTENSIONS:
        return False, f"Unsupported image format: {path.suffix}"

    return True, None


def validate_recipe_name(name: str) -> tuple[bool, Optional[str]]:
    """
    Validate a recipe name.

    Args:
        name: Recipe name to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not name:
        return False, "Recipe name cannot be empty"

    if len(name) > 100:
        return False, "Recipe name too long (max 100 characters)"

    # Check for invalid characters
    invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    for char in invalid_chars:
        if char in name:
            return False, f"Recipe name contains invalid character: {char}"

    return True, None


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing invalid characters.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    result = filename
    for char in invalid_chars:
        result = result.replace(char, '_')
    return result
