class ClientException(Exception):
    pass


class HTTPException(ClientException):
    def __init__(self, status_code: int, message: str | None, url: str, method: str):
        self.status_code = status_code
        self.message = message
        self.url = url
        self.method = method

    def __str__(self):
        return f"{self.method} {self.url}: {self.status_code}: {self.message}"


class RequestException(ClientException):
    def __init__(self, inner_exc: Exception, url: str, method: str):
        self.inner_exc = inner_exc
        self.url = url
        self.method = method

    def __str__(self):
        return f"[{self.inner_exc.__class__.__name__}]: {self.method} {self.url}: {self.inner_exc}"
