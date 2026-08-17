from abc import ABC, abstractmethod

class Stream:
    @abstractmethod
    def is_connected(self) -> bool:
        pass

    @abstractmethod
    def start(self) -> None:
        pass