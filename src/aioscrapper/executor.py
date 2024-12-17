import asyncio
import time
from logging import Logger, getLogger
from types import TracebackType
from typing import Callable, Any, Self, Type

from aiojobs import Scheduler

from .config import Config
from .pipeline import Pipeline
from .scrapper import BaseScrapper
from .session import Session


class ScrapperExecutor:
    def __init__(
        self,
        config: Config = Config(),
        logger: Logger | None = None,
        exception_handler: Callable[[Scheduler, dict[str, Any]], None] | None = None,
    ):
        self._logger = logger or getLogger("aioscrapper")
        self._start_time = time.time()
        self._config = config
        self._scheduler = Scheduler(
            wait_timeout=self._config.execution.wait_timeout,
            limit=self._config.session.concurrent_requests,
            pending_limit=self._config.session.pending_requests,
            exception_handler=exception_handler,
        )
        self._pipeline = Pipeline(logger=self._logger.getChild("pipeline"), pipelines=self._config.pipelines)
        self._session = Session(
            logger=self._logger.getChild("session"),
            config=self._config.session,
            scheduler=self._scheduler,
            srv_kwargs={"pipeline": self._pipeline},
        )
        self._receive_requests_task: asyncio.Task | None = None
        self._scrappers: list[BaseScrapper] = []

    async def start(self) -> None:
        self._receive_requests_task = asyncio.create_task(self._session.start())
        await asyncio.gather(*[scrapper.start(self._session.send_request) for scrapper in self._scrappers])

    async def __aenter__(self) -> Self:
        await self._pipeline.initialize()
        return self

    async def __aexit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            return await self.close()

        try:
            await self.start()
        finally:
            await self.close()

    async def add(self, scrapper: BaseScrapper) -> None:
        self._scrappers.append(scrapper)
        await scrapper.initialize()

    async def _shutdown(self) -> None:
        execution_timeout = (
            max(self._config.execution.timeout - (time.time() - self._start_time), 0.1)
            if self._config.execution.timeout
            else None
        )
        while True:
            if execution_timeout is not None and (execution_time := time.time() - self._start_time) > execution_timeout:
                self._logger.log(
                    level=self._config.execution.log_level,
                    msg=f"execution timeout: {execution_time:.2f} > {execution_timeout}",
                )
                break
            if len(self._scheduler) == 0 and self._session.queue.qsize() == 0:
                break

            await asyncio.sleep(self._config.execution.shutdown_check_interval)

    async def shutdown(self) -> None:
        await self._shutdown()
        await self._session.shutdown()
        if self._receive_requests_task is not None:
            await self._receive_requests_task

    async def close(self, shutdown: bool = True) -> None:
        if shutdown:
            await self.shutdown()

        for scrapper in self._scrappers:
            await scrapper.close()

        await self._scheduler.close()
        await self._session.close()
        await self._pipeline.close()
