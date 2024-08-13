import asyncio
import logging
import time
from typing import Callable, Any

from aiojobs import Scheduler

from .config import Config
from .scrapper import BaseScrapper
from .session import Session, SendRequest

logger = logging.getLogger(__name__)


class Executor:
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
        self._listen_queue_task: asyncio.Task = asyncio.create_task(self._session.listen_queue())
        self._scrappers: list[BaseScrapper] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.shutdown()

    async def shutdown(self, wait: bool = True):
        execution_timeout = self._config.execution.timeout
        if wait:
            while True:
                if execution_timeout is not None and time.time() - self._start_time > execution_timeout:
                    logger.log(
                        level=self._config.execution.log_level,
                        msg=f"execution timeout: {time.time() - self._start_time} > {execution_timeout}",
                    )
                    break

                if len(self._scheduler) == 0 and self._session.queue.qsize() == 0:
                    break

                await asyncio.sleep(0.1)

        try:
            await asyncio.wait_for(self._listen_queue_task, timeout=self._config.execution.shutdown_timeout)
        except asyncio.TimeoutError:
            pass
        finally:
            await self._scheduler.close()

        await self._session.close()
        for scrapper in self._scrappers:
            await scrapper.close()

    async def submit(self, scrapper: BaseScrapper) -> None:
        self._scrappers.append(scrapper)
        await scrapper.start(self._send_request)
