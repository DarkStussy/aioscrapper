import abc

from .types import Request, RequestParams, Response


class RequestOuterMiddleware(abc.ABC):
    @abc.abstractmethod
    async def __call__(self, request: Request, params: RequestParams) -> None: ...


class RequestInnerMiddleware(abc.ABC):
    @abc.abstractmethod
    async def __call__(self, request: Request, params: RequestParams) -> None: ...


class ResponseMiddleware(abc.ABC):
    @abc.abstractmethod
    async def __call__(self, params: RequestParams, response: Response) -> None: ...
