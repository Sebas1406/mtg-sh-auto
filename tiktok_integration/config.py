from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    client_key: str
    client_secret: str
    redirect_uri: str
    local_callback_url: str
    scopes: str
    verify_prefix: str
    media_base_url: str
    flask_host: str
    flask_port: int
    token_store_path: Path
    netlify_auth_token: str
    netlify_site_id: str
    netlify_deploy_poll_seconds: int


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def load_settings() -> Settings:
    token_store_raw = os.getenv("TOKEN_STORE_PATH", ".secrets/tiktok_tokens.json").strip()
    return Settings(
        client_key=_required("TIKTOK_CLIENT_KEY"),
        client_secret=_required("TIKTOK_CLIENT_SECRET"),
        redirect_uri=_required("TIKTOK_REDIRECT_URI"),
        local_callback_url=_required("TIKTOK_LOCAL_CALLBACK_URL"),
        scopes=os.getenv("TIKTOK_SCOPES", "video.publish,video.upload").strip(),
        verify_prefix=_required("TIKTOK_VERIFY_PREFIX"),
        media_base_url=_required("TIKTOK_MEDIA_BASE_URL"),
        flask_host=os.getenv("FLASK_HOST", "127.0.0.1").strip(),
        flask_port=int(os.getenv("FLASK_PORT", "8765")),
        token_store_path=(ROOT / token_store_raw).resolve(),
        netlify_auth_token=os.getenv("NETLIFY_AUTH_TOKEN", "").strip(),
        netlify_site_id=os.getenv("NETLIFY_SITE_ID", "").strip(),
        netlify_deploy_poll_seconds=int(os.getenv("NETLIFY_DEPLOY_POLL_SECONDS", "3")),
    )
