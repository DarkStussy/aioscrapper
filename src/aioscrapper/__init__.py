__title__ = "aioscrapper"

__author__ = "darkstussy"

__copyright__ = f"Copyright (c) 2025 {__author__}"

from .request_sender import RequestSender
from .scrapper import AIOScrapper, BaseScrapper

__all__ = ["AIOScrapper", "BaseScrapper", "RequestSender"]
