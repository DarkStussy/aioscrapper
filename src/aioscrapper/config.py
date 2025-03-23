import logging
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RequestConfig:
    timeout: int = 60
    delay: float = 0.0
    ssl: bool = True


@dataclass(slots=True, frozen=True)
class SessionConfig:
    lib: str | None = None
    request: RequestConfig = RequestConfig()


@dataclass(slots=True, frozen=True)
class SchedulerConfig:
    concurrent_requests: int = 64
    pending_requests: int = 1
    close_timeout: float | None = 0.1


@dataclass(slots=True, frozen=True)
class ExecutionConfig:
    timeout: float | None = None
    shutdown_timeout: float = 0.1
    shutdown_check_interval: float = 0.1
    log_level: int = logging.ERROR


@dataclass(slots=True, frozen=True)
class Config:
    session: SessionConfig = SessionConfig()
    scheduler: SchedulerConfig = SchedulerConfig()
    execution: ExecutionConfig = ExecutionConfig()
