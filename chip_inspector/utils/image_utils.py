"""
Image utility functions.
"""
from pathlib import Path
from typing import List, Optional

from core.constants import IMAGE_EXTENSIONS
from core.exceptions import ImageLoadError


def get_image_files(directory: str, recursive: bool = False) -> List[str]:
    """
    Get all image files from a directory.

    Args:
        directory: Path to directory
        recursive: Whether to search subdirectories

    Returns:
        List of image file paths (sorted)
    """
    dir_path = Path(directory)
    if not dir_path.exists() or not dir_path.is_dir():
        return []

    if recursive:
        files = list(dir_path.rglob('*'))
    else:
        files = list(dir_path.glob('*'))

    # Filter and sort
    image_files = [
        str(f) for f in files
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
    ]

    return sorted(image_files)


def load_image(image_path: str) -> Optional[bytes]:
    """
    Load an image file as bytes.

    Args:
        image_path: Path to image file

    Returns:
        Image data as bytes or None if failed
    """
    try:
        with open(image_path, 'rb') as f:
            return f.read()
    except Exception as e:
        raise ImageLoadError(f"Failed to load image: {str(e)}")


def validate_image_path(image_path: str) -> bool:
    """
    Validate that a path points to a valid image file.

    Args:
        image_path: Path to validate

    Returns:
        True if valid image file, False otherwise
    """
    path = Path(image_path)
    if not path.exists() or not path.is_file():
        return False
    return path.suffix.lower() in IMAGE_EXTENSIONS


def get_image_info(image_path: str) -> Optional[dict]:
    """
    Get basic information about an image file.

    Args:
        image_path: Path to image file

    Returns:
        Dict with 'name', 'size', 'extension', or None
    """
    path = Path(image_path)
    if not path.exists():
        return None

    return {
        'name': path.stem,
        'full_name': path.name,
        'size': path.stat().st_size,
        'extension': path.suffix,
        'path': str(path)
    }
