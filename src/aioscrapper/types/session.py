import asyncio
import json
from dataclasses import field, dataclass
from typing import Union, Mapping, Any, Callable, Awaitable, TypedDict


QueryParams = Mapping[str, Union[str, int, float]]

Cookies = Mapping[str, str]
Headers = Mapping[str, str]


class BasicAuth(TypedDict):
    username: str
    password: str


@dataclass(slots=True)
class Request:
    url: str
    method: str
    params: QueryParams | None = None
    data: Any = None
    json_data: Any = None
    cookies: Cookies | None = None
    headers: Headers | None = None
    auth: BasicAuth | None = None
    proxy: str | None = None
    timeout: float | None = None


@dataclass(slots=True)
class RequestParams:
    callback: Callable[..., Awaitable] | None = None
    cb_kwargs: dict[str, Any] | None = None
    errback: Callable[..., Awaitable] | None = None


@dataclass(slots=True, order=True)
class PRPRequest:
    priority: int
    request: Request = field(compare=False)
    request_params: RequestParams = field(compare=False)


RequestQueue = asyncio.PriorityQueue[PRPRequest | None]


class Response:
    def __init__(
        self,
        url: str,
        method: str,
        params: QueryParams | None = None,
        status: int | None = None,
        headers: Headers | None = None,
        cookies: Cookies | None = None,
        content: bytes | None = None,
        content_type: str | None = None,
        exception: Exception | None = None,
    ) -> None:
        self._url = url
        self._method = method
        self._params = params
        self._status = status
        self._headers = headers
        self._cookies = cookies
        self._content = content
        self._content_type = content_type
        self._exception = exception

    @property
    def url(self) -> str:
        return self._url

    @property
    def method(self) -> str:
        return self._method

    @property
    def params(self) -> QueryParams | None:
        return self._params

    @property
    def status(self) -> int | None:
        return self._status

    @property
    def headers(self) -> Headers | None:
        return self._headers

    @property
    def cookies(self) -> Cookies | None:
        return self._cookies

    @property
    def content_type(self) -> str | None:
        return self._content_type

    @property
    def exception(self) -> Exception | None:
        return self._exception

    def bytes(self) -> bytes | None:
        return self._content

    def json(self) -> Any:
        return json.loads(self._content) if self._content is not None else None

    def text(self, encoding: str = "utf-8") -> str | None:
        return self._content.decode(encoding) if self._content is not None else None
