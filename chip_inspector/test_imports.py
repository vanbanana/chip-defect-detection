"""
Test script to verify all module imports work correctly.
Run this to check if the application is properly set up.
"""
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_imports():
    """Test all module imports."""
    print("=" * 60)
    print("Testing Chip Inspector Imports")
    print("=" * 60)

    # Test core modules
    print("\n1. Testing core modules...")
    try:
        from core import models, enums, exceptions, constants
        print("   [OK] core.models")
        print("   [OK] core.enums")
        print("   [OK] core.exceptions")
        print("   [OK] core.constants")
    except Exception as e:
        print(f"   [FAIL] Error importing core: {e}")
        return False

    # Test algorithms
    print("\n2. Testing algorithms...")
    try:
        from algorithms import base, registry, hsv_detector
        print("   [OK] algorithms.base")
        print("   [OK] algorithms.registry")
        print("   [OK] algorithms.hsv_detector")

        # Verify algorithm is registered
        from algorithms.registry import AlgorithmRegistry
        algos = AlgorithmRegistry.list_algorithms()
        print(f"   [OK] Registered algorithms: {algos}")
    except Exception as e:
        print(f"   [FAIL] Error importing algorithms: {e}")
        return False

    # Test utils
    print("\n3. Testing utils...")
    try:
        from utils import logger, validators, image_utils
        print("   [OK] utils.logger")
        print("   [OK] utils.validators")
        print("   [OK] utils.image_utils")
    except Exception as e:
        print(f"   [FAIL] Error importing utils: {e}")
        return False

    # Test config
    print("\n4. Testing config...")
    try:
        from config import settings, validation
        print("   [OK] config.settings")
        print("   [OK] config.validation")
    except Exception as e:
        print(f"   [FAIL] Error importing config: {e}")
        return False

    # Test data
    print("\n5. Testing data...")
    try:
        from data import database, repositories
        print("   [OK] data.database")
        print("   [OK] data.repositories")
    except Exception as e:
        print(f"   [FAIL] Error importing data: {e}")
        return False

    # Test services
    print("\n6. Testing services...")
    try:
        from services import (
            detection_service, image_service, result_service,
            export_service, config_service
        )
        print("   [OK] services.detection_service")
        print("   [OK] services.image_service")
        print("   [OK] services.result_service")
        print("   [OK] services.export_service")
        print("   [OK] services.config_service")
    except Exception as e:
        print(f"   [FAIL] Error importing services: {e}")
        return False

    # Note: Skipping UI imports as they require PySide6 and a display
    print("\n7. Skipping UI modules (requires display server)...")

    print("\n" + "=" * 60)
    print("[OK] All non-UI imports successful!")
    print("=" * 60)
    return True


def test_algorithm():
    """Test the HSV detector algorithm."""
    print("\n8. Testing HSV detector...")

    try:
        from algorithms.registry import AlgorithmRegistry

        # Create detector
        detector = AlgorithmRegistry.create_instance("hsv_detector")
        print(f"   [OK] Created detector: {detector.algorithm_name}")

        # Get parameters
        params = detector.get_default_parameters()
        print(f"   [OK] Default parameters: {list(params.keys())}")

        # Get parameter definitions
        definitions = detector.get_parameter_definitions()
        print(f"   [OK] Parameter definitions: {len(definitions)} parameters")

        return True
    except Exception as e:
        print(f"   [FAIL] Error testing algorithm: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_imports()
    if success:
        test_algorithm()

        print("\n[OK] Import test complete!")
        print("\nTo run the application:")
        print("  python main.py")
    else:
        print("\n[FAIL] Import test failed!")
        print("\nPlease check that all dependencies are installed:")
        print("  pip install -r requirements.txt")
        sys.exit(1)
