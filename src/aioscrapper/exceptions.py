from aiohttp import RequestInfo
from aiohttp.typedefs import StrOrURL


class ClientException(Exception):
    pass


class HTTPException(ClientException):
    def __init__(self, status_code: int, message: str, request_info: RequestInfo):
        self.status_code = status_code
        self.message = message
        self.request_info = request_info

    def __str__(self):
        return f"{self.request_info.url}: {self.status_code}: {self.message}"


class RequestException(ClientException):
    def __init__(self, inner_exc: Exception, url: StrOrURL, method: str):
        self.inner_exc = inner_exc
        self.url = url
        self.method = method

    def __str__(self):
        return f"[{self.inner_exc.__class__.__name__}]: {self.method} {self.url}: {self.inner_exc}"
