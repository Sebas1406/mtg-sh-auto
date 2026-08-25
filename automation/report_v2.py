from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
REPORT_DATA_DIR = ROOT / "report_data"


def _difficulty(manifest: dict) -> str:
    archetype = (manifest.get("archetype") or {}).get("name")
    average_mv = float((manifest.get("stats") or {}).get("average_mana_value") or 0)
    if archetype in {"spellslinger", "graveyard", "artifacts"}:
        return "HIGH"
    if average_mv >= 3.8:
        return "MED-HIGH"
    return "MEDIUM"


def _curve(mainboard: list[dict]) -> list[dict]:
    buckets = Counter({"0–1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6+": 0})
    for card in mainboard:
        if "land" in (card.get("roles") or []):
            continue
        quantity = int(card.get("quantity") or 1)
        cmc = float(card.get("cmc") or 0)
        if cmc <= 1:
            key = "0–1"
        elif cmc >= 6:
            key = "6+"
        else:
            key = str(int(cmc))
        buckets[key] += quantity
    maximum = max(buckets.values()) or 1
    return [{"label": label, "count": count, "percent": round(count / maximum * 100)} for label, count in buckets.items()]


def _featured_groups(cards: list[dict]) -> list[dict]:
    ordered = sorted(cards, key=lambda card: (-float(card.get("utility_score") or 0), card["name"]))
    used: set[str] = set()

    def take(title: str, subtitle: str, roles: set[str], count: int = 4) -> dict:
        chosen = []
        for card in ordered:
            if card["name"] in used or "land" in (card.get("roles") or []):
                continue
            if roles and not roles.intersection(card.get("roles") or []):
                continue
            chosen.append(card)
            used.add(card["name"])
            if len(chosen) == count:
                break
        if len(chosen) < count:
            for card in ordered:
                if card["name"] in used or "land" in (card.get("roles") or []):
                    continue
                chosen.append(card)
                used.add(card["name"])
                if len(chosen) == count:
                    break
        prepared = []
        for card in chosen:
            featured = dict(card)
            card_roles = set(card.get("roles") or [])
            if title == "HOW IT WINS":
                featured["feature_role"] = "WINCON"
                featured["feature_reason"] = "Converts the deck's established engine into a concrete way to end the game."
            elif title == "ANSWERS & PROTECTION":
                if "protection" in card_roles:
                    featured["feature_role"] = "PROTECT"
                    featured["feature_reason"] = "Keeps the commander or engine intact through the interaction that matters."
                elif "board_wipe" in card_roles:
                    featured["feature_role"] = "BOARD WIPE"
                    featured["feature_reason"] = "Resets an opposing board when spot interaction is no longer enough."
                else:
                    featured["feature_role"] = "ANSWER"
                    featured["feature_reason"] = "Answers a relevant threat without abandoning the deck's main plan."
            elif title == "MANA & CARDS":
                if "ramp" in card_roles:
                    featured["feature_role"] = "RAMP"
                    featured["feature_reason"] = "Develops mana so the commander and engine pieces arrive on schedule."
                else:
                    featured["feature_role"] = "DRAW"
                    featured["feature_reason"] = "Keeps cards flowing after the first wave of resources is spent."
            else:
                featured["feature_role"] = "ENGINE"
                featured["feature_reason"] = card.get("why_in_deck") or "Makes the commander's plan repeatable."
            prepared.append(featured)
        return {"title": title, "subtitle": subtitle, "cards": prepared}

    # Reserve scarce closing cards first so another package cannot consume them.
    winning = take("HOW IT WINS", "Turn the established engine into a real closing line", {"wincon"})
    answers = take("ANSWERS & PROTECTION", "Interact without giving up your own development", {"interaction", "board_wipe", "protection", "graveyard_hate"})
    mana = take("MANA & CARDS", "Set up early, then keep the engine supplied", {"ramp", "draw"})
    core = take("CORE ENGINE", "The cards that make the commander plan repeatable", {"synergy", "tokens", "counters", "recursion", "value"})
    return [core, mana, answers, winning]


