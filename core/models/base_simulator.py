from abc import ABC, abstractmethod

from core.models.base import AssetState


class BaseSimulator(ABC):
    @abstractmethod
    def tick(self) -> AssetState:
        """Generate one tick of simulated state."""
