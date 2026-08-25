from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.async_api import async_playwright


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "report_data"
OUTPUT_DIR = ROOT / "tiktok_assets"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
TEMPLATE_NAME = "builder_report_slide.html.j2"
VIEWPORT = {"width": 1080, "height": 1920}
FOOTER_HANDLE = "@sebastianhurtado92"

IDENTITY_ACCENTS = {
    "W": "#d6b86b",
    "U": "#4f8fb9",
    "B": "#8b6a91",
    "R": "#c65d43",
    "G": "#668b5a",
    "C": "#9b8d7a",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def slugify_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")


def blend_hex(colors: list[str]) -> str:
    if not colors:
        return IDENTITY_ACCENTS["C"]
    triples = [tuple(int(color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)) for color in colors]
    average = tuple(sum(value[index] for value in triples) // len(triples) for index in range(3))
    return "#" + "".join(f"{channel:02x}" for channel in average)


def build_theme(data: dict) -> dict:
    identity = data.get("commander", {}).get("color_identity") or ["C"]
    accent = blend_hex([IDENTITY_ACCENTS.get(color, IDENTITY_ACCENTS["C"]) for color in identity])
    return {
        "ink": "#25170f",
        "deep": "#2b1810",
        "wood": "#55331f",
        "paper": "#ead6b1",
        "paper_light": "#f8edda",
        "muted": "#846f59",
        "accent": accent,
        "cream": "#fff8e9",
        "success": "#5f825d",
    }


def _metric(label: str, value: object) -> dict:
    return {"label": label, "value": str(value)}


def build_cover_slide(data: dict) -> dict:
    stats = data.get("stats") or {}
    commander_cards = data.get("commander", {}).get("cards") or [data.get("commander", {})]
    commander_urls = [card.get("image_url", "") for card in commander_cards if card.get("image_url")]
    return {
        "kind": "cover",
        "filename": "01_deck_promise",
        "eyebrow": "COMMANDER BUILDER REPORT",
        "title": data.get("commander", {}).get("name", "Commander"),
        "promise": data.get("summary_short") or data.get("summary", ""),
        "commander_card_urls": commander_urls,
        "paired_commanders": len(commander_urls) == 2,
        "badge": data.get("validation_badge", "VALIDATION REQUIRED"),
        "metrics": [
            _metric("BRACKET", data.get("bracket", "—")),
            _metric("CARDS", stats.get("total_cards", "—")),
            _metric("LANDS", stats.get("land_count", "—")),
            _metric("AVG MV", stats.get("average_mana_value", "—")),
        ],
    }


def build_skeleton_slide(data: dict) -> dict:
    stats = data.get("stats") or {}
    roles = stats.get("role_counts") or {}
    return {
        "kind": "skeleton",
        "filename": "02_deck_skeleton",
        "eyebrow": "BUILD THE FOUNDATION",
        "title": "DECK SKELETON",
        "subtitle": "A useful deck starts with enough mana, cards, answers, and real ways to close.",
        "stats": [
            _metric("LANDS", stats.get("land_count", 0)),
            _metric("RAMP", roles.get("ramp", 0)),
            _metric("CARD ADVANTAGE", roles.get("draw", 0)),
            _metric("INTERACTION", int(roles.get("interaction", 0)) + int(roles.get("board_wipe", 0))),
            _metric("PROTECTION", roles.get("protection", 0)),
            _metric("WIN CONDITIONS", roles.get("wincon", 0)),
        ],
        "curve": stats.get("curve") or [],
        "validation_lines": [
            "Exact 100-card count",
            "Commander color identity",
            "Paper legality and singleton",
            "Bracket and Game Changers",
        ],
    }


def prepare_feature_card(card: dict) -> dict:
    return {
        "name": card.get("name", ""),
        "image_url": card.get("image_url", ""),
        "tag": card.get("feature_role") or (card.get("primary_role") or card.get("role") or "essential").replace("_", " ").upper(),
        "reason": card.get("feature_reason") or card.get("why_in_deck") or "Supports the commander's primary plan.",
    }


def build_feature_slides(data: dict) -> list[dict]:
    slides = []
    groups = data.get("featured_groups") or []
    for index, group in enumerate(groups, start=3):
        slides.append(
            {
                "kind": "feature",
                "filename": f"{index:02d}_{slugify_text(group.get('title', 'key-cards'))}",
                "eyebrow": f"PACKAGE {index - 2} OF {len(groups)}",
                "title": group.get("title", "KEY CARDS"),
                "subtitle": group.get("subtitle", ""),
                "cards": [prepare_feature_card(card) for card in (group.get("cards") or [])[:4]],
                "cta": data.get("full_decklist", {}).get("cta") if index == len(groups) + 2 else "",
            }
        )
    return slides


def build_slide_specs(data: dict) -> list[dict]:
    slides = [build_cover_slide(data), build_skeleton_slide(data), *build_feature_slides(data)]
    if len(slides) != 6:
        raise ValueError(f"Report V2 requires exactly 6 slides; built {len(slides)}.")
    return slides


async def screenshot_html(browser, html_path: Path, png_path: Path) -> None:
    page = await browser.new_page(viewport=VIEWPORT, device_scale_factor=1)
    await page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
    await page.screenshot(path=str(png_path), full_page=True)
    await page.close()


async def render_report_async(browser, template, data: dict, output_dir: Path) -> None:
    if data.get("schema_version") != 2:
        raise ValueError(f"Only validated Report V2 data can be rendered: {data.get('report_id')}")
    if (data.get("validation") or {}).get("status") != "pass":
        raise ValueError(f"Blocked report cannot be rendered: {data.get('report_id')}")
    output_dir.mkdir(parents=True, exist_ok=True)
    for existing in output_dir.glob("*"):
        if existing.is_file():
            existing.unlink()
    context = {
        "footer_handle": FOOTER_HANDLE,
        "theme": build_theme(data),
        "commander_name": data.get("commander", {}).get("name", ""),
    }
    for slide in build_slide_specs(data):
        html = template.render(**context, slide=slide)
        html_path = output_dir / f"{slide['filename']}.html"
        png_path = output_dir / f"{slide['filename']}.png"
        html_path.write_text(html, encoding="utf-8")
        await screenshot_html(browser, html_path, png_path)


async def main_async() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_paths = sorted(DATA_DIR.glob("*.json"))
    v2_paths = [path for path in json_paths if load_json(path).get("schema_version") == 2]
    if not v2_paths:
        print("No validated Report V2 files found.")
        return
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=select_autoescape(["html"]))
    template = env.get_template(TEMPLATE_NAME)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        try:
            for path in v2_paths:
                data = load_json(path)
                await render_report_async(browser, template, data, OUTPUT_DIR / data["report_id"])
        finally:
            await browser.close()


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
