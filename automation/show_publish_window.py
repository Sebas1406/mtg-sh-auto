from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUEUE_DIR = ROOT / "publish_queue"
SCHEDULE_PATH = Path(__file__).resolve().parent / "daily_publish_schedule.json"


def newest_queue_entry() -> Path | None:
    matches = sorted(QUEUE_DIR.glob("*.json"), key=lambda path: path.stat().st_mtime)
    return matches[-1] if matches else None


def main() -> None:
    weekday_arg = sys.argv[1].lower() if len(sys.argv) > 1 else datetime.now().strftime("%A").lower()
    schedule = json.loads(SCHEDULE_PATH.read_text(encoding="utf-8"))
    publish_time = schedule["publish_times"].get(weekday_arg)
    latest = newest_queue_entry()
    if latest is None:
        print("No publish queue entry found.")
        return

    payload = json.loads(latest.read_text(encoding="utf-8"))
    print(f"Today: {weekday_arg}")
    print(f"Suggested publish time ({schedule['timezone']}): {publish_time}")
    print(f"Commander: {payload['commander']}")
    print(f"Caption:\n{payload['caption']}\n")
    print("Images:")
    for image_path in payload["images"]:
        print(image_path)


if __name__ == "__main__":
    main()
