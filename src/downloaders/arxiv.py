import asyncio
import logging
from typing import Optional

import aiohttp

from .base import BaseDownloader

logger = logging.getLogger(__name__)


class ArxivDownloader(BaseDownloader):
    """Downloader for arXiv papers"""

    ARXIV_PDF_URL = "https://arxiv.org/pdf/{paper_id}.pdf"
    ARXIV_REQUEST_DELAY = 3.0  # arXiv recommends 3 seconds between requests

    def __init__(
        self,
        user_agent: str = BaseDownloader.DEFAULT_USER_AGENT,
        request_delay: float = ARXIV_REQUEST_DELAY,
        max_retries: int = BaseDownloader.DEFAULT_MAX_RETRIES,
        timeout: int = BaseDownloader.DEFAULT_TIMEOUT,
        backoff_factor: int = BaseDownloader.DEFAULT_BACKOFF_FACTOR,
    ):
        """Initialize the arXiv downloader"""
        super().__init__(
            user_agent=user_agent,
            request_delay=request_delay,
            max_retries=max_retries,
            timeout=timeout,
            backoff_factor=backoff_factor,
        )
        logger.info(
            f"ArxivDownloader initialized with request delay of {request_delay}s"
        )

    def _get_download_url(self, paper_id: str) -> str:
        base_id = paper_id.split("v")[0] if "v" in paper_id else paper_id
        return self.ARXIV_PDF_URL.format(paper_id=base_id)

    async def download_paper(self, paper_id: str) -> Optional[bytes]:
        """Download paper PDF from arXiv"""
        url = self._get_download_url(paper_id)
        logger.info(f"Downloading paper {paper_id} from {url}")

        await self._rate_limiting()

        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    headers = {"User-Agent": self.user_agent}
                    async with session.get(
                        url, headers=headers, timeout=self.timeout
                    ) as response:
                        if response.status == 200:
                            content = await response.read()
                            logger.info(
                                f"Successfully downloaded paper {paper_id} ({len(content)} bytes)"
                            )
                            return content

                        if response.status == 429:  # Too many requests
                            retry_after = response.headers.get("Retry-After")
                            if retry_after and retry_after.isdigit():
                                wait_time = int(retry_after)
                            else:
                                wait_time = self.backoff_factor**attempt

                            logger.warning(
                                f"Rate limited (HTTP 429), waiting {wait_time}s before retry {attempt+1}/{self.max_retries}"
                            )
                            await asyncio.sleep(wait_time)
                            continue

                        logger.error(
                            f"HTTP Error {response.status} for URL: {url}. Response: {await response.text()[:200]}..."
                        )

                        if 500 <= response.status < 600:
                            wait_time = self.backoff_factor**attempt
                            logger.warning(f"Server error, retrying in {wait_time}s")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            return None

            except aiohttp.ClientError as e:
                wait_time = self.backoff_factor**attempt
                logger.warning(
                    f"Request failed (attempt {attempt+1}/{self.max_retries}): {str(e)}. "
                    f"Retrying in {wait_time}s"
                )
                await asyncio.sleep(wait_time)
            except asyncio.TimeoutError:
                wait_time = self.backoff_factor**attempt
                logger.warning(
                    f"Request timed out after {self.timeout}s (attempt {attempt+1}/{self.max_retries}). "
                    f"Retrying in {wait_time}s"
                )
                await asyncio.sleep(wait_time)
            except Exception as e:
                logger.error(f"Unexpected error during download: {str(e)}")
                return None

        logger.error(f"All {self.max_retries} retries failed for paper {paper_id}")
        return None
