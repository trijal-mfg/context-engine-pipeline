
import httpx
import logging
import asyncio
from typing import AsyncGenerator, Dict, Any, List
from urllib.parse import urljoin

from config import CONFLUENCE_URL, CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN

logger = logging.getLogger(__name__)

class ConfluenceClient:
    def __init__(self):
        self.base_url = CONFLUENCE_URL.rstrip('/') + '/rest/api/'
        self.auth = (CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN)
        self.timeout = httpx.Timeout(30.0, connect=60.0)
        self.limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)

    async def _make_request(
        self, 
        client: httpx.AsyncClient, 
        method: str, 
        endpoint: str, 
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Make an HTTP request with retries and error handling.
        """
        url = urljoin(self.base_url, endpoint)
        retries = 3
        
        for attempt in range(retries):
            try:
                response = await client.request(method, url, params=params, auth=self.auth)
                
                if response.status_code == 429:
                    # Rate limited
                    wait_time = int(response.headers.get("Retry-After", 5))
                    logger.warning(f"Rate limited. Waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code < 500 and e.response.status_code != 429:
                    # Client error, do not retry
                    logger.error(f"Client error {e.response.status_code} for {url}: {e}")
                    raise
                logger.warning(f"Server error {e.response.status_code} (Attempt {attempt+1}/{retries})")
            except httpx.RequestError as e:
                logger.warning(f"Request error (Attempt {attempt+1}/{retries}): {e}")
            
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        raise Exception(f"Failed to fetch {url} after {retries} attempts.")

    async def get_updated_pages(self, since_date: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Yields pages updated since the given date.
        """
        cql = f"type=page AND lastModified > '{since_date}' ORDER BY lastModified"
        
        start = 0
        limit = 50
        
        async with httpx.AsyncClient(timeout=self.timeout, limits=self.limits) as client:
            while True:
                params = {
                    "cql": cql,
                    "expand": "body.storage,version,ancestors,space",
                    "start": start,
                    "limit": limit
                }
                
                try:
                    data = await self._make_request(client, "GET", "content/search", params)
                except Exception as e:
                    logger.error(f"Failed to fetch pages: {e}")
                    # In a real scenario we might want to bubble this up to abort the sync
                    raise

                results = data.get("results", [])
                if not results:
                    break
                
                for page in results:
                    yield page
                
                if len(results) < limit:
                    break
                    
                start += limit
