from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from .tiktok_api import TikTokAPI
from .token_store import TokenStore


def _parse_iso_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _load_env_tokens() -> dict[str, Any]:
    tokens: dict[str, Any] = {}

    raw_json = os.getenv("TIKTOK_TOKEN_JSON", "").strip()
    if raw_json:
        parsed = json.loads(raw_json)
        if not isinstance(parsed, dict):
            raise RuntimeError("TIKTOK_TOKEN_JSON must contain a JSON object.")
        tokens.update(parsed)

    field_map = {
        "TIKTOK_ACCESS_TOKEN": "access_token",
        "TIKTOK_REFRESH_TOKEN": "refresh_token",
        "TIKTOK_ACCESS_TOKEN_EXPIRES_AT": "access_token_expires_at",
        "TIKTOK_REFRESH_TOKEN_EXPIRES_AT": "refresh_token_expires_at",
    }
    for env_name, field_name in field_map.items():
        value = os.getenv(env_name, "").strip()
        if value:
            tokens[field_name] = value
    return tokens


def load_runtime_tokens(token_store: TokenStore) -> dict[str, Any]:
    data = token_store.load()
    data.update(_load_env_tokens())
    return data


def access_token_is_fresh(tokens: dict[str, Any], skew_seconds: int = 120) -> bool:
    access_token = (tokens.get("access_token") or "").strip()
    if not access_token:
        return False

    expires_at = _parse_iso_timestamp(str(tokens.get("access_token_expires_at", "")).strip())
    if expires_at is None:
        return True
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at > datetime.now(timezone.utc) + timedelta(seconds=skew_seconds)


def ensure_access_token(api: TikTokAPI, token_store: TokenStore) -> tuple[str, dict[str, Any]]:
    tokens = load_runtime_tokens(token_store)
    if access_token_is_fresh(tokens):
        return str(tokens["access_token"]).strip(), tokens

    refresh_token = str(tokens.get("refresh_token", "")).strip()
    if not refresh_token:
        raise RuntimeError("Missing TikTok refresh token. Complete OAuth once and store the refresh token in secrets.")

    refreshed = api.refresh_access_token(refresh_token)
    merged = dict(tokens)
    merged.update(refreshed)
    merged = token_store.with_expirations(merged)
    token_store.save(merged)
    return str(merged["access_token"]).strip(), merged
