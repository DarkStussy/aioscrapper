import asyncio
import logging
from typing import Callable, Awaitable, Any, Mapping

from aiohttp import ClientSession, BasicAuth, ClientTimeout, TCPConnector
from aiohttp.typedefs import StrOrURL, LooseCookies, LooseHeaders
from aiojobs import Scheduler

from .config.models import SessionConfig
from .exceptions import RequestException, HTTPException
from .models import Request
from .models.request import HttpMethod, PrioritizedRequest

logger = logging.getLogger(__name__)


class Session:
    def __init__(self, config: SessionConfig, scheduler: Scheduler) -> None:
        self._config = config
        self._scheduler = scheduler
        self._client = ClientSession(
            timeout=ClientTimeout(total=config.timeout),
            connector=TCPConnector(ssl=config.ssl),
        )
        self._queue: asyncio.PriorityQueue[PrioritizedRequest] = asyncio.PriorityQueue()

    @property
    def queue(self) -> asyncio.PriorityQueue[PrioritizedRequest]:
        return self._queue

    async def _request(self, request: Request):
        logger.debug(f"request: {request.method} {request.url}")
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
                        request=request,
                        request_info=response.request_info,
                    )
                    if request.errback is not None:
                        await request.errback(output_exc, **(request.cb_kwargs or {}))
                    else:
                        raise output_exc
                elif request.callback is not None:
                    await request.callback(response, **(request.cb_kwargs or {}))

        except Exception as exc:
            output_exc = RequestException(exc, request)
            if request.errback is not None:
                await request.errback(output_exc, **(request.cb_kwargs or {}))
            else:
                raise output_exc

    async def listen_queue(self):
        while True:
            await self._scheduler.spawn(self._request((await self._queue.get()).request))
            if self._config.request_delay > 0:
                await asyncio.sleep(self._config.request_delay)

    async def close(self) -> None:
        await self._client.close()


class SendRequest:
    def __init__(self, queue: asyncio.PriorityQueue[PrioritizedRequest]):
        self._queue = queue

    async def __call__(
        self,
        url: StrOrURL,
        method: HttpMethod = "GET",
        callback: Callable[..., Awaitable] | None = None,
        cb_kwargs: dict[str, Any] | None = None,
        errback: Callable[..., Awaitable] | None = None,
        params: Mapping[str, str | int] | str | None = None,
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