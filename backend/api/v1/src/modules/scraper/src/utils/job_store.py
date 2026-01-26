"""Redis-backed storage for temporary scraping job state."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from src.core.redis_client import get_redis_client


def _deep_merge_dicts(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    for key, value in (patch or {}).items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key] = _deep_merge_dicts(base[key], value)
        else:
            base[key] = value
    return base


@dataclass(frozen=True)
class ScrapingJobStore:
    """Stores scraping job state in Redis with a TTL.

    Keys are deterministic by email (normalized upstream).
    """

    key_prefix: str = "scraper:job:"
    ttl_seconds: int = int(os.getenv("SCRAPER_JOB_TTL_SECONDS", "86400"))

    def _key(self, email_key: str) -> str:
        return f"{self.key_prefix}{email_key}"

    def get(self, email_key: str) -> Optional[Dict[str, Any]]:
        r = get_redis_client()
        raw = r.get(self._key(email_key))
        if not raw:
            return None
        return json.loads(raw)

    def set(self, email_key: str, state: Dict[str, Any]) -> None:
        r = get_redis_client()
        r.set(self._key(email_key), json.dumps(state, ensure_ascii=False), ex=self.ttl_seconds)

    def patch(self, email_key: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        current = self.get(email_key) or {}
        updated = _deep_merge_dicts(current, patch or {})
        self.set(email_key, updated)
        return updated

    def delete(self, email_key: str) -> None:
        r = get_redis_client()
        r.delete(self._key(email_key))
