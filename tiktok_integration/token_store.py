from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


class TokenStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def clear(self) -> None:
        if self.path.exists():
            self.path.unlink()

    @staticmethod
    def with_expirations(token_data: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        enriched = dict(token_data)
        expires_in = int(token_data.get("expires_in", 0) or 0)
        refresh_expires_in = int(token_data.get("refresh_expires_in", 0) or 0)
        if expires_in:
            enriched["access_token_expires_at"] = (now + timedelta(seconds=expires_in)).isoformat()
        if refresh_expires_in:
            enriched["refresh_token_expires_at"] = (now + timedelta(seconds=refresh_expires_in)).isoformat()
        enriched["saved_at"] = now.isoformat()
        return enriched
