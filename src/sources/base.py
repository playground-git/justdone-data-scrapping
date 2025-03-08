import asyncio
import logging
import time
from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

from models.paper import PaperMetadata

logger = logging.getLogger(__name__)


class BaseSource(ABC):
    """Abstract base class for research paper sources"""

    DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    DEFAULT_REQUEST_DELAY = 1.0
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_TIMEOUT = 30
    DEFAULT_BACKOFF_FACTOR = 2

    def __init__(
        self,
        base_url: str,
        user_agent: str = DEFAULT_USER_AGENT,
        request_delay: float = DEFAULT_REQUEST_DELAY,
        max_retries: int = DEFAULT_MAX_RETRIES,
        timeout: int = DEFAULT_TIMEOUT,
        backoff_factor: int = DEFAULT_BACKOFF_FACTOR,
    ):
        """Initialize base source"""
        self.base_url = base_url
        self.user_agent = user_agent
        self.request_delay = request_delay
        self.max_retries = max_retries
        self.timeout = timeout
        self.backoff_factor = backoff_factor

        # Track last request time for rate limiting logic
        self.last_request_time = 0

        logger.info(
            f"Initialized source {self.__class__.__name__} with base URL: {base_url}, "
            f"request delay: {request_delay}s, max retries: {max_retries}"
        )

    async def _rate_limiting(self) -> None:
        """Rate limiting logic to prevent overloading API"""
        curr_time = time.time()
        elapsed = curr_time - self.last_request_time

        if elapsed < self.request_delay:
            delay = self.request_delay - elapsed
            logger.debug(f"Rate limiting: waiting {delay:.2f} seconds")
            await asyncio.sleep(delay)

        self.last_request_time = time.time()

    @abstractmethod
    async def fetch_papers(
        self,
        category: str,
        start_date: date,
        end_date: date,
        limit: Optional[int] = None,
    ) -> list[PaperMetadata]:
        """Fetch papers in a specific category within a date range"""
        pass
