from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tiktok_integration.publish_helpers import stage_queue_media
from tiktok_integration.publish_helpers import resolve_report_id


def main() -> None:
    if len(sys.argv) > 2:
        raise SystemExit("Usage: python automation/stage_tiktok_media.py [report_id]")
    report_id = resolve_report_id(sys.argv[1] if len(sys.argv) == 2 else None)
    written = stage_queue_media(report_id)
    print(f"Staged {len(written)} images for {report_id}:")
    for path in written:
        print(path)
    print("Redeploy the legal-site folder to your public static host after staging.")


if __name__ == "__main__":
    main()