def _gameplan(manifest: dict) -> dict:
    name = " + ".join(card["name"] for card in manifest.get("commanders") or [])
    archetype = (manifest.get("archetype") or {}).get("name", "value")
    return {
        "early": f"Develop mana and a low-cost support piece. Keep hands that can cast {name} on schedule without using every card to do it.",
        "mid": f"Resolve the commander with protection or immediate value available, then connect the deck's {archetype} packages instead of deploying cards at random.",
        "late": "Protect the strongest engine, force opponents to spend interaction inefficiently, and commit a listed win condition only when it can end the game or create an overwhelming lead.",
        "mulligan": "Prioritize three mana sources, one acceleration piece, and either card advantage or early interaction. Ship hands that only contain expensive payoffs.",
    }


def _weaknesses(manifest: dict) -> list[str]:
    stats = manifest.get("stats") or {}
    roles = stats.get("role_counts") or {}
    archetype = (manifest.get("archetype") or {}).get("name")
    weaknesses = []
    if archetype in {"tokens", "counters", "artifacts", "enchantments"}:
        weaknesses.append("Board resets can erase several turns of development; sequence protection before the largest commitment.")
    if int(roles.get("protection") or 0) <= 4:
        weaknesses.append("Protection is intentionally compact, so do not expose the commander before it can create value.")
    if float(stats.get("average_mana_value") or 0) >= 3.5:
        weaknesses.append("The curve is top-heavy enough that missing an early land drop will be costly; mulligan slow hands aggressively.")
    weaknesses.append("Graveyard, combo, and creature-heavy tables demand different interaction priorities; use the flex slots accordingly.")
    return weaknesses[:3]


def build_report_data(manifest: dict, validation: dict, decklist_path: Path) -> dict:
    commanders = manifest.get("commanders") or []
    mainboard = manifest.get("mainboard") or []
    stats = manifest.get("stats") or {}
    commander_name = " + ".join(card["name"] for card in commanders)
    primary = commanders[0]
    groups = _featured_groups(mainboard)
    gameplan = _gameplan(manifest)
    section_counts = stats.get("section_counts") or {}
    deck_sections: dict[str, list[str]] = {}
    for card in mainboard:
        deck_sections.setdefault(card["section"], []).extend([card["name"]] * int(card.get("quantity") or 1))

    report = {
        "schema_version": 2,
        "report_id": manifest["report_id"],
        "generated_at": manifest.get("generated_at"),
        "deck_hash": manifest["deck_hash"],
        "language": "English",
        "commander": {
            **primary,
            "name": commander_name,
            "cards": commanders,
            "color_identity": manifest.get("color_identity") or [],
        },
        "summary": (manifest.get("archetype") or {}).get("promise", "Build repeatable value around the commander."),
        "summary_short": (manifest.get("archetype") or {}).get("promise", ""),
        "bracket": (manifest.get("target") or {}).get("bracket"),
        "bracket_note": "Bracket is enforced during deck construction and verified before publication.",
        "playstyle": f"{(manifest.get('archetype') or {}).get('name', 'value').title()} Commander",
        "difficulty": _difficulty(manifest),
        "deck_price": {
            "currency": "USD",
            "deck_estimate": stats.get("deck_price_usd"),
            "source": "Scryfall prices",
        },
        "gameplan": gameplan,
        "deck_sections": deck_sections,
        "cards": mainboard,
        "stats": {
            **stats,
            "section_counts": section_counts,
            "curve": _curve(mainboard),
        },
        "featured_groups": groups,
        "featured_cards": [card for group in groups for card in group["cards"]],
        "weaknesses": _weaknesses(manifest),
        "budget_swaps": manifest.get("budget_swaps") or [],
        "validation": validation,
        "validation_badge": "100-CARD VERIFIED" if validation.get("status") == "pass" else "BLOCKED",
        "full_decklist": {
            "local_path": decklist_path.resolve().relative_to(ROOT.resolve()).as_posix(),
            "cta": "Full verified 100-card list in the deck link.",
        },
        "content_angle": {
            "hook": f"Build {commander_name} with a plan",
            "power_line": (manifest.get("archetype") or {}).get("promise", ""),
            "promise": (manifest.get("archetype") or {}).get("promise", ""),
            "swipe_cta": "Swipe for the deck skeleton and the cards that matter.",
            "commander_short": primary["name"].split(",", 1)[0],
            "primary_roles": [role for role, _ in Counter(stats.get("role_counts") or {}).most_common(3)],
            "playstyle_short": f"{(manifest.get('archetype') or {}).get('name', 'value').title()} Commander",
        },
        "sources": manifest.get("sources") or {},
    }
    return report


