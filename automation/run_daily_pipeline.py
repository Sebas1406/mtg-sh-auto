from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
REPORT_DATA_DIR = ROOT / "report_data"
ASSETS_DIR = ROOT / "tiktok_assets"
QUEUE_DIR = ROOT / "publish_queue"
SCHEDULE_PATH = Path(__file__).resolve().parent / "daily_publish_schedule.json"


def run_step(args: list[str]) -> None:
    print(f"Running: {' '.join(args)}")
    subprocess.run(args, cwd=str(ROOT), check=True)


def newest_path(directory: Path, pattern: str) -> Path | None:
    matches = sorted(directory.glob(pattern), key=lambda path: path.stat().st_mtime)
    return matches[-1] if matches else None


def build_caption(data: dict) -> str:
    commander = data.get("commander", {}).get("name", "Commander")
    style = english_style(data.get("playstyle", "Commander strategy"))
    bracket = data.get("bracket", "?")
    budget = data.get("deck_price", {}).get("deck_estimate")
    budget_text = f"${int(round(budget))}" if isinstance(budget, (int, float)) else "budget TBD"
    hashtags = [
        "#mtg",
        "#magicthegathering",
        "#commander",
        "#edh",
        "#decktech",
        "#tiktokgaming",
    ]
    lines = [
        f"Commander of the Day: {commander}",
        f"Bracket {bracket} | {style} | Budget {budget_text}",
        "5-slide deck case ready to post.",
        " ".join(hashtags),
    ]
    return "\n".join(lines)


def english_style(playstyle: str) -> str:
    text = (playstyle or "").lower()
    replacements = [
        ("mono red", "mono-red"),
        ("de mesa estable", "steady board plan"),
        ("value incremental", "incremental value"),
        ("tokens evasivos", "evasive tokens"),
        ("blink azorius", "azorius blink"),
        ("control blando", "soft control"),
        ("acumulacion de etb", "ETB value"),
        ("tesoros", "treasures"),
        ("impulso", "impulse draw"),
        ("sacrificio", "sacrifice"),
        ("stompy verde", "green stompy"),
        ("ramp explosivo", "explosive ramp"),
        ("presion de combate", "combat pressure"),
        ("dano incremental", "incremental damage"),
        ("remates explosivos", "explosive finishers"),
        ("pingers", "pingers"),
    ]
    converted = playstyle or "Commander strategy"
    for source, target in replacements:
        converted = re.sub(source, target, converted, flags=re.IGNORECASE)
    converted = converted.replace(" y ", " and ")
    converted = converted.replace(" de ", " ")
    converted = converted.replace(" con ", " with ")
    return converted


def build_queue_entry() -> Path:
    latest_json = newest_path(REPORT_DATA_DIR, "*.json")
    if latest_json is None:
        raise FileNotFoundError("No JSON reports found in report_data/.")

    data = json.loads(latest_json.read_text(encoding="utf-8"))
    asset_dir = ASSETS_DIR / data["report_id"]
    pngs = sorted(asset_dir.glob("*.png"))
    if len(pngs) != 5:
        raise RuntimeError(f"Expected 5 PNG files in {asset_dir}, found {len(pngs)}.")

    schedule = json.loads(SCHEDULE_PATH.read_text(encoding="utf-8"))
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    queue_path = QUEUE_DIR / f"{data['report_id']}.json"
    payload = {
        "report_id": data["report_id"],
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "timezone": schedule["timezone"],
        "publish_times": schedule["publish_times"],
        "caption": build_caption(data),
        "commander": data.get("commander", {}).get("name", ""),
        "cover_image": str(pngs[0].resolve()),
        "images": [str(path.resolve()) for path in pngs],
        "status": "ready_for_publish",
        "notes": [
            "Images are in English and ready for TikTok photo post publishing.",
            "Direct posting can be wired later to TikTok Content Posting API for photos.",
        ],
    }
    queue_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return queue_path


def main() -> None:
    python_exe = sys.executable
    run_step([python_exe, "automation/generate_test_reports.py"])
    run_step([python_exe, "automation/export_report_data.py"])
    run_step([python_exe, "automation/render_tiktok_assets.py"])
    queue_path = build_queue_entry()
    print(f"Queued daily post payload: {queue_path}")


if __name__ == "__main__":
    main()
