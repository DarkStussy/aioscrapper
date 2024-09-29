import asyncio
import logging
import time
from types import TracebackType
from typing import Callable, Any, Self, Type

from aiojobs import Scheduler

from .config import Config
from .scrapper import BaseScrapper
from .session import Session, SendRequest

logger = logging.getLogger(__name__)


class ScrapperExecutor:
    def __init__(
        self,
        config: Config = Config(),
        exception_handler: Callable[[Scheduler, dict[str, Any]], None] | None = None,
    ):
        self._start_time = time.time()
        self._config = config
        self._scheduler = Scheduler(
            wait_timeout=self._config.execution.wait_timeout,
            limit=self._config.session.concurrent_requests,
            pending_limit=self._config.session.pending_requests,
            exception_handler=exception_handler,
        )
        self._session = Session(self._config.session, self._scheduler)
        self._send_request = SendRequest(self._session.queue)
        self._receive_requests_task: asyncio.Task = asyncio.create_task(self._session.start())
        self._scrappers: list[BaseScrapper] = []

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

    async def submit(self, scrapper: BaseScrapper) -> None:
        self._scrappers.append(scrapper)
        await scrapper.start(self._send_request)

    async def _shutdown(self):
        execution_timeout = (
            min(self._config.execution.timeout - (time.time() - self._start_time), 0.1)
            if self._config.execution.timeout
            else None
        )
        while True:
            if execution_timeout is not None and (execution_time := time.time() - self._start_time) > execution_timeout:
                logger.log(
                    level=self._config.execution.log_level,
                    msg=f"execution timeout: {execution_time:.2f} > {execution_timeout}",
                )
                break
            if len(self._scheduler) == 0 and self._session.queue.qsize() == 0:
                break

            await asyncio.sleep(0.1)

    async def shutdown(self) -> None:
        await self._shutdown()
        await self._session.shutdown()
        await self._receive_requests_task

    async def close(self, shutdown: bool = True):
        if shutdown:
            await self.shutdown()

        for scrapper in self._scrappers:
            await scrapper.close()

        await self._scheduler.close()
        await self._session.close()
