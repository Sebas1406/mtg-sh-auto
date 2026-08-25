from __future__ import annotations

import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automation.edhrec_recommendations import audit_deck

REPORTS_DIR = ROOT / "reports"
OUTPUT_DIR = ROOT / "report_data"
CACHE_DIR = ROOT / ".cache" / "scryfall"
SCRYFALL_CACHE_TTL_HOURS = int(os.environ.get("SCRYFALL_CACHE_TTL_HOURS", "24"))

META_PREFIXES = {
    "Fecha de generacion": "date",
    "Hora de generacion": "time",
    "Bracket objetivo": "bracket",
    "Nota de bracket": "bracket_note",
    "Tipo de juego": "playstyle",
    "Dificultad": "difficulty",
    "Precio actual en Card Kingdom": "price_value",
    "Fuente de precio": "price_url",
}
META_ALIASES = {
    "date": ["Fecha de generacion"],
    "time": ["Hora de generacion"],
    "datetime": ["Fecha y hora de generacion"],
    "bracket": ["Bracket objetivo"],
    "bracket_note": ["Nota de bracket", "Nota sobre bracket"],
    "playstyle": ["Tipo de juego"],
    "difficulty": ["Dificultad", "Dificultad de pilotaje"],
    "price_value": ["Precio actual en Card Kingdom", "Precio actual del commander en Card Kingdom"],
    "price_url": ["Fuente de precio"],
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def section_slice(text: str, title: str, next_titles: list[str]) -> str:
    start_match = re.search(rf"^## {re.escape(title)}\s*$", text, re.MULTILINE)
    if not start_match:
        return ""
    start = start_match.end()
    end = len(text)
    for next_title in next_titles:
        match = re.search(rf"^## {re.escape(next_title)}\s*$", text[start:], re.MULTILINE)
        if match:
            end = start + match.start()
            break
    return text[start:end].strip()


def section_slice_any(text: str, titles: list[str], next_titles: list[str]) -> str:
    for title in titles:
        block = section_slice(text, title, next_titles)
        if block:
            return block
    return ""


def parse_bullets(block: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in block.splitlines():
        line = line.strip()
        if not line.startswith("- "):
            continue
        if ":" not in line:
            continue
        key, value = line[2:].split(":", 1)
        clean_key = key.strip().strip("*").strip()
        data[clean_key] = value.strip().strip("*").strip()
    return data


def parse_plan_block(block: str) -> dict[str, str]:
    plan: dict[str, str] = {}
    parts = re.split(r"^### ", block, flags=re.MULTILINE)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        lines = part.splitlines()
        title = lines[0].strip()
        body = "\n".join(lines[1:]).strip()
        plan[title] = body
    return plan


def parse_decklist(block: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current = None
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("### "):
            current = line[4:].strip()
            sections[current] = []
            continue
        if current and line.startswith("1x "):
            sections[current].append(line[3:].strip())
            continue
        if current:
            quantity_match = re.match(r"^(\d+)\s+(.+)$", line)
            if quantity_match:
                quantity = int(quantity_match.group(1))
                card_name = quantity_match.group(2).strip()
                sections[current].extend([card_name] * quantity)
    return sections


def normalize_section_name(name: str) -> str:
    return re.sub(r"\s+\(\d+\)$", "", name).strip()


def normalize_deck_sections(deck_sections: dict[str, list[str]]) -> dict[str, list[str]]:
    normalized: dict[str, list[str]] = {}
    for section, cards in deck_sections.items():
        normalized[normalize_section_name(section)] = cards
    return normalized


def meta_value(meta: dict[str, str], target: str) -> str:
    for key in META_ALIASES.get(target, []):
        if meta.get(key):
            return meta[key]
    return ""


def split_datetime(value: str) -> tuple[str, str]:
    match = re.search(r"(\d{4}-\d{2}-\d{2})\s+(\d{1,2}:\d{2})", value or "")
    if not match:
        return "", ""
    return match.group(1), match.group(2)


def bracket_number(value: str) -> int | None:
    match = re.search(r"\d+", value or "")
    return int(match.group(0)) if match else None


def infer_role(section: str, card_name: str, type_line: str, oracle_text: str) -> str:
    lowered_name = card_name.lower()
    lowered_type = type_line.lower()
    lowered_text = oracle_text.lower()

    if section == "Tierras":
        return "utility_land" if lowered_name not in {"plains", "island", "swamp", "mountain", "forest", "wastes"} else "support"
    if "create a treasure" in lowered_text or "add {" in lowered_text or lowered_name in {"sol ring", "arcane signet", "cultivate", "kodama's reach"}:
        return "ramp"
    if "draw" in lowered_text:
        return "draw"
    if any(token in lowered_text for token in ["destroy target", "exile target", "counter target", "return target", "deals", "fight target"]):
        return "interaction"
    if any(token in lowered_text for token in ["hexproof", "indestructible", "protection from", "phase out"]):
        return "protection"
    if any(token in lowered_text for token in ["create", "token"]) and "token" in lowered_text:
        return "tokens"
    if any(token in lowered_text for token in ["return ", "from your graveyard", "reanimate", "recursion"]):
        return "recursion"
    if any(token in lowered_text for token in ["double", "wins the game", "extra combat", "whenever you cast", "at the beginning of your end step"]):
        return "finisher"
    if "enchantment" in lowered_type or "whenever" in lowered_text:
        return "core_synergy"
    if section in {"Criaturas", "Artefactos", "Encantamientos"}:
        return "value"
    return "support"


def normalized_card_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value or "")
    normalized = normalized.replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", normalized).strip().casefold()


def card_name_aliases(card: dict) -> set[str]:
    aliases = {normalized_card_name(card.get("name", ""))}
    full_name = card.get("name", "")
    if " // " in full_name:
        aliases.update(normalized_card_name(part) for part in full_name.split(" // "))
    for face in card.get("card_faces") or []:
        aliases.add(normalized_card_name(face.get("name", "")))
    aliases.discard("")
    return aliases


def card_matches_requested_name(requested_name: str, card: dict) -> bool:
    return normalized_card_name(requested_name) in card_name_aliases(card)


def read_cached_card(name: str, cache_path: Path) -> dict | None:
    if not cache_path.exists():
        return None
    age_seconds = datetime.now(timezone.utc).timestamp() - cache_path.stat().st_mtime
    if age_seconds > SCRYFALL_CACHE_TTL_HOURS * 3600:
        return None
    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if data.get("object") != "card" or not card_matches_requested_name(name, data):
        return None
    return data


def write_card_cache(requested_name: str, card: dict) -> None:
    if not card_matches_requested_name(requested_name, card):
        raise ValueError(
            f"Scryfall integrity error: requested {requested_name!r}, received {card.get('name')!r}."
        )
    cache_path = CACHE_DIR / f"{urllib.parse.quote(requested_name, safe='')}.json"
    cache_path.write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_scryfall_card(name: str) -> dict:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / f"{urllib.parse.quote(name, safe='')}.json"
    cached = read_cached_card(name, cache_path)
    if cached is not None:
        return cached

    url = f"https://api.scryfall.com/cards/named?exact={urllib.parse.quote(name)}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "codex-mtg-agent/0.2",
            "Accept": "application/json;q=0.9,*/*;q=0.8",
        },
    )
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                data = json.load(response)
                write_card_cache(name, data)
                time.sleep(0.12)
                return data
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt == 4:
                raise
            retry_after = exc.headers.get("Retry-After")
            delay = float(retry_after) if retry_after else (1.5 * (attempt + 1))
            time.sleep(delay)
    raise RuntimeError(f"No se pudo consultar Scryfall para {name}")


