from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def audit(report_id: str) -> dict:
    paths = {
        "manifest": ROOT / "deck_manifests" / f"{report_id}.json",
        "validation": ROOT / "deck_validation" / f"{report_id}.json",
        "report": ROOT / "report_data" / f"{report_id}.json",
        "queue": ROOT / "publish_queue" / f"{report_id}.json",
    }
    missing = [name for name, path in paths.items() if not path.exists()]
    if missing:
        return {"report_id": report_id, "status": "fail", "errors": [f"Missing {name}" for name in missing]}
    artifacts = {name: load(path) for name, path in paths.items()}
    hashes = {artifact.get("deck_hash") for artifact in artifacts.values()}
    manifest = artifacts["manifest"]
    report = artifacts["report"]
    queue = artifacts["queue"]
    errors = []
    if hashes == {None} or len(hashes) != 1:
        errors.append("Deck hashes do not match")
    if artifacts["validation"].get("status") != "pass":
        errors.append("Validation did not pass")
    if (manifest.get("stats") or {}).get("total_cards") != 100:
        errors.append("Manifest total is not 100")
    if len(queue.get("images") or []) != 6:
        errors.append("Queue does not contain six images")
    manifest_names = {card.get("name") for card in manifest.get("mainboard") or []}
    featured_names = {card.get("name") for card in report.get("featured_cards") or []}
    if not featured_names.issubset(manifest_names):
        errors.append("A featured card is not in the manifest")
    if report.get("language") != "English":
        errors.append("Report language is not English")
    return {
        "report_id": report_id,
        "commander": report.get("commander", {}).get("name"),
        "status": "fail" if errors else "pass",
        "errors": errors,
        "deck_hash": manifest.get("deck_hash"),
        "cards": (manifest.get("stats") or {}).get("total_cards"),
        "identity": manifest.get("color_identity"),
        "commander_count": (manifest.get("stats") or {}).get("commander_cards"),
        "queue_status": queue.get("status"),
        "slides": len(queue.get("images") or []),
        "featured_cards": len(featured_names),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--require-passed", type=int, default=3)
    args = parser.parse_args()
    validation_paths = sorted(
        (ROOT / "deck_validation").glob("*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    rows = []
    for path in validation_paths:
        validation = load(path)
        if validation.get("schema_version") != 2:
            continue
        report_id = validation.get("report_id") or path.stem
        if not (ROOT / "publish_queue" / f"{report_id}.json").exists():
            continue
        rows.append(audit(report_id))
        if len(rows) >= args.limit:
            break
    passed = sum(row["status"] == "pass" for row in rows)
    payload = {
        "audited_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "required_passed": args.require_passed,
        "passed": passed,
        "status": "pass" if passed >= args.require_passed and all(row["status"] == "pass" for row in rows) else "fail",
        "runs": rows,
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = OUTPUT_DIR / "commander_shadow_run_audit.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if payload["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
