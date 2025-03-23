from httpx import AsyncClient, BasicAuth

from .base import BaseSession
from ..types import Request, Response


class HttpxSession(BaseSession):
    def __init__(self, timeout: float | None = None, ssl: bool | None = None):
        super().__init__(timeout, ssl)
        self._session = AsyncClient(timeout=timeout, verify=ssl if ssl is not None else True)

    async def make_request(self, request: Request) -> Response:
        try:
            response = await self._session.request(
                url=request.url,
                method=request.method,
                params=request.params,
                data=request.data,
                json=request.json_data,
                auth=(
                    BasicAuth(username=request.auth["username"], password=request.auth["password"])
                    if request.auth is not None
                    else None
                ),
                cookies=request.cookies,  # type: ignore
                headers=request.headers,
                timeout=request.timeout,
            )
            return Response(
                url=request.url,
                method=request.method,
                params=request.params,
                status=response.status_code,
                headers=response.headers,
                cookies={k: v for k, v in response.cookies.items()},
                content=response.content,
                content_type=response.headers.get("content-type"),
            )
        except Exception as exc:
            return Response(url=request.url, method=request.method, params=request.params, exception=exc)

    async def close(self) -> None:
        await self._session.aclose()
