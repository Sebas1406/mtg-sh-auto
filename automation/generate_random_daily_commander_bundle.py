from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automation.bundle_queue import build_queue
from automation.commander_deck_engine import build_deck_manifest, write_manifest, write_moxfield_decklist
from automation.commander_policy import load_game_changers
from automation.edhrec_recommendations import fetch_commander_page
from automation.render_tiktok_assets import TEMPLATES_DIR, TEMPLATE_NAME, load_json, render_report_async
from automation.report_v2 import write_report_v2
from automation.validate_commander_deck import validate_manifest, write_validation


ASSETS_DIR = ROOT / "tiktok_assets"
SELECTION_DIR = ROOT / "commander_selection_runs"
SCRYFALL_RANDOM_URL = "https://api.scryfall.com/cards/random"
SCRYFALL_QUERY = "legal:commander is:commander game:paper -is:funny -is:digital"
USER_AGENT = "mtg-sh-auto/2.0 commander-selector"


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower().replace("&", "and")).strip("-")


def fetch_random_card(query: str) -> dict:
    request = urllib.request.Request(
        f"{SCRYFALL_RANDOM_URL}?q={urllib.parse.quote(query)}",
        headers={"User-Agent": USER_AGENT, "Accept": "application/json;q=0.9,*/*;q=0.8"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        card = json.load(response)
    if card.get("object") != "card" or not card.get("name"):
        raise RuntimeError(f"Scryfall did not return a card for query: {query}")
    if (card.get("legalities") or {}).get("commander") != "legal" or "paper" not in (card.get("games") or []):
        raise RuntimeError(f"Scryfall returned an invalid Commander candidate: {card.get('name')}")
    return card


def resolve_commander_configuration(selected: dict) -> list[dict]:
    from automation.export_report_data import fetch_scryfall_card

    line = selected.get("type_line") or ""
    text = selected.get("oracle_text") or ""
    lowered = text.lower()
    if "Background" in line:
        partner = fetch_random_card('legal:commander game:paper o:"Choose a Background" -is:funny')
        return [partner, selected]
    if "choose a background" in lowered:
        background = fetch_random_card("legal:commander game:paper t:background -is:funny")
        return [selected, background]
    if "doctor's companion" in lowered:
        doctor = fetch_random_card("legal:commander game:paper t:doctor is:commander -is:funny")
        return [doctor, selected]
    partner_match = re.search(r"Partner with ([^\n(]+)", text, flags=re.IGNORECASE)
    if partner_match:
        partner_name = partner_match.group(1).strip().rstrip(".")
        return [selected, fetch_scryfall_card(partner_name)]
    return [selected]


def selection_payload(report_id: str, selected_at: datetime, selected: dict, commanders: list[dict], override: str = "") -> dict:
    return {
        "report_id": report_id,
        "selected_at": selected_at.isoformat(timespec="seconds"),
        "source": "Scryfall Cards API",
        "endpoint": SCRYFALL_RANDOM_URL,
        "query": SCRYFALL_QUERY,
        "selection_method": (
            f"explicit test override: {override}"
            if override
            else "server-side random card from the live commander-capable universe"
        ),
        "selected_card": {
            "id": selected.get("id"),
            "oracle_id": selected.get("oracle_id"),
            "name": selected.get("name"),
            "released_at": selected.get("released_at"),
            "scryfall_uri": selected.get("scryfall_uri"),
        },
        "resolved_commanders": [
            {"id": card.get("id"), "oracle_id": card.get("oracle_id"), "name": card.get("name")}
            for card in commanders
        ],
    }


async def render_report(json_path: Path, output_dir: Path) -> None:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    from playwright.async_api import async_playwright

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=select_autoescape(["html"]))
    template = env.get_template(TEMPLATE_NAME)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        try:
            await render_report_async(browser, template, load_json(json_path), output_dir)
        finally:
            await browser.close()


def main() -> None:
    selected_at = datetime.now()
    target_bracket = int(os.environ.get("COMMANDER_TARGET_BRACKET", "3"))
    if target_bracket not in {1, 2, 3, 4, 5}:
        raise ValueError("COMMANDER_TARGET_BRACKET must be between 1 and 5.")

    override = os.environ.get("COMMANDER_OVERRIDE", "").strip()
    if override:
        from automation.export_report_data import fetch_scryfall_card

        selected = fetch_scryfall_card(override)
    else:
        selected = fetch_random_card(SCRYFALL_QUERY)
    commanders = resolve_commander_configuration(selected)
    report_id = f"{selected_at.strftime('%Y-%m-%d-%H%M')}-{slugify('-'.join(card['name'] for card in commanders))}"
    evidence = selection_payload(report_id, selected_at, selected, commanders, override=override)
    SELECTION_DIR.mkdir(parents=True, exist_ok=True)
    evidence_path = SELECTION_DIR / f"{report_id}.json"
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")

    edhrec_anchor = next((card for card in commanders if "Background" not in (card.get("type_line") or "")), commanders[0])
    try:
        edhrec_page = fetch_commander_page(edhrec_anchor["name"])
    except Exception:
        edhrec_page = {}
    policy = load_game_changers(force_refresh=True)
    manifest = build_deck_manifest(
        report_id=report_id,
        commanders=commanders,
        target_bracket=target_bracket,
        edhrec_page=edhrec_page,
        game_changer_policy=policy,
        selection_evidence=evidence,
    )
    manifest_path = write_manifest(manifest)
    validation = validate_manifest(manifest, verify_live_data=True)
    validation_path = write_validation(validation)
    if validation["status"] != "pass":
        failures = [gate["detail"] for gate in validation["gates"] if gate["status"] == "fail" and gate["severity"] == "critical"]
        raise RuntimeError("Commander deck failed strict validation:\n- " + "\n- ".join(failures))

    decklist_path = write_moxfield_decklist(manifest)
    markdown_path, json_path, report = write_report_v2(manifest, validation, decklist_path)
    asset_dir = ASSETS_DIR / report_id
    asyncio.run(render_report(json_path, asset_dir))
    queue_path = build_queue(report, validation, asset_dir)

    print(
        json.dumps(
            {
                "report_id": report_id,
                "commander": report["commander"]["name"],
                "deck_hash": manifest["deck_hash"],
                "validation_status": validation["status"],
                "selection_evidence": str(evidence_path),
                "manifest_path": str(manifest_path),
                "validation_path": str(validation_path),
                "decklist_path": str(decklist_path),
                "report_path": str(markdown_path),
                "json_path": str(json_path),
                "queue_path": str(queue_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
