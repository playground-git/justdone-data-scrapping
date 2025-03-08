import asyncio
import logging
import xml.etree.ElementTree as ET
from datetime import date, datetime
from typing import Optional

import aiohttp

from models.paper import PaperMetadata

from .base import BaseSource

logger = logging.getLogger(__name__)

# XML namespaces used in arXiv API responses
NAMESPACES = {
    "atom": "http://www.w3.org/2005/Atom",
    "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
    "arxiv": "http://arxiv.org/schemas/atom",
}


class ArxivSource(BaseSource):
    """Source for fetching papers from arXiv.org"""

    # ArXiv specific constants
    ARXIV_API_URL = "http://export.arxiv.org/api/query"
    ARXIV_REQUEST_DELAY = (
        3.0  # arXiv recommends 3 seconds between requests (arXiv API User's Manual)
    )
    ARXIV_MAX_RESULTS_PER_REQUEST = 100

    def __init__(
        self,
        base_url: str = ARXIV_API_URL,
        user_agent: str = BaseSource.DEFAULT_USER_AGENT,
        request_delay: float = ARXIV_REQUEST_DELAY,
        max_retries: int = BaseSource.DEFAULT_MAX_RETRIES,
        timeout: int = BaseSource.DEFAULT_TIMEOUT,
        backoff_factor: int = BaseSource.DEFAULT_BACKOFF_FACTOR,
    ):
        """Initialize the arXiv source"""
        super().__init__(
            base_url=base_url,
            user_agent=user_agent,
            request_delay=request_delay,
            max_retries=max_retries,
            timeout=timeout,
            backoff_factor=backoff_factor,
        )
        logger.info(f"ArxivSource initialized with request delay of {request_delay}s")

    def _build_url(
        self,
        category: str,
        start_date: date,
        end_date: date,
        start: int = 0,
        max_results: int = ARXIV_MAX_RESULTS_PER_REQUEST,
    ) -> str:
        """Build URL for arXiv API request"""
        start_str = start_date.strftime("%Y%m%d0000")
        end_str = end_date.strftime("%Y%m%d2359")

        url = (
            f"{self.base_url}?search_query=cat:{category}+AND+submittedDate:[{start_str}+TO+{end_str}]"
            f"&start={start}&max_results={max_results}&sortBy=submittedDate&sortOrder=ascending"
        )

        return url

    async def _fetch_page(
        self,
        category: str,
        start_date: date,
        end_date: date,
        start: int,
        max_results: int,
    ) -> Optional[str]:
        """Fetch single page of results from arXiv API"""

        # NOTE: constructing params doesn't work (idk why) so I construct URL with the search parameters manually
        url = self._build_url(category, start_date, end_date, start, max_results)
        logger.debug(f"Fetching URL: {url}")

        # Apply rate limiting
        await self._rate_limiting()

        # Retry logic with exponential backoff
        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    headers = {"User-Agent": self.user_agent}
                    async with session.get(
                        url, headers=headers, timeout=self.timeout
                    ) as response:
                        if response.status == 200:
                            return await response.text()

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
                logger.error(f"Unexpected error during request: {str(e)}")
                return None

        logger.error(f"All {self.max_retries} retries failed for URL: {url}")
        return None

    def _parse_xml_response(self, xml_content: str) -> tuple[list[PaperMetadata], int]:
        """Parse XML response from arXiv API and extract paper metadata"""
        try:
            root = ET.fromstring(xml_content)

            total_results_elem = root.find("opensearch:totalResults", NAMESPACES)
            total_results = (
                int(total_results_elem.text) if total_results_elem is not None else 0
            )

            papers = []

            # Process each paper in the feed
            for entry in root.findall("atom:entry", NAMESPACES):
                try:
                    # Skip first entry if it's feed information
                    id_elem = entry.find("atom:id", NAMESPACES)
                    if id_elem is None or "http://arxiv.org/api" in id_elem.text:
                        continue

                    full_id = id_elem.text.split("/")[-1]

                    # Remove version number
                    paper_id = full_id.split("v")[0] if "v" in full_id else full_id

                    title_elem = entry.find("atom:title", NAMESPACES)
                    title = (
                        " ".join(title_elem.text.split())
                        if title_elem is not None
                        else ""
                    )

                    summary_elem = entry.find("atom:summary", NAMESPACES)
                    abstract = (
                        " ".join(summary_elem.text.split())
                        if summary_elem is not None
                        else ""
                    )

                    authors = []
                    for author_elem in entry.findall("atom:author", NAMESPACES):
                        name_elem = author_elem.find("atom:name", NAMESPACES)
                        if name_elem is not None and name_elem.text:
                            authors.append(name_elem.text)

                    categories = []
                    for category_elem in entry.findall("atom:category", NAMESPACES):
                        term = category_elem.get("term")
                        if term:
                            categories.append(term)

                    published_elem = entry.find("atom:published", NAMESPACES)
                    updated_elem = entry.find("atom:updated", NAMESPACES)

                    submission_date = None
                    update_date = None

                    if published_elem is not None and published_elem.text:
                        dt = datetime.fromisoformat(published_elem.text)
                        submission_date = dt.date()

                    if updated_elem is not None and updated_elem.text:
                        dt = datetime.fromisoformat(updated_elem.text)
                        update_date = dt.date()

                    if not submission_date or not update_date:
                        logger.warning(
                            f"Skipping paper {paper_id} due to missing dates"
                        )
                        continue

                    paper = PaperMetadata(
                        id=paper_id,
                        authors=authors,
                        title=title,
                        abstract=abstract,
                        categories=categories,
                        submission_date=submission_date,
                        update_date=update_date,
                    )

                    papers.append(paper)

                except Exception as e:
                    logger.warning(f"Error parsing paper entry: {str(e)}")
                    continue

            return papers, total_results

        except ET.ParseError as e:
            logger.error(f"XML parsing error: {str(e)}")
            return [], 0
        except Exception as e:
            logger.error(f"Unexpected error parsing XML: {str(e)}")
            return [], 0

    async def fetch_papers(
        self,
        category: str,
        start_date: date,
        end_date: date,
        limit: Optional[int] = None,
    ) -> list[PaperMetadata]:
        """Fetch papers in a specific category within a date range"""
        logger.info(
            f"Fetching papers in category '{category}' from {start_date} to {end_date}, "
            f"limit: {'unlimited' if limit is None else limit}"
        )

        all_papers = []
        start = 0
        batch_size = self.ARXIV_MAX_RESULTS_PER_REQUEST
        total_results = None

        while True:
            xml_content = await self._fetch_page(
                category=category,
                start_date=start_date,
                end_date=end_date,
                start=start,
                max_results=batch_size,
            )

            if not xml_content:
                logger.warning(f"Failed to fetch papers at offset {start}")
                break

            papers, total_count = self._parse_xml_response(xml_content)

            if total_results is None:
                total_results = total_count
                logger.info(f"Found {total_results} total papers matching the criteria")

            if not papers:
                logger.info("No papers found in this batch")
                if start == 0:
                    break
                else:
                    logger.info("Reached end of results")
                    break

            all_papers.extend(papers)
            logger.info(
                f"Fetched {len(papers)} papers, total so far: {len(all_papers)}/{total_results}"
            )

            if (
                len(papers) < batch_size
                or (limit is not None and len(all_papers) >= limit)
                or len(all_papers) >= total_results
            ):
                logger.info(
                    f"Reached end of available papers or limit: {len(all_papers)}/{total_results}"
                )
                break

            start += len(papers)

            # Adjust batch size for the last request if needed
            if limit is not None:
                remaining = limit - len(all_papers)
                if remaining < batch_size:
                    batch_size = remaining

            await asyncio.sleep(self.request_delay)

        if limit is not None and len(all_papers) > limit:
            all_papers = all_papers[:limit]

        logger.info(f"Successfully fetched {len(all_papers)} papers from arXiv")
        return all_papers
