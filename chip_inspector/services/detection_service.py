"""
Detection service - Business logic for chip defect detection.
Orchestrates algorithm execution with parameter management and result handling.
"""
from typing import List, Optional, Dict, Any, Callable
from pathlib import Path
from datetime import datetime
import time

from core.models import InspectionResult, Recipe, BatchProgress
from core.enums import DetectionStatus, ProcessingStatus
from core.exceptions import AlgorithmError, ImageLoadError
from algorithms.registry import AlgorithmRegistry
from services.result_service import ResultService
from services.config_service import ConfigService
from utils.logger import get_logger
from utils.image_utils import get_image_files
from utils.validators import validate_image_path


class DetectionService:
    """
    High-level detection service.

    Features:
    - Single image detection
    - Batch processing with progress tracking
    - Parameter management
    - Result persistence
    """

    def __init__(
        self,
        config_service: ConfigService,
        result_service: ResultService
    ):
        self._config = config_service
        self._results = result_service
        self._logger = get_logger(__name__)

        # Processing state
        self._status = ProcessingStatus.IDLE
        self._should_stop = False

    @property
    def status(self) -> ProcessingStatus:
        """Get current processing status."""
        return self._status

    def detect_single(
        self,
        image_path: str,
        recipe: Optional[Recipe] = None,
        save_result: bool = True
    ) -> InspectionResult:
        """
        Run detection on a single image.

        Args:
            image_path: Path to image file
            recipe: Recipe to use, or None for current recipe
            save_result: Whether to save result to database

        Returns:
            InspectionResult

        Raises:
            ImageLoadError: If image cannot be loaded
            AlgorithmError: If detection fails
        """
        # Validate image path
        is_valid, error = validate_image_path(image_path)
        if not is_valid:
            raise ImageLoadError(error)

        # Get recipe
        if recipe is None:
            recipe = self._config.get_current_recipe()
            if recipe is None:
                raise AlgorithmError("No current recipe set")

        # Create detector with recipe parameters
        detector = AlgorithmRegistry.create_instance(recipe.algorithm)
        detector.set_parameters(recipe.parameters)

        # Run detection
        try:
            from algorithms.base import DetectionResult
            algo_result = detector.detect(image_path)

            # Create inspection result
            image_name = Path(image_path).name

            result = InspectionResult(
                image_path=image_path,
                image_name=image_name,
                status=algo_result.status,
                defect_area=algo_result.defect_area,
                timestamp=datetime.now(),
                recipe_name=recipe.name,
                parameters=detector.get_parameters(),
                processing_time_ms=algo_result.processing_time_ms,
                original_image=algo_result.original_image,
                result_image=algo_result.result_image,
                metadata=algo_result.metadata
            )

            # Save to database if requested
            if save_result:
                self._results.save_inspection(result)

            self._logger.info(
                f"Detection complete: {image_name} - "
                f"{result.status.name} (area: {result.defect_area:.1f})"
            )

            return result

        except Exception as e:
            self._logger.error(f"Detection failed for {image_path}: {str(e)}")
            raise AlgorithmError(f"Detection failed: {str(e)}")

    def detect_batch(
        self,
        image_paths: List[str],
        recipe: Optional[Recipe] = None,
        progress_callback: Optional[Callable[[BatchProgress], None]] = None,
        result_callback: Optional[Callable[[InspectionResult], None]] = None,
        save_results: bool = True
    ) -> List[InspectionResult]:
        """
        Run detection on multiple images.

        Args:
            image_paths: List of image paths
            recipe: Recipe to use, or None for current recipe
            progress_callback: Called with progress updates
            result_callback: Called for each result
            save_results: Whether to save results to database

        Returns:
            List of InspectionResult
        """
        if not image_paths:
            return []

        # Get recipe
        if recipe is None:
            recipe = self._config.get_current_recipe()
            if recipe is None:
                raise AlgorithmError("No current recipe set")

        # Setup batch processing
        self._status = ProcessingStatus.RUNNING
        self._should_stop = False

        results = []
        progress = BatchProgress(total=len(image_paths), completed=0)

        # Create detector once
        detector = AlgorithmRegistry.create_instance(recipe.algorithm)
        detector.set_parameters(recipe.parameters)

        try:
            for i, image_path in enumerate(image_paths):
                if self._should_stop:
                    self._logger.info("Batch processing stopped by user")
                    break

                # Validate
                is_valid, error = validate_image_path(image_path)
                if not is_valid:
                    self._logger.warning(f"Skipping invalid image: {image_path} - {error}")
                    continue

                # Update progress
                progress.completed = i
                progress.current_file = Path(image_path).name

                # Detect
                try:
                    algo_result = detector.detect(image_path)

                    result = InspectionResult(
                        image_path=image_path,
                        image_name=Path(image_path).name,
                        status=algo_result.status,
                        defect_area=algo_result.defect_area,
                        timestamp=datetime.now(),
                        recipe_name=recipe.name,
                        parameters=detector.get_parameters(),
                        processing_time_ms=algo_result.processing_time_ms,
                        original_image=algo_result.original_image,
                        result_image=algo_result.result_image,
                        metadata=algo_result.metadata
                    )

                    results.append(result)

                    # Update statistics
                    if result.is_ok:
                        progress.ok_count += 1
                    else:
                        progress.ng_count += 1

                    # Save if requested
                    if save_results:
                        self._results.save_inspection(result)

                    # Callbacks
                    if result_callback:
                        result_callback(result)

                    if progress_callback:
                        progress_callback(progress)

                except Exception as e:
                    self._logger.error(f"Detection failed for {image_path}: {str(e)}")
                    continue

            self._status = ProcessingStatus.COMPLETED
            self._logger.info(
                f"Batch complete: {len(results)}/{len(image_paths)} processed, "
                f"{progress.ok_count} OK, {progress.ng_count} NG"
            )

            return results

        except Exception as e:
            self._status = ProcessingStatus.ERROR
            self._logger.error(f"Batch processing error: {str(e)}")
            raise AlgorithmError(f"Batch processing failed: {str(e)}")

    def detect_folder(
        self,
        folder_path: str,
        recipe: Optional[Recipe] = None,
        progress_callback: Optional[Callable[[BatchProgress], None]] = None,
        result_callback: Optional[Callable[[InspectionResult], None]] = None,
        save_results: bool = True,
        recursive: bool = False
    ) -> List[InspectionResult]:
        """
        Run detection on all images in a folder.

        Args:
            folder_path: Path to folder
            recipe: Recipe to use
            progress_callback: Called with progress updates
            result_callback: Called for each result
            save_results: Whether to save results
            recursive: Whether to search subdirectories

        Returns:
            List of InspectionResult
        """
        # Get image files
        image_paths = get_image_files(folder_path, recursive)

        if not image_paths:
            self._logger.warning(f"No images found in: {folder_path}")
            return []

        self._logger.info(f"Found {len(image_paths)} images in {folder_path}")

        # Add to recent folders
        self._config.add_recent_folder(folder_path)

        # Run batch detection
        return self.detect_batch(
            image_paths=image_paths,
            recipe=recipe,
            progress_callback=progress_callback,
            result_callback=result_callback,
            save_results=save_results
        )

    def stop(self) -> None:
        """Stop current batch processing."""
        self._should_stop = True
        self._logger.info("Stop requested")

    def get_detector(self, algorithm_id: Optional[str] = None) -> Any:
        """
        Get a detector instance.

        Args:
            algorithm_id: Algorithm ID, or None for current

        Returns:
            Detector instance
        """
        return self._config.create_detector(algorithm_id)

    # Quick detection for UI preview (without saving)

    def preview_detection(
        self,
        image_path: str,
        parameters: Dict[str, Any]
    ) -> InspectionResult:
        """
        Quick detection for UI parameter preview (not saved).

        Args:
            image_path: Path to image
            parameters: Detection parameters

        Returns:
            InspectionResult (not saved to database)
        """
        # Get current recipe's algorithm
        current = self._config.get_current_recipe()
        algorithm = current.algorithm if current else "hsv_detector"

        # Create detector
        detector = AlgorithmRegistry.create_instance(algorithm)
        detector.set_parameters(parameters)

        # Detect
        algo_result = detector.detect(image_path)

        return InspectionResult(
            image_path=image_path,
            image_name=Path(image_path).name,
            status=algo_result.status,
            defect_area=algo_result.defect_area,
            timestamp=datetime.now(),
            recipe_name="Preview",
            parameters=parameters,
            processing_time_ms=algo_result.processing_time_ms,
            original_image=algo_result.original_image,
            result_image=algo_result.result_image,
            metadata=algo_result.metadata
        )
