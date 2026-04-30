from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tiktok_integration.config import load_settings
from tiktok_integration.publish_helpers import build_public_urls, load_queue_entry, resolve_report_id
from tiktok_integration.tiktok_api import TikTokAPI, TikTokAPIError
from tiktok_integration.token_runtime import ensure_access_token
from tiktok_integration.token_store import TokenStore


PUBLISH_RUNS_DIR = ROOT / "publish_runs"


def split_caption(queue: dict) -> tuple[str, str]:
    caption = (queue.get("caption") or "").strip()
    parts = [part.strip() for part in caption.splitlines() if part.strip()]
    if not parts:
        return ("MTG Auto Publisher", "")
    return (parts[0], "\n".join(parts[1:]))


def main() -> None:
    if len(sys.argv) > 2:
        raise SystemExit("Usage: python automation/publish_ready_queue_item.py [report_id]")

    report_id = resolve_report_id(sys.argv[1] if len(sys.argv) == 2 else None)
    settings = load_settings()
    api = TikTokAPI(settings)
    token_store = TokenStore(settings.token_store_path)
    access_token, token_data = ensure_access_token(api, token_store)

    queue = load_queue_entry(report_id)
    title, description = split_caption(queue)
    image_urls = build_public_urls(report_id, settings.media_base_url)
    try:
        publish = api.init_photo_post(
            access_token,
            image_urls=image_urls,
            title=title,
            description=description,
            post_mode="MEDIA_UPLOAD",
        )
    except requests.HTTPError as exc:
        cause = exc.__cause__
        if isinstance(cause, TikTokAPIError):
            debug_payload = {
                "report_id": report_id,
                "image_urls": image_urls,
                "status_code": cause.status_code,
                "tiktok_error": cause.error_payload,
                "request_payload": cause.request_payload,
            }
            print(json.dumps(debug_payload, ensure_ascii=False, indent=2))
        raise
    publish_id = publish["data"]["publish_id"]

    last_status = {}
    while True:
        status = api.fetch_publish_status(access_token, publish_id)
        last_status = status
        state = status.get("data", {}).get("status")
        if state in {"FAILED", "PUBLISH_COMPLETE", "SEND_TO_USER_INBOX"}:
            break
        time.sleep(3)

    result = {
        "report_id": report_id,
        "token_fields": sorted(token_data.keys()),
        "image_urls": image_urls,
        "publish": publish,
        "status": last_status,
    }
    PUBLISH_RUNS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = PUBLISH_RUNS_DIR / f"{report_id}.json"
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
