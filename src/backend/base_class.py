from abc import ABC, abstractmethod


class Stream(ABC):
    @abstractmethod
    def is_connected(self) -> bool:
        pass

    @abstractmethod
    def start(self) -> None:
        pass
