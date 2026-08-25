from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automation.commander_deck_engine import (
    PRIMARY_ROLE_CAPS,
    ROLE_MINIMUMS,
    _deck_hash,
    combined_color_identity,
    image_url,
    oracle_text,
    type_line,
)
from automation.commander_policy import maximum_game_changers


VALIDATION_DIR = ROOT / "deck_validation"


def _add_gate(gates: list[dict], name: str, passed: bool, detail: str, severity: str = "critical") -> None:
    gates.append({"name": name, "status": "pass" if passed else "fail", "severity": severity, "detail": detail})


def _commander_eligible(card: dict) -> bool:
    line = type_line(card)
    text = oracle_text(card).lower()
    return (
        ("Legendary" in line and ("Creature" in line or "Artifact" in line))
        or "can be your commander" in text
        or "Background" in line
    )


def _valid_pair(commanders: list[dict]) -> bool:
    if len(commanders) == 1:
        return "Background" not in type_line(commanders[0])
    first, second = commanders
    texts = [oracle_text(first).lower(), oracle_text(second).lower()]
    lines = [type_line(first), type_line(second)]
    if ("choose a background" in texts[0] and "Background" in lines[1]) or (
        "choose a background" in texts[1] and "Background" in lines[0]
    ):
        return True
    if ("doctor's companion" in texts[0] and "Doctor" in lines[1]) or (
        "doctor's companion" in texts[1] and "Doctor" in lines[0]
    ):
        return True
    if all("friends forever" in text for text in texts):
        return True
    if all(re.search(r"\bpartner\b", text) for text in texts):
        return True
    names = [first.get("name", "").lower(), second.get("name", "").lower()]
    if names[1] in texts[0] and "partner with" in texts[0]:
        return True
    if names[0] in texts[1] and "partner with" in texts[1]:
        return True
    return False


def _allows_multiple(card: dict, quantity: int) -> bool:
    if "Basic Land" in type_line(card):
        return True
    text = oracle_text(card).lower()
    if "a deck can have any number of cards named" in text:
        return True
    match = re.search(r"a deck can have up to (\w+) cards named", text)
    if not match:
        return False
    words = {
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
        "eleven": 11,
        "twelve": 12,
    }
    maximum = words.get(match.group(1))
    return maximum is not None and quantity <= maximum


def _mana_sources(mainboard: list[dict], identity: list[str]) -> dict[str, int]:
    sources = Counter({color: 0 for color in identity})
    basic_type_by_color = {"W": "Plains", "U": "Island", "B": "Swamp", "R": "Mountain", "G": "Forest"}
    for card in mainboard:
        if "Land" not in type_line(card):
            continue
        quantity = int(card.get("quantity") or 1)
        line = type_line(card)
        text = oracle_text(card)
        universal = "any color" in text.lower() or "commander's color identity" in text.lower()
        for color in identity:
            if universal or basic_type_by_color[color] in line or "{" + color + "}" in text:
                sources[color] += quantity
    return dict(sources)


def _minimum_sources(color_count: int) -> int:
    return {0: 0, 1: 24, 2: 14, 3: 10, 4: 8, 5: 8}.get(color_count, 8)


