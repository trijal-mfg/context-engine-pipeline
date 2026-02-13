import httpx
import logging
import asyncio
from typing import AsyncGenerator, Dict, Any
from urllib.parse import urljoin

from config import (
    CONFLUENCE_URL,
    CONFLUENCE_USERNAME,
    CONFLUENCE_API_TOKEN,
    CONFLUENCE_CLIENT_RETRIES,
    CONFLUENCE_CLIENT_PAGE_LIMIT,
)

logger = logging.getLogger(__name__)


class ConfluenceClient:
    def __init__(self):
        base = CONFLUENCE_URL.rstrip("/")

        # Always keep domain only (no /wiki duplication issues)
        if base.endswith("/wiki"):
            self.domain = base[:-5]
        else:
            self.domain = base

        # Canonical API base for Confluence Cloud
        self.base_url = self.domain + "/wiki/rest/api/"

        self.auth = (CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN)
        self.timeout = httpx.Timeout(30.0, connect=60.0)
        self.limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)

    async def _make_request(
        self,
        client: httpx.AsyncClient,
        method: str,
        endpoint: str,
        params: Dict[str, Any] = None,
    ) -> Dict[str, Any]:

        if endpoint.startswith("http"):
            url = endpoint
        else:
            url = urljoin(self.base_url, endpoint)

        retries = CONFLUENCE_CLIENT_RETRIES

        for attempt in range(retries):
            try:
                response = await client.request(
                    method,
                    url,
                    params=params,
                    auth=self.auth,
                )

                if response.status_code == 429:
                    wait_time = int(response.headers.get("Retry-After", 5))
                    logger.warning(f"Rate limited. Waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                if e.response.status_code < 500 and e.response.status_code != 429:
                    logger.error(f"Client error {e.response.status_code} for {url}: {e}")
                    raise
                logger.warning(
                    f"Server error {e.response.status_code} "
                    f"(Attempt {attempt + 1}/{retries})"
                )
            except httpx.RequestError as e:
                logger.warning(
                    f"Request error (Attempt {attempt + 1}/{retries}): {e}"
                )

            await asyncio.sleep(2 ** attempt)

        raise Exception(f"Failed to fetch {url} after {retries} attempts.")

    def _normalize_next_link(self, next_link: str) -> str:
        """
        Atlassian Cloud sometimes returns:
        - /wiki/rest/api/...
        - /rest/api/...
        This ensures we always hit /wiki/rest/api/...
        """

        next_link = next_link.lstrip("/")

        # If link starts with rest/api, prepend wiki/
        if next_link.startswith("rest/"):
            next_link = "wiki/" + next_link

        return urljoin(self.domain + "/", next_link)

    async def get_updated_pages(
        self, since_date: str
    ) -> AsyncGenerator[Dict[str, Any], None]:

        cql = (
            f"type=page AND lastmodified > '{since_date}' "
            f"ORDER BY lastmodified"
        )

        limit = CONFLUENCE_CLIENT_PAGE_LIMIT
        next_url = None

        async with httpx.AsyncClient(
            timeout=self.timeout,
            limits=self.limits,
        ) as client:

            while True:
                if next_url:
                    data = await self._make_request(
                        client,
                        "GET",
                        next_url,
                        None,
                    )
                else:
                    data = await self._make_request(
                        client,
                        "GET",
                        "content/search",
                        {
                            "cql": cql,
                            "expand": "body.storage,version,ancestors,space",
                            "limit": limit,
                        },
                    )

                results = data.get("results", [])

                for page in results:
                    yield page

                next_link = data.get("_links", {}).get("next")

                if not next_link:
                    break

                next_url = self._normalize_next_link(next_link)
