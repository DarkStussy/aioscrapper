import asyncio
from dataclasses import dataclass, field
from logging import Logger
from typing import Callable, Awaitable, Any

from aiohttp import ClientSession, BasicAuth, ClientTimeout, TCPConnector
from aiohttp.typedefs import StrOrURL, LooseCookies, LooseHeaders, Query
from aiojobs import Scheduler

from .config import SessionConfig
from .exceptions import RequestException, HTTPException
from .utils import get_cb_kwargs


@dataclass(slots=True)
class Request:
    url: StrOrURL
    method: str
    callback: Callable[..., Awaitable] | None = None
    cb_kwargs: dict[str, Any] | None = None
    errback: Callable[..., Awaitable] | None = None
    params: Query = None
    data: Any = None
    json: Any = None
    cookies: LooseCookies | None = None
    headers: LooseHeaders | None = None
    proxy: StrOrURL | None = None
    proxy_auth: BasicAuth | None = None
    timeout: ClientTimeout | None = None
    proxy_headers: LooseHeaders | None = None


@dataclass(slots=True, order=True)
class PrioritizedRequest:
    priority: int
    request: Request | None = field(compare=False)


class SendRequest:
    def __init__(self, queue: asyncio.PriorityQueue[PrioritizedRequest]):
        self._queue = queue

    async def __call__(
        self,
        url: StrOrURL,
        method: str = "GET",
        callback: Callable[..., Awaitable] | None = None,
        cb_kwargs: dict[str, Any] | None = None,
        errback: Callable[..., Awaitable] | None = None,
        params: Query = None,
        data: Any = None,
        json: Any = None,
        cookies: LooseCookies | None = None,
        headers: LooseHeaders | None = None,
        proxy: StrOrURL | None = None,
        proxy_auth: BasicAuth | None = None,
        timeout: ClientTimeout | None = None,
        proxy_headers: LooseHeaders | None = None,
        priority: int = 0,
        delay: float | None = None,
    ) -> None:
        await self._queue.put(
            PrioritizedRequest(
                priority=priority,
                request=Request(
                    method=method,
                    url=url,
                    callback=callback,
                    cb_kwargs=cb_kwargs,
                    errback=errback,
                    params=params,
                    data=data,
                    json=json,
                    cookies=cookies,
                    headers=headers,
                    proxy=proxy,
                    proxy_auth=proxy_auth,
                    timeout=timeout,
                    proxy_headers=proxy_headers,
                ),
            )
        )
        if delay:
            await asyncio.sleep(delay)


class Session:
    def __init__(self, logger: Logger, config: SessionConfig, scheduler: Scheduler, srv_kwargs: dict[str, Any]) -> None:
        self._logger = logger
        self._config = config
        self._scheduler = scheduler
        self._client = ClientSession(
            timeout=ClientTimeout(total=config.timeout),
            connector=TCPConnector(ssl=config.ssl),
        )
        self._queue: asyncio.PriorityQueue[PrioritizedRequest] = asyncio.PriorityQueue()
        self._send_request = SendRequest(self._queue)
        self._srv_kwargs = {"send_request": self._send_request, **srv_kwargs}

    @property
    def queue(self) -> asyncio.PriorityQueue[PrioritizedRequest]:
        return self._queue

    @property
    def send_request(self) -> SendRequest:
        return self._send_request

    async def _request(self, request: Request):
        self._logger.debug(f"request: {request.method} {request.url}")
        try:
            async with self._client.request(
                url=request.url,
                method=request.method,
                params=request.params,
                data=request.data,
                cookies=request.cookies,
                headers=request.headers,
                proxy=request.proxy,
                proxy_auth=request.proxy_auth,
                proxy_headers=request.proxy_headers,
                timeout=request.timeout,
            ) as response:
                if response.status >= 400:
                    output_exc = HTTPException(
                        status_code=response.status,
                        message=await response.text(),
                        request_info=response.request_info,
                    )
                    if request.errback is None:
                        raise output_exc

                    await request.errback(
                        output_exc,
                        **get_cb_kwargs(request.errback, srv_kwargs=self._srv_kwargs, cb_kwargs=request.cb_kwargs),
                    )
                elif request.callback is not None:
                    await request.callback(
                        response,
                        **get_cb_kwargs(request.callback, srv_kwargs=self._srv_kwargs, cb_kwargs=request.cb_kwargs),
                    )
        except Exception as exc:
            output_exc = RequestException(exc, request.url, request.method)
            if request.errback is None:
                raise output_exc

            await request.errback(
                output_exc,
                **get_cb_kwargs(request.errback, srv_kwargs=self._srv_kwargs, cb_kwargs=request.cb_kwargs),
            )

    async def start(self):
        while (request := (await self._queue.get()).request) is not None:
            await self._scheduler.spawn(self._request(request))
            if self._config.request_delay > 0:
                await asyncio.sleep(self._config.request_delay)

    async def shutdown(self):
        await self._queue.put(PrioritizedRequest(priority=-999, request=None))

    async def close(self) -> None:
        await self._client.close()
