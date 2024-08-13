from dataclasses import dataclass, field
from typing import Any, Mapping, Awaitable, Callable, Literal

from aiohttp import BasicAuth, ClientTimeout
from aiohttp.typedefs import LooseCookies, LooseHeaders, StrOrURL

HttpMethod = Literal["GET", "HEAD", "POST", "PUT", "DELETE", "CONNECT", "OPTIONS", "TRACE", "PATCH"]


@dataclass(kw_only=True)
class Request:
    url: StrOrURL
    method: HttpMethod
    callback: Callable[..., Awaitable] | None
    cb_kwargs: Mapping[str, Any] | None
    errback: Callable[..., Awaitable] | None
    params: Mapping[str, str | int] | str | None
    data: Any
    json: Any
    cookies: LooseCookies | None
    headers: LooseHeaders | None
    proxy: StrOrURL | None
    proxy_auth: BasicAuth | None
    timeout: ClientTimeout | None
    proxy_headers: LooseHeaders | None


@dataclass(order=True)
class PrioritizedRequest:
    priority: int
    request: Request = field(compare=False)