def fetch_scryfall_cards(names: list[str]) -> dict[str, dict]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    results: dict[str, dict] = {}
    unresolved: list[str] = []

    for name in names:
        cache_path = CACHE_DIR / f"{urllib.parse.quote(name, safe='')}.json"
        cached = read_cached_card(name, cache_path)
        if cached is None:
            unresolved.append(name)
        else:
            results[name] = cached

    if not unresolved:
        return results

    batch_size = 75
    for index in range(0, len(unresolved), batch_size):
        batch = unresolved[index:index + batch_size]
        payload = json.dumps({"identifiers": [{"name": name} for name in batch]}).encode("utf-8")
        req = urllib.request.Request(
            "https://api.scryfall.com/cards/collection",
            data=payload,
            headers={
                "User-Agent": "codex-mtg-agent/0.2",
                "Accept": "application/json;q=0.9,*/*;q=0.8",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        for attempt in range(5):
            try:
                with urllib.request.urlopen(req, timeout=30) as response:
                    payload_data = json.load(response)
                returned_cards = payload_data.get("data", [])
                returned_by_alias: dict[str, dict] = {}
                for card_data in returned_cards:
                    for alias in card_name_aliases(card_data):
                        returned_by_alias.setdefault(alias, card_data)
                for requested_name in batch:
                    card_data = returned_by_alias.get(normalized_card_name(requested_name))
                    if card_data is None:
                        continue
                    write_card_cache(requested_name, card_data)
                    results[requested_name] = card_data
                time.sleep(0.2)
                break
            except urllib.error.HTTPError as exc:
                if exc.code != 429 or attempt == 4:
                    raise
                retry_after = exc.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else (1.5 * (attempt + 1))
                time.sleep(delay)

    for name in unresolved:
        if name not in results:
            results[name] = fetch_scryfall_card(name)
    return results


def image_url_from_card(card: dict) -> str:
    image_uris = card.get("image_uris") or {}
    if image_uris.get("normal"):
        return image_uris["normal"]
    faces = card.get("card_faces") or []
    for face in faces:
        face_uris = face.get("image_uris") or {}
        if face_uris.get("normal"):
            return face_uris["normal"]
    return ""


def art_crop_url_from_card(card: dict) -> str:
    image_uris = card.get("image_uris") or {}
    if image_uris.get("art_crop"):
        return image_uris["art_crop"]
    faces = card.get("card_faces") or []
    for face in faces:
        face_uris = face.get("image_uris") or {}
        if face_uris.get("art_crop"):
            return face_uris["art_crop"]
    return image_url_from_card(card)


def build_card_entry(name: str, section: str, card: dict) -> dict:
    oracle_text = card.get("oracle_text", "")
    if not oracle_text and card.get("card_faces"):
        oracle_text = " // ".join(face.get("oracle_text", "") for face in card["card_faces"])

    type_line = card.get("type_line", "")
    if not type_line and card.get("card_faces"):
        type_line = " // ".join(face.get("type_line", "") for face in card["card_faces"])

    return {
        "name": card.get("name", name),
        "requested_name": name,
        "scryfall_id": card.get("id", ""),
        "oracle_id": card.get("oracle_id", ""),
        "quantity": 1,
        "section": section,
        "role": infer_role(section, name, type_line, oracle_text),
        "mana_cost": card.get("mana_cost", ""),
        "cmc": card.get("cmc", 0),
        "type_line": type_line,
        "oracle_text": oracle_text.replace("\n", " ").strip(),
        "color_identity": card.get("color_identity", []),
        "legalities": card.get("legalities", {}),
        "games": card.get("games", []),
        "security_stamp": card.get("security_stamp"),
        "image_url": image_url_from_card(card),
        "art_crop_url": art_crop_url_from_card(card),
        "prices": card.get("prices", {}),
        "scryfall_uri": card.get("scryfall_uri", ""),
    }


def truncate_text(text: str, max_length: int) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= max_length:
        return compact
    return compact[: max_length - 3].rstrip() + "..."


def role_counts(cards: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for card in cards:
        counts[card["role"]] = counts.get(card["role"], 0) + 1
    return counts


def card_price_value(card: dict) -> float:
    prices = card.get("prices") or {}
    for key in ("usd", "usd_foil", "eur"):
        value = prices.get(key)
        if value:
            try:
                return float(value)
            except ValueError:
                continue
    return 0.0


def deck_price_summary(commander_card: dict, cards: list[dict]) -> dict:
    commander_price = card_price_value({"prices": commander_card.get("prices", {})})
    main_total = sum(card_price_value(card) for card in cards)
    total = commander_price + main_total
    return {
        "currency": "USD",
        "commander_estimate": round(commander_price, 2),
        "deck_estimate": round(total, 2),
        "source": "Scryfall prices",
    }


def section_counts(deck_sections: dict[str, list[str]]) -> dict[str, int]:
    return {section: len(cards) for section, cards in deck_sections.items() if section != "Commander"}


def first_name(commander_name: str) -> str:
    return commander_name.split(",", 1)[0].strip()


def build_content_angle(data: dict, cards: list[dict]) -> dict:
    commander_short = first_name(data["commander"]["name"])
    bracket = data["bracket"]
    playstyle = data["playstyle"]
    summary = data["summary"]
    role_count_map = role_counts(cards)

    if bracket == 2:
        power_line = "Value limpio y constante"
    elif bracket == 3:
        power_line = "Escala sin volverse torpe"
    elif bracket == 4:
        power_line = "Presion fuerte desde medio juego"
    else:
        power_line = "Plan explosivo y muy serio"

    primary_roles = sorted(role_count_map.items(), key=lambda item: (-item[1], item[0]))[:3]
    role_labels = [role for role, _ in primary_roles]
    promise = truncate_text(summary, 115)
    swipe_cta = "Desliza para ver las cartas clave"

    return {
        "hook": f"Por que {commander_short} funciona",
        "power_line": power_line,
        "promise": promise,
        "swipe_cta": swipe_cta,
        "commander_short": commander_short,
        "primary_roles": role_labels,
        "playstyle_short": truncate_text(playstyle, 70),
    }


def parse_report(path: Path) -> dict:
    text = read_text(path)
    title_match = re.search(r"^# (.+)$", text, re.MULTILINE)
    if not title_match:
        raise ValueError(f"No se encontro el titulo principal en {path}")

    raw_title = title_match.group(1).strip()
    summary = section_slice_any(text, ["Resumen", "Resumen del mazo"], ["Commander", "Datos del commander", "Plan de juego", "Decklist"])
    commander_block = section_slice_any(text, ["Commander", "Datos del commander"], ["Plan de juego", "Decklist", "Notas de construccion"])
    plan_block = section_slice(text, "Plan de juego", ["Decklist", "Notas de construccion"])
    decklist_block = section_slice(text, "Decklist", ["Notas de construccion", "Riesgos y puntos debiles", "Fuentes"])
    notes_block = section_slice(text, "Notas de construccion", ["Riesgos y puntos debiles", "Fuentes"])
    risks_block = section_slice(text, "Riesgos y puntos debiles", ["Fuentes"])

    meta_block = text.split("## Resumen", 1)[0]
    meta = parse_bullets(meta_block)
    commander_meta = parse_bullets(commander_block)
    title = meta.get("Commander") or commander_meta.get("Nombre") or re.sub(r"\s+-\s+Informe Commander$", "", raw_title).strip()
    gameplan = parse_plan_block(plan_block)
    deck_sections = normalize_deck_sections(parse_decklist(decklist_block))
    notes = [line[2:].strip() for line in notes_block.splitlines() if line.strip().startswith("- ")]
    risks = [line[2:].strip() for line in risks_block.splitlines() if line.strip().startswith("- ")]

    normalized_meta = {target: meta.get(source, "") for source, target in META_PREFIXES.items()}
    for target in META_ALIASES:
        normalized_meta[target] = normalized_meta.get(target) or meta_value(meta, target)
    if not normalized_meta.get("date") or not normalized_meta.get("time"):
        date_value, time_value = split_datetime(normalized_meta.get("datetime", ""))
        normalized_meta["date"] = normalized_meta.get("date") or date_value
        normalized_meta["time"] = normalized_meta.get("time") or time_value
    names_to_fetch = [title]
    for section_name, cards in deck_sections.items():
        if section_name == "Commander":
            continue
        names_to_fetch.extend(cards)
    card_lookup = fetch_scryfall_cards(list(dict.fromkeys(names_to_fetch)))
    commander_card = card_lookup[title]

    card_entries = []
    for section_name, cards in deck_sections.items():
        if section_name == "Commander":
            continue
        for card_name in cards:
            card_entries.append(build_card_entry(card_name, section_name, card_lookup[card_name]))

    result = {
        "report_id": path.stem,
        "source_markdown": str(path.resolve()),
        "generated_at": f"{normalized_meta['date']} {normalized_meta['time']}".strip(),
        "commander": {
            "name": title,
            "mana_cost": commander_meta.get("Coste de mana", commander_card.get("mana_cost", "")),
            "type_line": commander_meta.get("Tipo de carta", commander_card.get("type_line", "")),
            "oracle_text": commander_meta.get("Texto relevante", "").strip(),
            "color_identity": commander_card.get("color_identity", []),
            "image_url": image_url_from_card(commander_card),
            "art_crop_url": art_crop_url_from_card(commander_card),
            "scryfall_uri": commander_card.get("scryfall_uri", ""),
        },
        "summary": summary,
        "summary_short": truncate_text(summary, 160),
        "bracket": bracket_number(normalized_meta["bracket"]),
        "bracket_note": normalized_meta["bracket_note"],
        "playstyle": normalized_meta["playstyle"],
        "difficulty": normalized_meta["difficulty"],
        "price": {
            "value": normalized_meta["price_value"],
            "source_url": normalized_meta["price_url"],
        },
        "deck_price": deck_price_summary(commander_card, card_entries),
        "gameplan": {
            "early": gameplan.get("Early game", ""),
            "mid": gameplan.get("Mid game", ""),
            "late": gameplan.get("Late game", ""),
        },
        "deck_sections": deck_sections,
        "cards": card_entries,
        "stats": {
            "total_cards": len(card_entries) + 1,
            "section_counts": section_counts(deck_sections),
            "role_counts": role_counts(card_entries),
        },
        "build_notes": notes,
        "weaknesses": risks,
    }
    try:
        result["edhrec"] = audit_deck(title, [card["name"] for card in card_entries])
    except Exception as exc:
        result["edhrec"] = {
            "source": f"https://edhrec.com/commanders/{title.lower().replace(' ', '-')}",
            "error": str(exc),
            "quality_flags": ["EDHREC audit could not be completed; review recommendations manually before publishing."],
        }
    result["content_angle"] = build_content_angle(result, card_entries)
    return result


def export_report(path: Path) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    data = parse_report(path)
    output_path = OUTPUT_DIR / f"{path.stem}.json"
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_paths = sorted(REPORTS_DIR.glob("*.md"))
    if not report_paths:
        print("No se encontraron reportes Markdown en reports/.")
        return

    written = []
    for path in report_paths:
        written.append(export_report(path).name)

    print("JSON exportados:")
    for name in written:
        print(name)


if __name__ == "__main__":
    main()
