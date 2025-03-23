import abc
from typing import Type

from ..types import Request, Response


class BaseSession(abc.ABC):
    def __init__(self, timeout: float | None = None, ssl: bool | None = None):
        self._timeout = timeout
        self._ssl = ssl

    @abc.abstractmethod
    async def make_request(self, request: Request) -> Response: ...

    async def close(self) -> None: ...


def get_session_wrapper(session: str | None) -> Type[BaseSession]:
    if session == "aiohttp" or session is None:
        try:
            import aiohttp
        except ImportError:
            pass
        else:
            from .aiohttp import AiohttpSession

            return AiohttpSession
    if session == "httpx" or session is None:
        try:
            import httpx
        except ImportError:
            pass
        else:
            from .httpx import HttpxSession

            return HttpxSession

    raise RuntimeError("Async http session_old heeded. Please install aiohttp or httpx")
