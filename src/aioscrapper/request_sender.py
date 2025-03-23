import asyncio
from typing import Callable, Awaitable, Any

from .types import QueryParams, Cookies, Headers, BasicAuth, Request, RequestParams, RequestQueue, PRPRequest


class RequestSender:
    def __init__(self, queue: RequestQueue) -> None:
        self._queue = queue

    async def __call__(
        self,
        url: str,
        method: str = "GET",
        callback: Callable[..., Awaitable] | None = None,
        cb_kwargs: dict[str, Any] | None = None,
        errback: Callable[..., Awaitable] | None = None,
        params: QueryParams | None = None,
        data: Any = None,
        json_data: Any = None,
        cookies: Cookies | None = None,
        headers: Headers | None = None,
        proxy: str | None = None,
        auth: BasicAuth | None = None,
        timeout: float | None = None,
        priority: int = 0,
        delay: float | None = None,
    ) -> None:
        await self._queue.put(
            PRPRequest(
                priority=priority,
                request=Request(
                    method=method,
                    url=url,
                    params=params,
                    data=data,
                    json_data=json_data,
                    cookies=cookies,
                    headers=headers,
                    auth=auth,
                    proxy=proxy,
                    timeout=timeout,
                ),
                request_params=RequestParams(
                    callback=callback,
                    cb_kwargs=cb_kwargs,
                    errback=errback,
                ),
            )
        )
        if delay:
            await asyncio.sleep(delay)
