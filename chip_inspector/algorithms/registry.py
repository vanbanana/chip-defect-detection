"""
Algorithm registry for plugin management.
Allows dynamic registration and retrieval of detection algorithms.
"""
from typing import Dict, Type, Optional, List

from core.exceptions import AlgorithmError
from .base import BaseDetector


class AlgorithmRegistry:
    """
    Singleton registry for detection algorithms.

    Algorithms register themselves at import time using the @register decorator.
    """

    _instance = None
    _algorithms: Dict[str, Type[BaseDetector]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def register(cls, algorithm_class: Type[BaseDetector]) -> Type[BaseDetector]:
        """
        Register a detection algorithm class.

        Usage as decorator:
            @AlgorithmRegistry.register
            class MyDetector(BaseDetector):
                ...
        """
        # Create a temporary instance to get algorithm_id
        temp_instance = algorithm_class()
        algo_id = temp_instance.algorithm_id

        if algo_id in cls._algorithms:
            raise AlgorithmError(f"Algorithm '{algo_id}' is already registered")

        cls._algorithms[algo_id] = algorithm_class
        return algorithm_class

    @classmethod
    def get_algorithm(cls, algorithm_id: str) -> Optional[Type[BaseDetector]]:
        """Get an algorithm class by ID."""
        return cls._algorithms.get(algorithm_id)

    @classmethod
    def create_instance(cls, algorithm_id: str) -> BaseDetector:
        """
        Create a new instance of an algorithm.

        Args:
            algorithm_id: ID of the algorithm to instantiate

        Returns:
            New instance of the algorithm

        Raises:
            AlgorithmError: If algorithm not found
        """
        algorithm_class = cls.get_algorithm(algorithm_id)
        if algorithm_class is None:
            raise AlgorithmError(f"Algorithm '{algorithm_id}' not found")
        return algorithm_class()

    @classmethod
    def list_algorithms(cls) -> List[str]:
        """List all registered algorithm IDs."""
        return list(cls._algorithms.keys())

    @classmethod
    def get_algorithm_info(cls, algorithm_id: str) -> Optional[Dict[str, str]]:
        """
        Get information about an algorithm.

        Returns:
            Dict with 'id', 'name', 'description' or None
        """
        algorithm_class = cls.get_algorithm(algorithm_id)
        if algorithm_class is None:
            return None

        instance = algorithm_class()
        return {
            'id': instance.algorithm_id,
            'name': instance.algorithm_name,
            'description': instance.algorithm_description
        }

    @classmethod
    def get_all_info(cls) -> List[Dict[str, str]]:
        """Get information about all registered algorithms."""
        info_list = []
        for algo_id in cls.list_algorithms():
            info = cls.get_algorithm_info(algo_id)
            if info:
                info_list.append(info)
        return info_list


def get_algorithm(algorithm_id: str) -> Optional[BaseDetector]:
    """
    Convenience function to get an algorithm instance.

    Args:
        algorithm_id: ID of the algorithm

    Returns:
        New algorithm instance or None if not found
    """
    try:
        return AlgorithmRegistry.create_instance(algorithm_id)
    except AlgorithmError:
        return None


def register_algorithm(algorithm_class: Type[BaseDetector]) -> Type[BaseDetector]:
    """Decorator to register an algorithm."""
    return AlgorithmRegistry.register(algorithm_class)
