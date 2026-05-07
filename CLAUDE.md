# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **Industrial Chip Defect Detection System** (工业芯片缺陷检测系统) - a production environment vision inspection application. The system detects dark/stain defects on chip surfaces using HSV color segmentation in a safe detection zone.

### Core Detection Algorithm
1. **Chip Localization**: HSV color filtering (`h_min`~`h_max`, `s_min`) to find the chip region
2. **Safe Zone Definition**: Erode the chip contour by `margin` pixels to create defect-free boundary
3. **Defect Detection**: Find dark areas (`v_thresh` threshold) within the safe zone
4. **Decision**: NG if total defect area > `area_max`, ignoring blobs smaller than `min_blob`

## Architecture (Current - Monolithic)

**Current State**: All code in single `test3.py` file (~520 lines)

```
test3.py
├── UI Components (NoWheelSlider, SmartSlider, CanvasWidget)
├── Core Algorithm (CoreAlgo, InspectRes, Worker thread)
├── Main Window (MainWindow with 2 tabs: RUN, GALLERY)
└── Configuration management (JSON files in configs/)
```

## Running the Application

```bash
# Install dependencies
pip install PySide6 opencv-python numpy

# Run the application
python test3.py
```

## Configuration System

- **Location**: `configs/` directory
- **Format**: JSON files, one per recipe/preset
- **Parameters**:
  - `h_min`, `h_max`: Hue range for chip detection (HSV)
  - `s_min`: Minimum saturation for chip detection
  - `v_thresh`: Brightness threshold for defect detection (lower = detect more)
  - `area_max`: Maximum allowed defect area (NG if exceeded)
  - `margin`: Erosion margin from chip edge (safe zone)
  - `min_blob`: Minimum noise blob size to ignore

## Key UI Components

- **CanvasWidget**: High-performance image display widget with zoom (mouse wheel)
- **SmartSlider**: Combined slider+spinbox with bidirectional sync
- **NoWheel*** variants: Input widgets that ignore scroll wheel (prevent accidental changes)

## Planned Refactoring Goals

To transform this into a proper industrial software architecture:

1. **Separation of Concerns**: Split UI, algorithm, and business logic
2. **Config Management**: Centralized configuration with validation
3. **Plugin Architecture**: Support multiple detection algorithms
4. **Logging System**: Industrial-grade logging for traceability
5. **Result Database**: SQLite/CSV export for quality tracking
