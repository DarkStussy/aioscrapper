from logging import Logger
from typing import Generator

from .base import BasePipeline, BaseItem


class Pipeline:
    def __init__(self, logger: Logger, pipelines: dict[str, list[BasePipeline]] | None = None) -> None:
        self._logger = logger
        self._pipelines = pipelines or {}

    async def put_item(self, item: BaseItem) -> None:
        self._logger.debug(f"pipeline item received: {item}")
        try:
            pipelines = self._pipelines[item.pipeline_name]
        except KeyError:
            raise RuntimeError(f"Pipelines for item {item} not found")

        for pipeline in pipelines:
            await pipeline.put_item(item)

    def _get_pipelines(self) -> Generator[BasePipeline, None, None]:
        for pipelines in self._pipelines.values():
            for pipeline in pipelines:
                yield pipeline

    async def initialize(self) -> None:
        for pipeline in self._get_pipelines():
            await pipeline.initialize()

    async def close(self) -> None:
        for pipeline in self._get_pipelines():
            await pipeline.close()
