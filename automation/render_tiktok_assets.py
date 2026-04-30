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
TEMPLATE_NAME = "deck_case_slide.html.j2"
VIEWPORT = {"width": 1080, "height": 1920}
FOOTER_HANDLE = "@sebastianhurtado92"
WATERMARK_HANDLE = "@sebastianhurtado92"

SECTION_LABELS = {
    "Artefactos": "Artifacts",
    "Encantamientos": "Enchantments",
    "Criaturas": "Creatures",
    "Instantaneos": "Instants",
    "Conjuros": "Sorceries",
    "Tierras": "Lands",
    "Planeswalkers": "Planeswalkers",
}

COLOR_THEME = {
    "W": {"paper": "#ead7a4", "light": "#fbf3dc", "shadow": "#d5bc80"},
    "U": {"paper": "#c9d9e5", "light": "#edf5fb", "shadow": "#97afc3"},
    "B": {"paper": "#d8d0df", "light": "#f2eef6", "shadow": "#a28fae"},
    "R": {"paper": "#ebc4ab", "light": "#f9e6d6", "shadow": "#d29b7b"},
    "G": {"paper": "#d0d7b0", "light": "#eef3dc", "shadow": "#a8b387"},
    "C": {"paper": "#ddd7ce", "light": "#f6f2ec", "shadow": "#b4ab9b"},
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def slugify_text(text: str) -> str:
    lowered = text.lower().replace("&", "and")
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    return lowered.strip("-")


def metric_size(value: str) -> str:
    length = len(value)
    if length <= 3:
        return "big"
    if length <= 7:
        return "medium"
    return "small"


def budget_text(data: dict) -> str:
    total = data.get("deck_price", {}).get("deck_estimate")
    if total is None:
        return data.get("price", {}).get("value", "--")
    rounded = int(round(total))
    return f"${rounded}"


def blend_hex(colors: list[str]) -> str:
    if not colors:
        return "#ead29a"
    triples = []
    for color in colors:
        color = color.lstrip("#")
        triples.append(tuple(int(color[i:i + 2], 16) for i in (0, 2, 4)))
    avg = tuple(sum(channel[i] for channel in triples) // len(triples) for i in range(3))
    return "#" + "".join(f"{value:02x}" for value in avg)


def rgba_from_hex(color: str, alpha: float) -> str:
    color = color.lstrip("#")
    r, g, b = (int(color[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {alpha})"


def build_theme(data: dict) -> dict:
    identities = data.get("commander", {}).get("color_identity") or ["C"]
    palette = [COLOR_THEME.get(identity, COLOR_THEME["C"]) for identity in identities] or [COLOR_THEME["C"]]
    paper = blend_hex([entry["paper"] for entry in palette])
    light = blend_hex([entry["light"] for entry in palette])
    shadow = blend_hex([entry["shadow"] for entry in palette])
    tint = rgba_from_hex(blend_hex([entry["paper"] for entry in palette]), 0.34)
    icon = blend_hex([entry["shadow"] for entry in palette])
    return {
        "paper": paper,
        "light": light,
        "shadow": shadow,
        "tint": tint,
        "icon": icon,
    }


def short_style(playstyle: str) -> str:
    text = (playstyle or "").lower()
    style_map = [
        ("enchant", "ENCHANTRESS"),
        ("voltron", "VOLTRON"),
        ("blink", "BLINK"),
        ("control", "CONTROL"),
        ("token", "TOKENS"),
        ("storm", "STORM"),
        ("aristocrat", "ARISTOCRATS"),
        ("artifact", "ARTIFACTS"),
        ("ramp", "RAMP"),
        ("spellslinger", "SPELLSLINGER"),
        ("burn", "BURN"),
        ("combat", "COMBAT"),
        ("stompy", "STOMPY"),
        ("midrange", "MIDRANGE"),
        ("graveyard", "GRAVEYARD"),
    ]
    for needle, label in style_map:
        if needle in text:
            return label

    words = re.findall(r"[A-Za-zÁÉÍÓÚáéíóúñÑ0-9]+", playstyle or "")
    if not words:
        return "MIDRANGE"
    return words[0].upper()


def uppercase_style(playstyle: str) -> str:
    return short_style(playstyle)


def pilot_text(data: dict) -> str:
    difficulty = (data.get("difficulty") or "").strip().upper()
    if not difficulty:
        return "MED"
    compact = difficulty.replace("MEDIA-", "M-").replace("ALTA", "HIGH").replace("MEDIA", "MID").replace("BAJA", "LOW")
    return compact[:8]


def label_from_card(card: dict) -> str:
    oracle = (card.get("oracle_text") or "").lower()
    role = (card.get("role") or "").lower()
    name = (card.get("name") or "").lower()

    if "search your library" in oracle or "tutor" in name:
        return "TUTOR"
    if "extra combat" in oracle or "wins the game" in oracle or role == "finisher":
        return "WINCON"
    if "double strike" in oracle or "combo" in name:
        return "COMBO"
    if "hexproof" in oracle or "indestructible" in oracle or role == "protection":
        return "PROTECT"
    if "destroy target" in oracle or "exile target" in oracle or "counter target" in oracle or role == "interaction":
        return "REMOVAL"
    if role == "draw" or "draw" in oracle:
        return "DRAW"
    if role == "ramp":
        return "RAMP"
    if role == "recursion":
        return "RECUR"
    return "ESSENTIAL"


def card_priority(card: dict) -> tuple[int, float, str]:
    tag = label_from_card(card)
    tag_rank = {
        "WINCON": 100,
        "COMBO": 95,
        "TUTOR": 90,
        "ESSENTIAL": 85,
        "RAMP": 80,
        "DRAW": 78,
        "REMOVAL": 76,
        "PROTECT": 74,
        "RECUR": 72,
    }.get(tag, 60)
    prices = card.get("prices") or {}
    price_value = 0.0
    for key in ("usd", "usd_foil", "eur"):
        if prices.get(key):
            try:
                price_value = float(prices[key])
                break
            except ValueError:
                pass
    return (-tag_rank, -price_value, card.get("name", ""))


def prepare_card(card: dict) -> dict:
    return {
        "name": card["name"],
        "image_url": card.get("image_url", ""),
        "tag": label_from_card(card),
    }


def pick_cards(
    cards: list[dict],
    limit: int = 9,
    preferred_sections: list[str] | None = None,
    exclude_names: set[str] | None = None,
) -> list[dict]:
    preferred_sections = preferred_sections or []
    exclude_names = exclude_names or set()

    ordered: list[dict] = []
    seen: set[str] = set(exclude_names)

    pools = []
    if preferred_sections:
        pools.append([card for card in cards if card.get("section") in preferred_sections])
    pools.append(cards)

    for pool in pools:
        for card in sorted(pool, key=card_priority):
            name = card.get("name")
            if not name or name in seen:
                continue
            seen.add(name)
            ordered.append(card)
            if len(ordered) >= limit:
                return ordered
    return ordered


def top_nonland_sections(data: dict, include_creatures: bool = False) -> list[str]:
    counts = data.get("stats", {}).get("section_counts", {})
    blocked = {"Tierras"}
    if not include_creatures:
        blocked.add("Criaturas")
    ranked = [(section, count) for section, count in counts.items() if section not in blocked and count > 0]
    ranked.sort(key=lambda item: (-item[1], item[0]))
    return [section for section, _ in ranked]


def build_mix_title(data: dict) -> str:
    available = set(top_nonland_sections(data, include_creatures=False))
    if not available:
        return "Core Cards"
    labels = []
    if "Instantaneos" in available or "Conjuros" in available:
        labels.append("Spells")
    if "Encantamientos" in available:
        labels.append("Enchantments")
    if "Artefactos" in available:
        labels.append("Artifacts")
    if "Planeswalkers" in available and len(labels) < 3:
        labels.append("Planeswalkers")
    if not labels:
        labels = [SECTION_LABELS.get(section, section) for section in list(available)[:3]]
    return " & ".join(labels[:3])


def build_cover_slide(data: dict) -> dict:
    metrics = [
        {"label": "BRACKET", "value": str(data.get("bracket") or "--")},
        {"label": "BUDGET", "value": budget_text(data)},
        {"label": "STYLE", "value": short_style(data.get("playstyle", ""))},
        {"label": "PILOT", "value": pilot_text(data)},
    ]
    for metric in metrics:
        metric["size"] = metric_size(metric["value"])

    return {
        "kind": "cover",
        "filename": "01_cover_deck_case",
        "title": uppercase_style(data.get("playstyle", "")),
        "commander_card_url": data["commander"].get("image_url", ""),
        "metrics": metrics,
    }


def build_grid_slides(data: dict) -> list[dict]:
    cards = data.get("cards", [])
    used: set[str] = set()
    slides: list[dict] = []

    mix_cards = pick_cards(
        cards,
        limit=9,
        preferred_sections=["Encantamientos", "Artefactos", "Instantaneos", "Conjuros", "Planeswalkers"],
        exclude_names=used,
    )
    used.update(card["name"] for card in mix_cards)
    slides.append(
        {
            "kind": "mix",
            "filename": f"02_{slugify_text(build_mix_title(data))}",
            "title": build_mix_title(data),
            "cards": [prepare_card(card) for card in mix_cards],
            "show_watermark": False,
        }
    )

    spell_cards = pick_cards(
        cards,
        limit=9,
        preferred_sections=["Instantaneos", "Conjuros"],
        exclude_names=used,
    )
    used.update(card["name"] for card in spell_cards)
    slides.append(
        {
            "kind": "section",
            "filename": "03_spells",
            "title": "Spells",
            "cards": [prepare_card(card) for card in spell_cards],
            "show_watermark": True,
        }
    )

    creature_cards = pick_cards(
        cards,
        limit=9,
        preferred_sections=["Criaturas"],
        exclude_names=used,
    )
    used.update(card["name"] for card in creature_cards)
    slides.append(
        {
            "kind": "section",
            "filename": "04_creatures",
            "title": "Creatures",
            "cards": [prepare_card(card) for card in creature_cards],
            "show_watermark": False,
        }
    )

    counts = data.get("stats", {}).get("section_counts", {})
    if counts.get("Artefactos", 0) >= counts.get("Encantamientos", 0):
        final_title = "Artifacts"
        preferred_sections = ["Artefactos"]
    else:
        final_title = "Enchantments"
        preferred_sections = ["Encantamientos"]

    final_cards = pick_cards(cards, limit=9, preferred_sections=preferred_sections, exclude_names=used)
    if len(final_cards) < 9:
        final_cards = pick_cards(
            cards,
            limit=9,
            preferred_sections=preferred_sections + ["Artefactos", "Encantamientos"],
            exclude_names=set(),
        )
    slides.append(
        {
            "kind": "section",
            "filename": f"05_{slugify_text(final_title)}",
            "title": final_title,
            "cards": [prepare_card(card) for card in final_cards[:9]],
            "show_watermark": True,
        }
    )

    return slides


def build_slide_specs(data: dict) -> list[dict]:
    return [build_cover_slide(data), *build_grid_slides(data)]


async def screenshot_html(browser, html_path: Path, png_path: Path) -> None:
    page = await browser.new_page(viewport=VIEWPORT, device_scale_factor=1)
    await page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
    await page.screenshot(path=str(png_path), full_page=True)
    await page.close()


async def render_report_async(browser, template, data: dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for existing in output_dir.glob("*"):
        if existing.is_file():
            existing.unlink()

    context_base = {
        "deck_case_title": uppercase_style(data.get("playstyle", "")),
        "commander_name": data["commander"].get("name", ""),
        "brand_top_text": "Commander of the Day",
        "footer_handle": FOOTER_HANDLE,
        "watermark_handle": WATERMARK_HANDLE,
        "theme": build_theme(data),
    }

    for slide in build_slide_specs(data):
        html = template.render(**context_base, slide=slide)
        html_path = output_dir / f"{slide['filename']}.html"
        png_path = output_dir / f"{slide['filename']}.png"
        html_path.write_text(html, encoding="utf-8")
        await screenshot_html(browser, html_path, png_path)


async def main_async() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_paths = sorted(DATA_DIR.glob("*.json"))
    if not json_paths:
        print("No se encontraron archivos JSON en report_data/.")
        return

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template(TEMPLATE_NAME)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        try:
            written = []
            for path in json_paths:
                data = load_json(path)
                out_dir = OUTPUT_DIR / data["report_id"]
                await render_report_async(browser, template, data, out_dir)
                written.append(str(out_dir))
        finally:
            await browser.close()

    print("Assets generados:")
    for output in written:
        print(output)


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
