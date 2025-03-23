from abc import abstractmethod
from typing import TypeVar, Generic, Protocol


class BaseItem(Protocol):
    @property
    def pipeline_name(self) -> str: ...


PipelineItem = TypeVar("PipelineItem", bound=BaseItem)


class BasePipeline(Generic[PipelineItem]):
    @abstractmethod
    async def put_item(self, item: PipelineItem) -> None: ...

    async def initialize(self) -> None: ...

    async def close(self) -> None: ...
