from __future__ import annotations

import json
import sys
import urllib.request


def main() -> None:
    if len(sys.argv) not in {2, 3}:
        raise SystemExit(
            "Usage: python automation/publish_tiktok_queue_item.py <report_id> [auto|direct_post|media_upload]"
        )

    report_id = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) == 3 else "auto"
    url = f"http://127.0.0.1:8765/api/tiktok/publish/{report_id}?mode={mode}"
    request = urllib.request.Request(url, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(body)
        raise SystemExit(exc.code)

    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
