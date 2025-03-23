import inspect
from typing import Callable, Awaitable, Any


def get_cb_kwargs(
    callback: Callable[..., Awaitable],
    srv_kwargs: dict[str, Any] | None,
    cb_kwargs: dict[str, Any] | None,
) -> dict[str, Any]:
    if cb_kwargs is None and srv_kwargs is None:
        return {}

    if cb_kwargs is None:
        cb_kwargs = {}
    if srv_kwargs is None:
        srv_kwargs = {}

    kwargs = cb_kwargs | srv_kwargs
    return {param: kwargs[param] for param in inspect.signature(callback).parameters.keys() if param in kwargs}
