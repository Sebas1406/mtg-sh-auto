from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tiktok_integration.config import load_settings
from tiktok_integration.netlify_deploy import create_deploy, get_deploy
from tiktok_integration.publish_helpers import build_public_urls, load_queue_entry, stage_queue_media
from tiktok_integration.tiktok_api import TikTokAPI
from tiktok_integration.token_store import TokenStore


LEGAL_SITE_DIR = ROOT / "legal-site"
PUBLISH_RUNS_DIR = ROOT / "publish_runs"


def split_caption(queue: dict) -> tuple[str, str]:
    caption = (queue.get("caption") or "").strip()
    parts = [part.strip() for part in caption.splitlines() if part.strip()]
    if not parts:
        return ("MTG Auto Publisher", "")
    return (parts[0], "\n".join(parts[1:]))


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python automation/run_tiktok_inbox_pipeline.py <report_id>")

    report_id = sys.argv[1]
    settings = load_settings()
    api = TikTokAPI(settings)
    token_store = TokenStore(settings.token_store_path)
    tokens = token_store.load()
    access_token = tokens.get("access_token", "")
    if not access_token:
        raise SystemExit("Missing TikTok access token. Run the OAuth flow first.")

    staged = [str(path) for path in stage_queue_media(report_id)]
    deploy = create_deploy(
        auth_token=settings.netlify_auth_token,
        site_id=settings.netlify_site_id,
        source_dir=LEGAL_SITE_DIR,
        production=True,
    )
    deploy_id = deploy["id"]
    while True:
        current = get_deploy(auth_token=settings.netlify_auth_token, deploy_id=deploy_id)
        if current.get("state") == "ready":
            break
        if current.get("state") == "error":
            raise SystemExit(json.dumps({"deploy": current}, ensure_ascii=False, indent=2))
        time.sleep(settings.netlify_deploy_poll_seconds)

    queue = load_queue_entry(report_id)
    title, description = split_caption(queue)
    image_urls = build_public_urls(report_id, settings.media_base_url)
    publish = api.init_photo_post(
        access_token,
        image_urls=image_urls,
        title=title,
        description=description,
        post_mode="MEDIA_UPLOAD",
    )
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
        "staged_files": staged,
        "image_urls": image_urls,
        "deploy": current,
        "publish": publish,
        "status": last_status,
    }
    PUBLISH_RUNS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = PUBLISH_RUNS_DIR / f"{report_id}.json"
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