def build_markdown(report: dict) -> str:
    commander = report["commander"]["name"]
    stats = report["stats"]
    roles = stats.get("role_counts") or {}
    lines = [
        f"# {commander}",
        "",
        f"- Generated: {report.get('generated_at')}",
        f"- Target bracket: {report.get('bracket')}",
        f"- Color identity: {'/'.join(report['commander'].get('color_identity') or ['Colorless'])}",
        f"- Validation: {report.get('validation_badge')}",
        f"- Deck hash: {report.get('deck_hash')}",
        "",
        "## Commander & Deck Promise",
        "",
        report.get("summary", ""),
        "",
        "## Deck Skeleton",
        "",
        f"- Total cards: {stats.get('total_cards')}",
        f"- Lands: {stats.get('land_count')}",
        f"- Ramp: {roles.get('ramp', 0)}",
        f"- Card advantage: {roles.get('draw', 0)}",
        f"- Interaction: {int(roles.get('interaction', 0)) + int(roles.get('board_wipe', 0))}",
        f"- Protection: {roles.get('protection', 0)}",
        f"- Win conditions: {roles.get('wincon', 0)}",
        f"- Average mana value: {stats.get('average_mana_value')}",
        "",
        "## Core Packages",
        "",
    ]
    for group in report.get("featured_groups") or []:
        lines.extend([f"### {group['title'].title()}", "", group["subtitle"], ""])
        for card in group["cards"]:
            lines.append(f"- **{card['name']}** — {card['why_in_deck']}")
        lines.append("")
    lines.extend(["## Mulligan & Turn Plan", "", f"- Opening hand: {report['gameplan']['mulligan']}", f"- Early game: {report['gameplan']['early']}", f"- Mid game: {report['gameplan']['mid']}", f"- Late game: {report['gameplan']['late']}", "", "## Weaknesses & Swaps", ""])
    lines.extend(f"- {item}" for item in report.get("weaknesses") or [])
    for swap in report.get("budget_swaps") or []:
        lines.append(f"- Budget swap: {swap['out']} → {swap['in']}. {swap['reason']}")
    lines.extend(["", "## Verified Full Decklist", ""])
    for section, names in report.get("deck_sections", {}).items():
        lines.extend([f"### {section}", ""])
        for name, quantity in Counter(names).items():
            lines.append(f"{quantity}x {name}")
        lines.append("")
    lines.extend(["## Sources", "", "- Official Commander rules: https://magic.wizards.com/en/formats/commander", "- Official banned list: https://magic.wizards.com/en/banned-restricted-list", "- Card data and legality: https://scryfall.com", "- Commander recommendations: https://edhrec.com", ""])
    return "\n".join(lines)


def write_report_v2(manifest: dict, validation: dict, decklist_path: Path) -> tuple[Path, Path, dict]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DATA_DIR.mkdir(parents=True, exist_ok=True)
    report = build_report_data(manifest, validation, decklist_path)
    markdown_path = REPORTS_DIR / f"{manifest['report_id']}.md"
    json_path = REPORT_DATA_DIR / f"{manifest['report_id']}.json"
    markdown_path.write_text(build_markdown(report), encoding="utf-8")
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return markdown_path, json_path, report
