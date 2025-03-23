import asyncio
from logging import Logger
from typing import Callable, Awaitable, Any, Coroutine
from urllib.parse import urlencode

from .exceptions import HTTPException, RequestException
from .helpers import get_cb_kwargs
from .middleware import RequestOuterMiddleware, RequestInnerMiddleware, ResponseMiddleware
from .request_sender import RequestSender
from .session.base import BaseSession
from .types import Request, RequestParams, RequestQueue


class RequestWorker:
    def __init__(
        self,
        logger: Logger,
        session: BaseSession,
        schedule_request: Callable[[Coroutine], Awaitable],
        sender: RequestSender,
        queue: RequestQueue,
        delay: float,
        shutdown_timeout: float,
        srv_kwargs: dict[str, Any],
        request_outer_middlewares: list[RequestOuterMiddleware] | None = None,
        request_inner_middlewares: list[RequestInnerMiddleware] | None = None,
        response_middlewares: list[ResponseMiddleware] | None = None,
    ) -> None:
        self._logger = logger
        self._session = session
        self._schedule_request = schedule_request
        self._queue = queue
        self._delay = delay
        self._shutdown_timeout = shutdown_timeout
        self._srv_kwargs = {"send_request": sender, **srv_kwargs}
        self._request_outer_middlewares = request_outer_middlewares or []
        self._request_inner_middlewares = request_inner_middlewares or []
        self._response_middlewares = response_middlewares or []
        self._task: asyncio.Task | None = None

    async def _send_request(self, request: Request, params: RequestParams) -> None:
        for inner_middleware in self._request_inner_middlewares:
            await inner_middleware(request, params)

        full_url = f"{request.url}{urlencode(request.params or {})}"
        self._logger.debug(f"request: {request.method} {full_url}")

        response = await self._session.make_request(request)
        for response_middleware in self._response_middlewares:
            await response_middleware(params, response)

        if response.exception is not None:
            output_exc = RequestException(
                inner_exc=response.exception,
                url=full_url,
                method=response.method,
            )
        elif response.status is not None and response.status >= 400:
            output_exc = HTTPException(
                status_code=response.status,
                message=response.text(),
                url=full_url,
                method=response.method,
            )
        else:
            output_exc = None

        if output_exc is not None:
            if params.errback is None:
                raise output_exc

            await params.errback(
                output_exc,
                **get_cb_kwargs(params.errback, srv_kwargs=self._srv_kwargs, cb_kwargs=params.cb_kwargs),
            )
        elif response.status is not None and params.callback is not None:
            await params.callback(
                response,
                **get_cb_kwargs(params.callback, srv_kwargs=self._srv_kwargs, cb_kwargs=params.cb_kwargs),
            )

    def listen_queue(self) -> None:
        self._task = asyncio.create_task(self._listen_queue())

    async def _listen_queue(self) -> None:
        while (r := (await self._queue.get())) is not None:
            for outer_middleware in self._request_outer_middlewares:
                await outer_middleware(r.request, r.request_params)

            await self._schedule_request(self._send_request(r.request, r.request_params))
            await asyncio.sleep(self._delay)

    async def shutdown(self, force: bool = False) -> None:
        await self._queue.put(None)
        if self._task is not None:
            await asyncio.wait_for(self._task, timeout=self._shutdown_timeout) if force else await self._task

    async def close(self) -> None:
        await self._session.close()
