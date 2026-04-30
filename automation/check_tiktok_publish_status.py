from __future__ import annotations

import json
import sys
import urllib.request
from urllib.parse import quote


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python automation/check_tiktok_publish_status.py <publish_id>")

    publish_id = sys.argv[1]
    url = f"http://127.0.0.1:8765/api/tiktok/publish-status/{quote(publish_id, safe='')}"
    with urllib.request.urlopen(url, timeout=30) as response:
        payload = json.load(response)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
