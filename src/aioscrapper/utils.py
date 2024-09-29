import inspect
from typing import Callable, Awaitable, Mapping, Any


def get_cb_kwargs(callback: Callable[..., Awaitable], cb_kwargs: Mapping[str, Any] | None) -> dict[str, Any]:
    if cb_kwargs is None:
        return {}

    return {param: cb_kwargs[param] for param in inspect.signature(callback).parameters.keys() if param in cb_kwargs}
