import asyncio
import time
from logging import Logger, getLogger

from aiojobs import Scheduler

from ..config import Config
from ..middleware import RequestOuterMiddleware, RequestInnerMiddleware, ResponseMiddleware
from ..pipeline import Pipeline, BasePipeline
from ..request_sender import RequestSender
from ..request_worker import RequestWorker
from ..scrapper import BaseScrapper
from ..session import get_session_wrapper
from ..types import ShutdownStatus


class AIOScrapper:
    def __init__(
        self,
        scrappers: list[BaseScrapper],
        pipelines: dict[str, list[BasePipeline]] | None = None,
        request_outer_middlewares: list[RequestOuterMiddleware] | None = None,
        request_inner_middlewares: list[RequestInnerMiddleware] | None = None,
        response_middlewares: list[ResponseMiddleware] | None = None,
        config: Config | None = None,
        logger: Logger | None = None,
    ):
        self._scrappers = scrappers

        self._logger = logger or getLogger("aioscrapper")
        self._start_time = time.time()

        self._config = config or Config()

        self._scheduler = Scheduler(
            limit=self._config.scheduler.concurrent_requests,
            pending_limit=self._config.scheduler.pending_requests,
            close_timeout=self._config.scheduler.close_timeout,
        )

        if pipelines:
            self._logger.info(
                f"set pipelines: "
                + ", ".join(f"{k}: " + ", ".join(map(lambda p: p.__class__.__name__, v)) for k, v in pipelines.items())
            )
        self._pipeline = Pipeline(logger=self._logger.getChild("pipeline"), pipelines=pipelines)

        self._request_queue = asyncio.PriorityQueue()
        self._request_sender = RequestSender(self._request_queue)

        session = get_session_wrapper(self._config.session.lib)(
            timeout=self._config.session.request.timeout,
            ssl=self._config.session.request.ssl,
        )
        self._logger.info(f"set http session: {session.__class__.__name__}")
        self._request_worker = RequestWorker(
            logger=self._logger.getChild("request_worker"),
            session=session,
            schedule_request=self._scheduler.spawn,
            sender=self._request_sender,
            queue=self._request_queue,
            delay=self._config.session.request.delay,
            shutdown_timeout=self._config.execution.shutdown_timeout,
            srv_kwargs={"pipeline": self._pipeline},
            request_outer_middlewares=request_outer_middlewares,
            request_inner_middlewares=request_inner_middlewares,
            response_middlewares=response_middlewares,
        )

    @classmethod
    async def create(
        cls,
        scrappers: list[BaseScrapper],
        pipelines: dict[str, list[BasePipeline]] | None = None,
        request_outer_middlewares: list[RequestOuterMiddleware] | None = None,
        request_inner_middlewares: list[RequestInnerMiddleware] | None = None,
        response_middlewares: list[ResponseMiddleware] | None = None,
        config: Config | None = None,
        logger: Logger | None = None,
    ) -> "AIOScrapper":
        instance = cls(
            scrappers=scrappers,
            pipelines=pipelines,
            request_outer_middlewares=request_outer_middlewares,
            request_inner_middlewares=request_inner_middlewares,
            response_middlewares=response_middlewares,
            config=config,
            logger=logger,
        )
        await instance.initialize()
        return instance

    async def initialize(self) -> None:
        await self._pipeline.initialize()
        self._request_worker.listen_queue()

        for scrapper in self._scrappers:
            await scrapper.initialize()

    async def start(self) -> None:
        await asyncio.gather(*[scrapper.start(request_sender=self._request_sender) for scrapper in self._scrappers])

    async def _shutdown(self) -> ShutdownStatus:
        status = ShutdownStatus.OK
        execution_timeout = (
            max(self._config.execution.timeout - (time.time() - self._start_time), 0.1)
            if self._config.execution.timeout
            else None
        )
        while True:
            if execution_timeout is not None and time.time() - self._start_time > execution_timeout:
                self._logger.log(
                    level=self._config.execution.log_level,
                    msg=f"execution timeout: {self._config.execution.timeout}!",
                )
                status = ShutdownStatus.TIMEOUT
                break
            if len(self._scheduler) == 0 and self._request_queue.qsize() == 0:
                break

            await asyncio.sleep(self._config.execution.shutdown_check_interval)

        return status

    async def shutdown(self) -> None:
        status = await self._shutdown()
        await self._request_worker.shutdown(status == ShutdownStatus.TIMEOUT)

    async def close(self, shutdown: bool = True) -> None:
        if shutdown:
            await self.shutdown()

        for scrapper in self._scrappers:
            await scrapper.close()

        await self._scheduler.close()
        await self._request_worker.close()
        await self._pipeline.close()
