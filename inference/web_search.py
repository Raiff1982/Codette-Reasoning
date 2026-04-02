#!/usr/bin/env python3
"""Safe, citation-oriented web search utilities for Codette."""

from __future__ import annotations

import html
import logging
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser
from ipaddress import ip_address
from typing import List, Optional


logger = logging.getLogger(__name__)

USER_AGENT = "CodetteWebResearch/1.0 (+safe text retrieval)"
DEFAULT_TIMEOUT = 8
MAX_HTML_BYTES = 350_000
MAX_TEXT_CHARS = 2200
DUCKDUCKGO_HTML = "https://html.duckduckgo.com/html/"


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str = ""
    source: str = "duckduckgo"
    fetched_text: str = ""

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source,
            "fetched_text": self.fetched_text,
        }


class _SearchResultsParser(HTMLParser):
    """Extract result anchors from DuckDuckGo HTML results."""

    def __init__(self):
        super().__init__()
        self.results: List[SearchResult] = []
        self._capture_anchor = False
        self._current_href = ""
        self._current_text: List[str] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a":
            href = attrs.get("href", "")
            cls = attrs.get("class", "")
            if "result__a" in cls or "result-link" in cls:
                self._capture_anchor = True
                self._current_href = href
                self._current_text = []

    def handle_data(self, data):
        if self._capture_anchor:
            self._current_text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._capture_anchor:
            title = " ".join(part.strip() for part in self._current_text if part.strip()).strip()
            url = _normalize_result_url(self._current_href)
            if title and url:
                self.results.append(SearchResult(title=title, url=url))
            self._capture_anchor = False
            self._current_href = ""
            self._current_text = []


class _TextExtractor(HTMLParser):
    """Very small HTML to visible-text extractor."""

    def __init__(self):
        super().__init__()
        self.parts: List[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
        elif tag in {"p", "div", "section", "article", "main", "li", "h1", "h2", "h3", "h4", "br"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self._skip_depth > 0:
            self._skip_depth -= 1
        elif tag in {"p", "div", "section", "article", "main", "li", "h1", "h2", "h3", "h4"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if self._skip_depth:
            return
        text = data.strip()
        if text:
            self.parts.append(text + " ")

    def get_text(self) -> str:
        text = "".join(self.parts)
        text = html.unescape(text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        return text.strip()


def _normalize_result_url(url: str) -> str:
    if not url:
        return ""
    if url.startswith("//"):
        url = "https:" + url
    if url.startswith("/l/?uddg="):
        parsed = urllib.parse.urlparse(url)
        qs = urllib.parse.parse_qs(parsed.query)
        resolved = qs.get("uddg", [""])[0]
        return urllib.parse.unquote(resolved)
    return url


def _is_safe_url(url: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        if hostname in {"localhost", "127.0.0.1", "::1"}:
            return False

        try:
            ip = ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                return False
        except ValueError:
            pass

        try:
            infos = socket.getaddrinfo(hostname, None)
            for info in infos:
                addr = info[4][0]
                ip = ip_address(addr)
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                    return False
        except socket.gaierror:
            return False
        return True
    except Exception:
        return False


def _fetch_bytes(url: str, timeout: int = DEFAULT_TIMEOUT) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.8"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(MAX_HTML_BYTES)


def search_web(query: str, max_results: int = 3) -> List[SearchResult]:
    """Search the public web using a text-only endpoint and return safe results."""
    if not query.strip():
        return []
    payload = urllib.parse.urlencode({"q": query}).encode("utf-8")
    req = urllib.request.Request(
        DUCKDUCKGO_HTML,
        data=payload,
        headers={"User-Agent": USER_AGENT, "Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
            raw = resp.read(MAX_HTML_BYTES).decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError) as e:
        logger.warning("Web search failed: %s", e)
        return []

    parser = _SearchResultsParser()
    parser.feed(raw)
    safe_results = []
    for result in parser.results:
        if _is_safe_url(result.url):
            safe_results.append(result)
        if len(safe_results) >= max_results:
            break
    return safe_results


def fetch_url_text(url: str, max_chars: int = MAX_TEXT_CHARS) -> str:
    """Fetch a page and return visible text, capped and stripped."""
    if not _is_safe_url(url):
        return ""
    try:
        raw = _fetch_bytes(url).decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, ValueError):
        return ""

    extractor = _TextExtractor()
    extractor.feed(raw)
    text = extractor.get_text()
    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", 1)[0] + "..."
    return text


def research_query(query: str, max_results: int = 3) -> List[SearchResult]:
    """Search and fetch text for top safe results."""
    results = search_web(query, max_results=max_results)
    for result in results:
        result.fetched_text = fetch_url_text(result.url)
        if result.fetched_text and not result.snippet:
            result.snippet = result.fetched_text[:240].replace("\n", " ")
    return results
