from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tiktok_integration.config import load_settings
from tiktok_integration.netlify_deploy import NetlifyDeployError, create_deploy, get_deploy


LEGAL_SITE_DIR = ROOT / "legal-site"


def main() -> None:
    settings = load_settings()
    deploy = create_deploy(
        auth_token=settings.netlify_auth_token,
        site_id=settings.netlify_site_id,
        source_dir=LEGAL_SITE_DIR,
        production=True,
    )
    deploy_id = deploy["id"]
    result = {"created_deploy": deploy}
    while True:
        current = get_deploy(auth_token=settings.netlify_auth_token, deploy_id=deploy_id)
        result["current_deploy"] = current
        state = current.get("state", "")
        if state == "ready":
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return
        if state == "error":
            raise NetlifyDeployError(json.dumps(result, ensure_ascii=False, indent=2))
        time.sleep(settings.netlify_deploy_poll_seconds)


if __name__ == "__main__":
    main()
