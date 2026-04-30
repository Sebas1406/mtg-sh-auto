from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tiktok_integration.publish_helpers import load_queue_entry, resolve_report_id


LEGAL_MEDIA_DIR = ROOT / "legal-site" / "media"


def main() -> None:
    if len(sys.argv) > 2:
        raise SystemExit("Usage: python automation/verify_publish_bundle.py [report_id]")

    report_id = resolve_report_id(sys.argv[1] if len(sys.argv) == 2 else None)
    queue = load_queue_entry(report_id)
    media_dir = LEGAL_MEDIA_DIR / report_id

    if not media_dir.exists():
        raise SystemExit(f"Missing media directory: {media_dir}")

    public_files = sorted(path for path in media_dir.iterdir() if path.is_file())
    if len(public_files) < 5:
        raise SystemExit(f"Expected at least 5 public media files in {media_dir}, found {len(public_files)}.")

    queue_images = queue.get("images", [])
    if len(queue_images) != 5:
        raise SystemExit(f"Expected 5 images in queue payload, found {len(queue_images)}.")

    print(f"Bundle verified for {report_id}")
    print(f"Queue file: publish_queue/{report_id}.json")
    print(f"Public media directory: legal-site/media/{report_id}")
    for path in public_files:
        print(path.name)


if __name__ == "__main__":
    main()
