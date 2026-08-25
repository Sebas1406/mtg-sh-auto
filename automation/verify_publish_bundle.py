from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automation.bundle_queue import EXPECTED_SLIDES
from tiktok_integration.publish_helpers import _source_path_parts, load_queue_entry, resolve_report_id


LEGAL_MEDIA_DIR = ROOT / "legal-site" / "media"


def load_required(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"Required quality artifact is missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def parse_moxfield_decklist(path: Path) -> tuple[Counter, Counter]:
    sections = {"commander": Counter(), "mainboard": Counter()}
    current: Counter | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        heading = line.casefold()
        if heading in sections:
            current = sections[heading]
            continue
        if not line:
            continue
        if current is None or " " not in line:
            raise SystemExit(f"Bundle blocked: malformed decklist line: {line!r}.")
        quantity_text, name = line.split(" ", 1)
        try:
            quantity = int(quantity_text)
        except ValueError as exc:
            raise SystemExit(f"Bundle blocked: malformed decklist quantity: {line!r}.") from exc
        if quantity < 1 or not name.strip():
            raise SystemExit(f"Bundle blocked: malformed decklist entry: {line!r}.")
        current[name.strip()] += quantity
    return sections["commander"], sections["mainboard"]


def main() -> None:
    if len(sys.argv) > 2:
        raise SystemExit("Usage: python automation/verify_publish_bundle.py [report_id]")
    report_id = resolve_report_id(sys.argv[1] if len(sys.argv) == 2 else None)
    queue = load_queue_entry(report_id)
    manifest = load_required(ROOT / "deck_manifests" / f"{report_id}.json")
    validation = load_required(ROOT / "deck_validation" / f"{report_id}.json")
    report = load_required(ROOT / "report_data" / f"{report_id}.json")

    hashes = {queue.get("deck_hash"), manifest.get("deck_hash"), validation.get("deck_hash"), report.get("deck_hash")}
    if None in hashes or len(hashes) != 1:
        raise SystemExit("Bundle blocked: queue, manifest, validation, and report deck hashes do not match.")
    if validation.get("status") != "pass" or validation.get("critical_error_count") != 0:
        raise SystemExit("Bundle blocked: strict Commander validation did not pass.")
    if (manifest.get("stats") or {}).get("total_cards") != 100:
        raise SystemExit("Bundle blocked: canonical manifest does not contain exactly 100 cards.")
    if queue.get("validation_status") != "pass":
        raise SystemExit("Bundle blocked: queue is not tied to a passing validation artifact.")

    decklist_path = ROOT / "moxfield_decklists_100" / f"{report_id}.txt"
    if not decklist_path.exists():
        raise SystemExit(f"Bundle blocked: Moxfield import decklist is missing: {decklist_path}.")
    exported_commanders, exported_mainboard = parse_moxfield_decklist(decklist_path)
    expected_commanders = Counter(
        {card["name"]: int(card.get("quantity") or 1) for card in manifest.get("commanders") or []}
    )
    expected_mainboard = Counter(
        {card["name"]: int(card.get("quantity") or 1) for card in manifest.get("mainboard") or []}
    )
    if exported_commanders != expected_commanders or exported_mainboard != expected_mainboard:
        raise SystemExit("Bundle blocked: Moxfield export does not exactly match the canonical manifest.")
    if sum(exported_commanders.values()) + sum(exported_mainboard.values()) != 100:
        raise SystemExit("Bundle blocked: Moxfield export does not contain exactly 100 cards.")

    allow_shadow = os.environ.get("ALLOW_SHADOW_BUNDLE") == "1"
    if queue.get("status") != "ready_for_publish" and not (allow_shadow and queue.get("status") == "shadow_ready"):
        raise SystemExit(f"Bundle blocked: queue status is {queue.get('status')!r}, not ready_for_publish.")

    queue_images = queue.get("images") or []
    if len(queue_images) != EXPECTED_SLIDES:
        raise SystemExit(f"Bundle blocked: expected {EXPECTED_SLIDES} queue images, found {len(queue_images)}.")

    media_dir = LEGAL_MEDIA_DIR / report_id
    if not media_dir.exists():
        raise SystemExit(f"Missing staged media directory: {media_dir}")
    public_files = sorted(path for path in media_dir.iterdir() if path.is_file())
    if len(public_files) != EXPECTED_SLIDES:
        raise SystemExit(f"Expected exactly {EXPECTED_SLIDES} public media files, found {len(public_files)}.")
    expected_public_names = {f"{_source_path_parts(source)[0]}.jpg" for source in queue_images}
    actual_public_names = {path.name for path in public_files}
    if len(expected_public_names) != EXPECTED_SLIDES or actual_public_names != expected_public_names:
        raise SystemExit("Bundle blocked: staged public media does not match the six queue slides.")

    featured = {card.get("name") for card in report.get("featured_cards") or []}
    manifest_names = {card.get("name") for card in manifest.get("mainboard") or []}
    missing_featured = sorted(name for name in featured if name not in manifest_names)
    if missing_featured:
        raise SystemExit("Bundle blocked: displayed cards are missing from the canonical deck:\n- " + "\n- ".join(missing_featured))

    print(f"Bundle verified for {report_id}")
    print(f"Deck hash: {manifest['deck_hash']}")
    print(f"Cards: {manifest['stats']['total_cards']}")
    print(f"Validation: {validation['status']} ({validation['warning_count']} warning(s))")
    print(f"Queue status: {queue['status']}")
    print(f"Public media: {len(public_files)} files")


if __name__ == "__main__":
    main()
