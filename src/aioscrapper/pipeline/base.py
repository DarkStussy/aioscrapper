from abc import abstractmethod
from typing import TypeVar, Generic, Protocol


class BaseItem(Protocol):
    @property
    def pipeline(self) -> str: ...


Item = TypeVar("Item", bound=BaseItem)


class BasePipeline(Generic[Item]):
    @abstractmethod
    async def put_item(self, item: Item) -> None: ...

    async def initialize(self) -> None: ...

    async def close(self) -> None: ...
