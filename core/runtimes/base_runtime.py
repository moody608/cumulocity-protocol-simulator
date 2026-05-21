from abc import ABC, abstractmethod


class BaseRuntime(ABC):
    @abstractmethod
    async def run_forever(self) -> None:
        """Run the simulation loop indefinitely."""
