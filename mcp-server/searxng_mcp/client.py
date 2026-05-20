"""HTTP client for SearXNG search, fetch, and crawl operations."""

import json
import os
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup
from urllib.parse import urljoin

from searxng_mcp.config import (
    DEFAULT_SUBPAGE_LIMIT,
    DEFAULT_TIMEOUT,
    DEFAULT_USER_AGENT,
    LINKS_SECTION_MARKER,
)
from searxng_mcp.content_utils import truncate_content_with_links
from searxng_mcp.http_body import decode_http_response_body


class SearXNGClient:
    def __init__(self, base_url: str = None, timeout: int = DEFAULT_TIMEOUT):
        if base_url is None:
            protocol = os.environ.get("SEARXNG_PROTOCOL", "http")
            host = os.environ.get("SEARXNG_HOST", "searxng")
            port = os.environ.get("SEARXNG_PORT", "7777")
            base_url = f"{protocol}://{host}:{port}"

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.search_url = f"{self.base_url}/search"

    def search(
        self,
        query: str,
        categories: Optional[List[str]] = None,
        engines: Optional[List[str]] = None,
        language: str = "en",
        time_range: Optional[str] = None,
        pageno: int = 1,
    ) -> Dict[str, Any]:
        params = {
            "q": query,
            "format": "json",
            "language": language,
            "safesearch": 0,
            "pageno": pageno,
        }

        if categories:
            params["categories"] = ",".join(categories)
        if engines:
            params["engines"] = ",".join(engines)
        if time_range:
            params["time_range"] = time_range

        url = f"{self.search_url}?{urllib.parse.urlencode(params)}"

        try:
            request = urllib.request.Request(url)
            request.add_header("User-Agent", DEFAULT_USER_AGENT)

            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                content = decode_http_response_body(response.read(), response.headers)
                return json.loads(content)
        except Exception as e:
            return {"error": str(e)}

    def fetch(self, url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Fetch content from a URL and return clean text (HTML stripped)."""
        try:
            request = urllib.request.Request(url)
            request.add_header("User-Agent", DEFAULT_USER_AGENT)

            if headers:
                for key, value in headers.items():
                    request.add_header(key, value)

            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw_content = decode_http_response_body(response.read(), response.headers)

                soup = BeautifulSoup(raw_content, "html.parser")

                for script in soup(["script", "style"]):
                    script.decompose()

                clean_text = soup.get_text()

                lines = (line.strip() for line in clean_text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                clean_text = "\n".join(chunk for chunk in chunks if chunk)

                links = []
                seen_urls = set()
                for link in soup.find_all("a", href=True):
                    href = link.get("href")
                    anchor_text = link.get_text(strip=True)
                    if href and anchor_text:
                        absolute_url = urljoin(url, href)
                        if absolute_url not in seen_urls:
                            seen_urls.add(absolute_url)
                            links.append(f"{anchor_text}: {absolute_url}")

                if links:
                    clean_text += LINKS_SECTION_MARKER + "\n" + "\n".join(links)

                return {
                    "url": url,
                    "status_code": response.status,
                    "headers": dict(response.headers),
                    "content": clean_text,
                    "content_length": len(clean_text),
                    "original_content_length": len(raw_content),
                }
        except Exception as e:
            return {"error": str(e), "url": url}

    def crawl(
        self,
        url: str,
        filters: Optional[List[str]] = None,
        headers: Optional[Dict[str, str]] = None,
        subpage_limit: int = DEFAULT_SUBPAGE_LIMIT,
        max_content_length: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Crawl a page and return its content plus up to subpage_limit subpages."""
        try:
            main_result = self.fetch(url, headers)
            if "error" in main_result:
                return main_result

            request = urllib.request.Request(url)
            request.add_header("User-Agent", DEFAULT_USER_AGENT)

            if headers:
                for key, value in headers.items():
                    request.add_header(key, value)

            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw_content = decode_http_response_body(response.read(), response.headers)
                soup = BeautifulSoup(raw_content, "html.parser")

            links = []
            seen_urls = set()
            for link in soup.find_all("a", href=True):
                href = link.get("href")
                anchor_text = link.get_text(strip=True)

                if href and anchor_text:
                    absolute_url = urljoin(url, href)

                    if absolute_url in seen_urls:
                        continue
                    seen_urls.add(absolute_url)

                    if filters:
                        if not any(
                            filter_str.lower() in anchor_text.lower()
                            for filter_str in filters
                        ):
                            continue

                    links.append({"url": absolute_url, "anchor_text": anchor_text})

            selected_links = links[:subpage_limit]

            subpages = []
            for link_info in selected_links:
                subpage_result = self.fetch(link_info["url"], headers)
                if "error" not in subpage_result:
                    content = subpage_result["content"]
                    content_length = subpage_result["content_length"]

                    if max_content_length is not None and len(content) > max_content_length:
                        content = truncate_content_with_links(content, max_content_length)
                        content_length = len(content)

                    subpages.append(
                        {
                            "url": link_info["url"],
                            "anchor_text": link_info["anchor_text"],
                            "content": content,
                            "content_length": content_length,
                        }
                    )

            return {
                "main_page": {
                    "url": url,
                    "content": main_result["content"],
                    "content_length": main_result["content_length"],
                },
                "subpages": subpages,
                "total_subpages_found": len(links),
                "subpages_returned": len(subpages),
                "filters_applied": filters,
            }

        except Exception as e:
            return {"error": str(e), "url": url}


client = SearXNGClient()
