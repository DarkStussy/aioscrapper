from abc import ABC, abstractmethod

from ..request_sender import RequestSender


class BaseScrapper(ABC):
    @abstractmethod
    async def start(self, request_sender: RequestSender) -> None: ...

    async def initialize(self) -> None: ...

    async def close(self) -> None: ...
