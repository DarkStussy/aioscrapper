from aiohttp import ClientSession, ClientTimeout, TCPConnector
from aiohttp.helpers import BasicAuth as AiohttpBasicAuth

from .base import BaseSession
from ..types import Response, Request


class AiohttpSession(BaseSession):
    def __init__(self, timeout: float | None = None, ssl: bool | None = None):
        super().__init__(timeout, ssl)
        self._session = ClientSession(
            timeout=ClientTimeout(total=timeout),
            connector=TCPConnector(ssl=ssl) if ssl is not None else None,
        )

    async def make_request(self, request: Request) -> Response:
        try:
            async with self._session.request(
                url=request.url,
                method=request.method,
                params=request.params,
                data=request.data,
                json=request.json_data,
                cookies=request.cookies,
                headers=request.headers,
                proxy=request.proxy,
                auth=(
                    AiohttpBasicAuth(login=request.auth["username"], password=request.auth["password"])
                    if request.auth is not None
                    else None
                ),
                timeout=ClientTimeout(total=request.timeout) if request.timeout is not None else None,
            ) as response:
                return Response(
                    url=request.url,
                    method=request.method,
                    params=request.params,
                    status=response.status,
                    headers=response.headers,
                    cookies={k: f"{v.key}={v.value}" for k, v in response.cookies.items()},
                    content=await response.read(),
                    content_type=response.headers.get("Content-Type"),
                )
        except Exception as exc:
            return Response(url=request.url, method=request.method, params=request.params, exception=exc)

    async def close(self) -> None:
        await self._session.close()
