"""Resolve the configured OpenAI-compatible API endpoint and credential."""

from __future__ import annotations

import os
import urllib.parse

DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"


def _normalize_api_base_url(url: str) -> str:
    value = (url or "").strip() or DEFAULT_OPENAI_BASE_URL
    parsed = urllib.parse.urlparse(
        value if "://" in value else f"https://{value}"
    )
    if not parsed.netloc:
        return DEFAULT_OPENAI_BASE_URL
    path = (parsed.path or "").rstrip("/")
    return urllib.parse.urlunparse(
        (parsed.scheme or "https", parsed.netloc, path, "", "", "")
    )


def custom_openai_base_url_configured() -> bool:
    """Return whether ``OPENAI_BASE_URL`` explicitly selects an endpoint."""
    return bool((os.getenv("OPENAI_BASE_URL") or "").strip())


def resolve_openai_base_url() -> str:
    """Return the normalized OpenAI-compatible base URL."""
    return _normalize_api_base_url(os.getenv("OPENAI_BASE_URL", ""))


def resolve_openai_api_key() -> str:
    """Return the sole credential used for model requests."""
    return (os.getenv("OPENAI_API_KEY") or "").strip()
