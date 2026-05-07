"""
Application constants.
"""
import os
from pathlib import Path

# Application info
APP_NAME = "ChipInspector"
APP_VERSION = "2.0.0"
APP_DISPLAY_NAME = "工业芯片缺陷检测系统"

# Directory paths
DEFAULT_CONFIG_DIR = "config"
DEFAULT_DATA_DIR = "data"
DEFAULT_LOG_DIR = "logs"
DEFAULT_RECIPE_DIR = "config/recipes"

# Database
DATABASE_NAME = "inspections.db"
DATABASE_BACKUP_DIR = "data/backups"

# Logging
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# File patterns
IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
RECIPE_EXTENSION = '.json'

# UI Constants
DEFAULT_WINDOW_WIDTH = 1600
DEFAULT_WINDOW_HEIGHT = 950
MIN_WINDOW_WIDTH = 1200
MIN_WINDOW_HEIGHT = 700

# Canvas display
ZOOM_MIN = 0.1
ZOOM_MAX = 10.0
ZOOM_STEP = 1.1

# Status colors (hex)
COLOR_OK = "#00C853"      # Green
COLOR_NG = "#D50000"      # Red
COLOR_WARNING = "#FF6D00" # Amber
COLOR_INFO = "#00B0FF"    # Blue
COLOR_READY = "#555555"   # Gray
COLOR_RUNNING = "#FF9800" # Orange

# Industrial UI dimensions
BUTTON_MIN_HEIGHT = 44
STATUS_MIN_HEIGHT = 100
STATUS_FONT_SIZE = 60
CONTROL_PANEL_WIDTH = 380
