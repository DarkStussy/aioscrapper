from aiohttp import RequestInfo

from .models import Request


class ClientException(Exception):
    pass


class HTTPException(ClientException):
    def __init__(self, status_code: int, message: str | dict, request: Request, request_info: RequestInfo):
        self.status_code = status_code
        self.message = message
        self.request = request
        self.request_info = request_info

    def __str__(self):
        return f"{self.request_info.url}: {self.status_code}: {self.message}"


class RequestException(ClientException):
    def __init__(self, inner_exception: Exception, request: Request):
        self.inner_exception = inner_exception
        self.request = request

    def __str__(self):
        return (
            f"[{self.inner_exception.__class__.__name__}] {self.request.method}: {self.request.url}: "
            f"{self.inner_exception}"
        )
