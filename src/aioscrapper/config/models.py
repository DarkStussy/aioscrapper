import logging
from dataclasses import dataclass


@dataclass(frozen=True)
class SessionConfig:
    concurrent_requests: int = 64
    pending_requests: int = 1
    timeout: int = 60
    request_delay: float = 0.0
    ssl: bool = True


@dataclass(frozen=True)
class ExecutionConfig:
    timeout: float | None = None
    wait_timeout: float | None = None
    shutdown_timeout: float = 0.1
    log_level: int | str = logging.ERROR


@dataclass(frozen=True)
class Config:
    session: SessionConfig = SessionConfig()
    execution: ExecutionConfig = ExecutionConfig()
