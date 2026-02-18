from abc import ABC, abstractmethod


class DataStorage(ABC):

    @abstractmethod
    async def save(self, data: dict) -> None:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass
