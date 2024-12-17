from abc import ABC, abstractmethod

from .session import SendRequest


class BaseScrapper(ABC):
    @abstractmethod
    async def start(self, send_request: SendRequest) -> None: ...

    async def initialize(self) -> None: ...

    async def close(self) -> None: ...
