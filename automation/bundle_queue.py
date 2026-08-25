from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUEUE_DIR = ROOT / "publish_queue"
PUBLISH_MODE_PATH = ROOT / "automation" / "publish_mode.json"
EXPECTED_SLIDES = 6


def project_path(path: Path) -> str:
    """Return a repository-relative path so queue items work on Windows and CI."""
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def load_publish_mode() -> dict:
    if not PUBLISH_MODE_PATH.exists():
        return {"mode": "draft_only", "reason": "Publish mode file is missing."}
    return json.loads(PUBLISH_MODE_PATH.read_text(encoding="utf-8"))


def build_caption(report: dict) -> str:
    commander = report.get("commander", {}).get("name", "Commander")
    bracket = report.get("bracket", "?")
    archetype = report.get("playstyle", "Commander deck")
    return "\n".join(
        [
            f"Commander Build: {commander}",
            f"Bracket {bracket} | {archetype} | Verified 100-card deck",
            "The carousel shows the cards that matter; the complete list is in the deck link.",
            "#mtg #magicthegathering #commander #edh #deckbuilding #decktech",
        ]
    )


def build_queue(report: dict, validation: dict, asset_dir: Path) -> Path:
    if validation.get("status") != "pass":
        raise RuntimeError("Cannot create a publish queue item for a deck that failed validation.")
    if validation.get("deck_hash") != report.get("deck_hash"):
        raise RuntimeError("Report and validation deck hashes do not match.")
    pngs = sorted(asset_dir.glob("*.png"))
    if len(pngs) != EXPECTED_SLIDES:
        raise RuntimeError(f"Expected {EXPECTED_SLIDES} rendered slides, found {len(pngs)} in {asset_dir}.")
    mode = load_publish_mode()
    status = "ready_for_publish" if mode.get("mode") == "live" else "shadow_ready"
    payload = {
        "schema_version": 2,
        "report_id": report["report_id"],
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "timezone": "America/Lima",
        "publish_times": {"daily": "08:00"},
        "caption": build_caption(report),
        "commander": report.get("commander", {}).get("name", ""),
        "deck_hash": report.get("deck_hash"),
        "validation_status": validation.get("status"),
        "validation_file": project_path(ROOT / "deck_validation" / f"{report['report_id']}.json"),
        "manifest_file": project_path(ROOT / "deck_manifests" / f"{report['report_id']}.json"),
        "full_decklist": project_path(ROOT / "moxfield_decklists_100" / f"{report['report_id']}.txt"),
        "cover_image": project_path(pngs[0]),
        "images": [project_path(path) for path in pngs],
        "status": status,
        "publish_mode": mode,
        "notes": [
            "Generated from a canonical, validated 100-card Commander manifest.",
            "Every displayed card is present in the validated decklist.",
            "All report and carousel copy is in English.",
        ],
    }
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    path = QUEUE_DIR / f"{report['report_id']}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