def validate_manifest(manifest: dict, verify_live_data: bool = True) -> dict:
    gates: list[dict] = []
    commanders = list(manifest.get("commanders") or [])
    mainboard = list(manifest.get("mainboard") or [])
    all_cards = commanders + mainboard
    identity = combined_color_identity(commanders)

    _add_gate(gates, "commander_count", len(commanders) in {1, 2}, f"Found {len(commanders)} commander card(s).")
    eligible = bool(commanders) and all(_commander_eligible(card) for card in commanders)
    _add_gate(gates, "commander_eligibility", eligible, "Every command-zone card must be eligible as a commander.")
    pair_valid = len(commanders) in {1, 2} and _valid_pair(commanders)
    _add_gate(gates, "commander_configuration", pair_valid, "The single or paired commander configuration must be rules-valid.")

    total_cards = sum(int(card.get("quantity") or 1) for card in all_cards)
    expected_mainboard = 100 - len(commanders)
    mainboard_total = sum(int(card.get("quantity") or 1) for card in mainboard)
    _add_gate(gates, "exactly_100_cards", total_cards == 100, f"Deck contains {total_cards} cards including commander(s).")
    _add_gate(gates, "mainboard_size", mainboard_total == expected_mainboard, f"Mainboard contains {mainboard_total}; expected {expected_mainboard}.")

    duplicate_errors = []
    for card in mainboard:
        quantity = int(card.get("quantity") or 1)
        if quantity > 1 and not _allows_multiple(card, quantity):
            duplicate_errors.append(f"{quantity}x {card.get('name')}")
    names = [card.get("name", "").casefold() for card in mainboard]
    repeated_rows = [name for name, count in Counter(names).items() if name and count > 1]
    duplicate_errors.extend(repeated_rows)
    _add_gate(gates, "singleton", not duplicate_errors, "No illegal duplicates." if not duplicate_errors else "; ".join(duplicate_errors))

    legality_errors = []
    identity_errors = []
    integrity_errors = []
    seen_ids = set()
    for card in all_cards:
        name = card.get("name") or "<unnamed>"
        if (card.get("legalities") or {}).get("commander") != "legal":
            legality_errors.append(f"{name}: Commander legality is not legal")
        if "paper" not in (card.get("games") or []):
            legality_errors.append(f"{name}: not available for paper play")
        if card.get("security_stamp") == "acorn":
            legality_errors.append(f"{name}: acorn card")
        if not set(card.get("color_identity") or []).issubset(set(identity)):
            identity_errors.append(f"{name}: {card.get('color_identity')} outside {identity}")
        if not card.get("scryfall_id") or not card.get("oracle_id") or not card.get("image_url"):
            integrity_errors.append(f"{name}: missing Scryfall ID, Oracle ID, or image")
        if card.get("scryfall_id") in seen_ids and "Basic Land" not in type_line(card):
            integrity_errors.append(f"{name}: duplicate Scryfall ID")
        seen_ids.add(card.get("scryfall_id"))
    _add_gate(gates, "commander_legality", not legality_errors, "All cards are paper-legal in Commander." if not legality_errors else "; ".join(legality_errors[:12]))
    _add_gate(gates, "color_identity", not identity_errors, "Every card is inside the combined commander identity." if not identity_errors else "; ".join(identity_errors[:12]))

    if verify_live_data and all(card.get("name") for card in all_cards):
        try:
            from automation.export_report_data import fetch_scryfall_cards

            canonical = fetch_scryfall_cards(list(dict.fromkeys(card["name"] for card in all_cards)))
            for card in all_cards:
                live = canonical.get(card["name"])
                if not live:
                    integrity_errors.append(f"{card['name']}: live Scryfall lookup missing")
                    continue
                if live.get("name") != card.get("name"):
                    integrity_errors.append(f"{card['name']}: canonical name is {live.get('name')}")
                if live.get("oracle_id") != card.get("oracle_id"):
                    integrity_errors.append(f"{card['name']}: Oracle ID mismatch")
        except Exception as exc:
            integrity_errors.append(f"Live Scryfall integrity check failed: {exc}")
    _add_gate(gates, "data_integrity", not integrity_errors, "Names, IDs, Oracle records, and images match." if not integrity_errors else "; ".join(integrity_errors[:12]))

    stats = manifest.get("stats") or {}
    land_count = int(stats.get("land_count") or 0)
    _add_gate(gates, "functional_land_count", 33 <= land_count <= 40, f"Land count is {land_count}; accepted range is 33–40.")
    role_counts = stats.get("role_counts") or {}
    for role, minimum in ROLE_MINIMUMS.items():
        count = int(role_counts.get(role) or 0)
        _add_gate(gates, f"role_{role}", count >= minimum, f"{role}: {count}; minimum {minimum}.")
    primary_counts = stats.get("primary_role_counts") or {}
    over_cap = [
        f"{role}: {int(primary_counts.get(role) or 0)} > {maximum}"
        for role, maximum in PRIMARY_ROLE_CAPS.items()
        if int(primary_counts.get(role) or 0) > maximum
    ]
    _add_gate(gates, "functional_role_balance", not over_cap, "Dedicated role slots stay inside the builder profile." if not over_cap else "; ".join(over_cap))
    high_cmc = sum(
        int(card.get("quantity") or 1)
        for card in mainboard
        if "land" not in (card.get("roles") or []) and float(card.get("cmc") or 0) >= 6
    )
    _add_gate(gates, "high_cost_card_limit", high_cmc <= 8, f"Deck contains {high_cmc} nonland cards with mana value 6+; maximum is 8.")

    sources = _mana_sources(mainboard, identity)
    minimum_sources = _minimum_sources(len(identity))
    source_errors = [f"{color}: {sources.get(color, 0)} < {minimum_sources}" for color in identity if sources.get(color, 0) < minimum_sources]
    _add_gate(gates, "colored_mana_sources", not source_errors, f"Sources: {sources}." if not source_errors else "; ".join(source_errors))

    bracket = int((manifest.get("target") or {}).get("bracket") or 0)
    gc_count = int(stats.get("game_changer_count") or 0)
    maximum = maximum_game_changers(bracket) if bracket else -1
    gc_valid = maximum is None or (maximum >= 0 and gc_count <= maximum)
    _add_gate(gates, "bracket_game_changers", gc_valid, f"Bracket {bracket} contains {gc_count} Game Changer(s); maximum is {maximum if maximum is not None else 'unlimited'}.")
    blocked_patterns = []
    if bracket <= 3:
        for card in mainboard:
            text = oracle_text(card).lower()
            if any(token in text for token in ["destroy all lands", "exile all lands", "take an extra turn after this one"]):
                blocked_patterns.append(card["name"])
    _add_gate(gates, "bracket_play_patterns", not blocked_patterns, "No mass-land-denial or extra-turn cards detected." if not blocked_patterns else ", ".join(blocked_patterns))

    policy_kind = (((manifest.get("sources") or {}).get("game_changers") or {}).get("source_kind"))
    policy_current = policy_kind == "live_official"
    _add_gate(gates, "current_official_policy", policy_current, f"Game Changers policy source: {policy_kind}.")

    computed_hash = _deck_hash(commanders, mainboard)
    _add_gate(gates, "deck_hash", computed_hash == manifest.get("deck_hash"), "Manifest hash matches the canonical card list.")

    average_mv = float(stats.get("average_mana_value") or 0)
    _add_gate(gates, "mana_curve", average_mv <= 4.5, f"Average nonland mana value is {average_mv:.2f}.", severity="warning")

    critical_failures = [gate for gate in gates if gate["severity"] == "critical" and gate["status"] == "fail"]
    warnings = [gate for gate in gates if gate["severity"] == "warning" and gate["status"] == "fail"]
    return {
        "schema_version": 2,
        "report_id": manifest.get("report_id"),
        "deck_hash": manifest.get("deck_hash"),
        "validated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "pass" if not critical_failures else "fail",
        "critical_error_count": len(critical_failures),
        "warning_count": len(warnings),
        "mana_sources": sources,
        "gates": gates,
    }


def write_validation(validation: dict) -> Path:
    VALIDATION_DIR.mkdir(parents=True, exist_ok=True)
    path = VALIDATION_DIR / f"{validation['report_id']}.json"
    path.write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a canonical Commander deck manifest.")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--offline", action="store_true", help="Skip live Scryfall identity verification.")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    validation = validate_manifest(manifest, verify_live_data=not args.offline)
    path = write_validation(validation)
    print(json.dumps({"validation": str(path), "status": validation["status"]}, indent=2))
    if validation["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
