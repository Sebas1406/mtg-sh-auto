from __future__ import annotations

import hashlib
import json
import math
import re
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = ROOT / "deck_manifests"
DECKLIST_DIR = ROOT / "moxfield_decklists_100"
SCRYFALL_SEARCH_URL = "https://api.scryfall.com/cards/search"
USER_AGENT = "mtg-sh-auto/2.0 deck-engine"

COLOR_ORDER = "WUBRG"
BASIC_BY_COLOR = {
    "W": "Plains",
    "U": "Island",
    "B": "Swamp",
    "R": "Mountain",
    "G": "Forest",
}

ROLE_MINIMUMS = {
    "ramp": 10,
    "draw": 10,
    "interaction": 8,
    "board_wipe": 2,
    "protection": 3,
    "wincon": 4,
}

PRIMARY_ROLE_CAPS = {
    "ramp": 12,
    "draw": 11,
    "interaction": 10,
    "board_wipe": 3,
    "protection": 4,
    "wincon": 5,
    "tutor": 3,
    "recursion": 4,
    "graveyard_hate": 2,
}

ROLE_LABELS = {
    "ramp": "Ramp",
    "draw": "Card advantage",
    "interaction": "Interaction",
    "board_wipe": "Board wipe",
    "protection": "Protection",
    "wincon": "Win condition",
    "recursion": "Recursion",
    "tutor": "Tutor",
    "tokens": "Token engine",
    "counters": "Counter engine",
    "graveyard_hate": "Graveyard hate",
    "land": "Mana base",
    "synergy": "Commander synergy",
    "value": "Value engine",
}

ROLE_PACKAGES = {
    "ramp": "Mana development",
    "draw": "Card advantage",
    "interaction": "Answers",
    "board_wipe": "Reset buttons",
    "protection": "Protection",
    "wincon": "Closing package",
    "recursion": "Recovery",
    "tutor": "Consistency",
    "tokens": "Token engine",
    "counters": "Counter engine",
    "graveyard_hate": "Meta tools",
    "land": "Mana base",
    "synergy": "Core engine",
    "value": "Support engine",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def combined_color_identity(commanders: list[dict]) -> list[str]:
    colors = {color for commander in commanders for color in commander.get("color_identity") or []}
    return [color for color in COLOR_ORDER if color in colors]


def oracle_text(card: dict) -> str:
    text = card.get("oracle_text") or ""
    if not text and card.get("card_faces"):
        text = " // ".join(face.get("oracle_text", "") for face in card["card_faces"])
    return re.sub(r"\s+", " ", text).strip()


def type_line(card: dict) -> str:
    text = card.get("type_line") or ""
    if not text and card.get("card_faces"):
        text = " // ".join(face.get("type_line", "") for face in card["card_faces"])
    return text


def image_url(card: dict) -> str:
    if (card.get("image_uris") or {}).get("normal"):
        return card["image_uris"]["normal"]
    for face in card.get("card_faces") or []:
        if (face.get("image_uris") or {}).get("normal"):
            return face["image_uris"]["normal"]
    return ""


def art_crop_url(card: dict) -> str:
    if (card.get("image_uris") or {}).get("art_crop"):
        return card["image_uris"]["art_crop"]
    for face in card.get("card_faces") or []:
        if (face.get("image_uris") or {}).get("art_crop"):
            return face["image_uris"]["art_crop"]
    return image_url(card)


def card_section(card: dict) -> str:
    line = type_line(card)
    if "Land" in line:
        return "Lands"
    if "Creature" in line:
        return "Creatures"
    if "Artifact" in line:
        return "Artifacts"
    if "Enchantment" in line:
        return "Enchantments"
    if "Instant" in line:
        return "Instants"
    if "Sorcery" in line:
        return "Sorceries"
    if "Planeswalker" in line:
        return "Planeswalkers"
    return "Other"


def detect_archetype(commanders: list[dict]) -> dict:
    commander_text = " ".join(oracle_text(card) for card in commanders).lower()
    commander_types = " ".join(type_line(card) for card in commanders).lower()
    options = [
        ("tokens", ["create", "token"]),
        ("counters", ["counter"]),
        ("artifacts", ["artifact"]),
        ("enchantments", ["enchantment"]),
        ("spellslinger", ["instant", "sorcery", "cast"]),
        ("graveyard", ["graveyard"]),
        ("lands", ["land"]),
        ("combat", ["combat", "attacks", "combat damage"]),
    ]
    scores: dict[str, int] = {}
    for label, needles in options:
        scores[label] = sum(commander_text.count(needle) * 2 + commander_types.count(needle) for needle in needles)
    label = max(scores, key=scores.get) if any(scores.values()) else "value"
    promise_map = {
        "tokens": "Build a wide board, multiply token payoffs, and convert creature count into a decisive finish.",
        "counters": "Grow a resilient board through counters and turn incremental scaling into lethal pressure.",
        "artifacts": "Chain artifact synergies into mana, cards, and a compact finishing engine.",
        "enchantments": "Develop an enchantment engine that compounds value while protecting its key pieces.",
        "spellslinger": "Turn efficient spells into card flow, interaction, and a focused closing sequence.",
        "graveyard": "Treat the graveyard as a second hand and keep rebuilding through interaction.",
        "lands": "Use land development as the value engine and translate extra land drops into inevitability.",
        "combat": "Create favorable attacks, protect the board, and finish through concentrated combat pressure.",
        "value": "Build repeatable value around the commander and win after pulling ahead on resources.",
    }
    keywords = set(re.findall(r"[a-z]{5,}", commander_text))
    stop = {"whenever", "creature", "control", "target", "commander", "another", "cards", "card", "until", "would"}
    return {
        "name": label,
        "promise": promise_map[label],
        "keywords": sorted(keywords - stop),
    }


def classify_roles(card: dict, archetype: str = "value") -> list[str]:
    if "Land" in type_line(card):
        return ["land"]
    text = oracle_text(card).lower()
    name = (card.get("name") or "").lower()
    roles: set[str] = set()

    if any(token in text for token in ["{t}: add {", "add one mana", "add two mana", "additional {", "double the amount of each type of", "create a treasure token", "create two treasure tokens", "search your library for a basic land", "search your library for up to two land"]):
        roles.add("ramp")
    if any(token in text for token in ["draw a card", "draw two cards", "draw three cards", "draw x cards", "draws x cards", "draw cards equal", "exile the top card", "you may play the exiled", "you may play that card"]):
        roles.add("draw")
    if "search your library" in text and "basic land" not in text:
        roles.add("tutor")
    if any(token in text for token in ["destroy target", "exile target", "counter target", "return target nonland permanent", "return target permanent to its owner's hand", "return target creature to its owner's hand", "fight target", "deals damage to target", "damage to any target"]):
        roles.add("interaction")
    if any(token in text for token in ["destroy all", "exile all", "all creatures get -", "deals damage to each creature", "each player sacrifices all"]):
        roles.update({"interaction", "board_wipe"})
    if any(token in text for token in ["creatures you control gain indestructible", "permanents you control gain indestructible", "target creature gains indestructible", "target creature you control gains", "you and permanents you control gain hexproof", "phase out", "protection from everything", "regenerate each", "counter target spell that targets"]):
        roles.add("protection")
    if any(token in text for token in ["return target", "from your graveyard", "from a graveyard to the battlefield", "reanimate"]):
        roles.add("recursion")
    if "graveyard" in text and any(token in text for token in ["exile target card", "exile all cards", "players can't cast spells from graveyards"]):
        roles.add("graveyard_hate")
    if "create" in text and "token" in text:
        roles.add("tokens")
    if "+1/+1 counter" in text or "proliferate" in text:
        roles.add("counters")
    if any(token in text for token in ["you win the game", "each opponent loses", "loses x life", "extra combat phase", "double the power", "get +x/+x", "gain control of all creatures", "put five", "create five", "deals damage equal to its power to each opponent", "combat damage to a player, that player loses"]):
        roles.add("wincon")
    if name in {"sol ring", "arcane signet", "fellwar stone", "cultivate", "kodama's reach"}:
        roles.add("ramp")
    if not roles:
        roles.add("synergy" if archetype in text or "whenever" in text else "value")
    return sorted(roles, key=lambda role: list(ROLE_LABELS).index(role) if role in ROLE_LABELS else 99)


def primary_role(roles: list[str]) -> str:
    priority = ["board_wipe", "interaction", "protection", "ramp", "draw", "wincon", "tutor", "recursion", "tokens", "counters", "graveyard_hate", "synergy", "value", "land"]
    return next((role for role in priority if role in roles), roles[0] if roles else "value")


def edhrec_candidates(page: dict) -> dict[str, dict]:
    aggregated: dict[str, dict] = {}
    cardlists = page.get("container", {}).get("json_dict", {}).get("cardlists", [])
    for cardlist in cardlists:
        tag = cardlist.get("tag") or ""
        header = cardlist.get("header") or tag
        for view in cardlist.get("cardviews") or []:
            name = (view.get("name") or "").strip()
            if not name:
                continue
            key = name.casefold()
            item = aggregated.setdefault(
                key,
                {
                    "name": name,
                    "tags": set(),
                    "headers": set(),
                    "synergy": 0.0,
                    "inclusion": 0,
                    "potential_decks": 0,
                },
            )
            item["tags"].add(tag)
            item["headers"].add(header)
            item["synergy"] = max(item["synergy"], float(view.get("synergy") or 0))
            item["inclusion"] = max(item["inclusion"], int(view.get("num_decks") or view.get("inclusion") or 0))
            item["potential_decks"] = max(item["potential_decks"], int(view.get("potential_decks") or 0))
    for item in aggregated.values():
        item["tags"] = sorted(item["tags"])
        item["headers"] = sorted(item["headers"])
    return aggregated


def _identity_query(identity: list[str]) -> str:
    return "id=c" if not identity else f"id<={''.join(color.lower() for color in COLOR_ORDER if color in identity)}"


def fetch_scryfall_search(query: str, limit: int = 80, order: str = "edhrec") -> list[dict]:
    params = urllib.parse.urlencode({"q": query, "order": order, "unique": "cards"})
    request = urllib.request.Request(
        f"{SCRYFALL_SEARCH_URL}?{params}",
        headers={"User-Agent": USER_AGENT, "Accept": "application/json;q=0.9,*/*;q=0.8"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    time.sleep(0.12)
    return list(payload.get("data") or [])[:limit]


def _fallback_queries(identity: list[str]) -> dict[str, str]:
    base = f"legal:commander game:paper {_identity_query(identity)} -t:land -is:funny"
    return {
        "ramp": f'{base} (o:"add {{" OR o:"create a treasure token" OR o:"search your library for a basic land")',
        "draw": f'{base} (o:"draw a card" OR o:"draw two cards" OR o:"exile the top card")',
        "interaction": f'{base} (o:"destroy target" OR o:"exile target" OR o:"counter target")',
        "board_wipe": f'{base} (o:"destroy all" OR o:"exile all" OR o:"all creatures get -")',
        "protection": f'{base} (o:hexproof OR o:indestructible OR o:"phase out")',
        "wincon": f'{base} (o:"you win the game" OR o:"extra combat" OR o:"double the power" OR o:"+X/+X" OR o:"gain control of all creatures")',
        "general": base,
        "lands": f"legal:commander game:paper {_identity_query(identity)} t:land -is:funny",
    }


def legal_for_deck(card: dict, identity: list[str]) -> bool:
    return (
        (card.get("legalities") or {}).get("commander") == "legal"
        and "paper" in (card.get("games") or [])
        and card.get("security_stamp") != "acorn"
        and set(card.get("color_identity") or []).issubset(set(identity))
    )


def blocked_casual_pattern(card: dict, bracket: int) -> bool:
    if bracket > 3:
        return False
    text = oracle_text(card).lower()
    return any(token in text for token in ["destroy all lands", "exile all lands", "take an extra turn after this one"])


def utility_score(card: dict, edhrec: dict, archetype: dict) -> float:
    tags = set(edhrec.get("tags") or [])
    tag_score = 0
    if "highsynergycards" in tags:
        tag_score += 32
    if "topcards" in tags:
        tag_score += 20
    if tags.intersection({"creatures", "instants", "sorceries", "utilityartifacts", "manaartifacts", "enchantments", "planeswalkers", "utilitylands"}):
        tag_score += 10
    synergy = max(0.0, float(edhrec.get("synergy") or 0))
    potential = int(edhrec.get("potential_decks") or 0)
    inclusion = int(edhrec.get("inclusion") or 0)
    inclusion_rate = inclusion / potential if potential else 0.0
    popularity = min(10.0, math.log10(max(1, inclusion)) * 2.5)
    overlap = sum(1 for word in archetype.get("keywords", []) if word in oracle_text(card).lower())
    roles = classify_roles(card, archetype["name"])
    versatility = min(8, max(0, len(roles) - 1) * 3)
    return round(tag_score + min(28, synergy * 70) + min(18, inclusion_rate * 24) + popularity + min(10, overlap * 2) + versatility, 2)


def why_in_deck(card: dict, roles: list[str], archetype: dict) -> str:
    role = primary_role(roles)
    explanations = {
        "ramp": "Develops mana so the commander and engine pieces arrive on schedule.",
        "draw": "Keeps cards flowing after the first wave of resources is spent.",
        "interaction": "Answers a relevant permanent or spell without abandoning the main plan.",
        "board_wipe": "Resets an opposing board when spot interaction is no longer enough.",
        "protection": "Protects the commander or the board from the interaction that matters most.",
        "wincon": "Turns an established board or resource lead into a concrete way to end the game.",
        "recursion": "Recovers key engine pieces and makes the deck harder to exhaust.",
        "tutor": "Improves access to the exact engine or answer the current game requires.",
        "tokens": "Adds bodies that feed the deck's token and board-scaling payoffs.",
        "counters": "Advances the counter engine and raises the pressure of every permanent around it.",
        "graveyard_hate": "Stops graveyard decks without consuming a purely defensive slot.",
        "land": "Provides a legal mana source or utility effect for the deck's color identity.",
        "synergy": f"Directly reinforces the deck's {archetype['name']} engine.",
        "value": "Adds efficient, repeatable value while supporting the commander's plan.",
    }
    return explanations.get(role, explanations["value"])


def card_record(card: dict, edhrec: dict, archetype: dict, game_changers: set[str], quantity: int = 1) -> dict:
    roles = classify_roles(card, archetype["name"])
    role = primary_role(roles)
    price = (card.get("prices") or {}).get("usd") or (card.get("prices") or {}).get("usd_foil")
    return {
        "name": card.get("name", ""),
        "quantity": quantity,
        "scryfall_id": card.get("id", ""),
        "oracle_id": card.get("oracle_id", ""),
        "mana_cost": card.get("mana_cost", ""),
        "cmc": card.get("cmc", 0),
        "type_line": type_line(card),
        "oracle_text": oracle_text(card),
        "color_identity": card.get("color_identity") or [],
        "legalities": card.get("legalities") or {},
        "games": card.get("games") or [],
        "security_stamp": card.get("security_stamp"),
        "image_url": image_url(card),
        "art_crop_url": art_crop_url(card),
        "scryfall_uri": card.get("scryfall_uri", ""),
        "prices": card.get("prices") or {},
        "price_usd": float(price) if price else 0.0,
        "section": card_section(card),
        "roles": roles,
        "primary_role": role,
        "role": role,
        "package": ROLE_PACKAGES.get(role, "Support engine"),
        "why_in_deck": why_in_deck(card, roles, archetype),
        "utility_score": utility_score(card, edhrec, archetype),
        "is_game_changer": card.get("name") in game_changers,
        "edhrec": {
            "tags": edhrec.get("tags") or [],
            "headers": edhrec.get("headers") or [],
            "synergy": round(float(edhrec.get("synergy") or 0), 4),
            "inclusion": int(edhrec.get("inclusion") or 0),
            "potential_decks": int(edhrec.get("potential_decks") or 0),
        },
    }


def _land_target(commanders: list[dict]) -> int:
    highest_cmc = max(float(card.get("cmc") or 0) for card in commanders)
    if highest_cmc >= 6:
        return 37
    if highest_cmc <= 3:
        return 35
    return 36


def _colored_pips(cards: list[dict], identity: list[str]) -> Counter:
    pips: Counter = Counter({color: 0 for color in identity})
    for card in cards:
        cost = card.get("mana_cost") or ""
        for color in identity:
            pips[color] += cost.count("{" + color + "}")
    return pips


def _basic_mix(identity: list[str], count: int, selected_nonlands: list[dict]) -> list[str]:
    if count <= 0:
        return []
    if not identity:
        return ["Wastes"] * count
    pips = _colored_pips(selected_nonlands, identity)
    weights = {color: max(1, pips[color]) for color in identity}
    allocation = {color: 1 for color in identity}
    remaining = count - len(identity)
    if remaining < 0:
        return [BASIC_BY_COLOR[color] for color in identity[:count]]
    total_weight = sum(weights.values())
    raw = {color: remaining * weights[color] / total_weight for color in identity}
    for color in identity:
        allocation[color] += int(raw[color])
    assigned = sum(allocation.values())
    for color in sorted(identity, key=lambda value: raw[value] - int(raw[value]), reverse=True):
        if assigned >= count:
            break
        allocation[color] += 1
        assigned += 1
    basics: list[str] = []
    for color in identity:
        basics.extend([BASIC_BY_COLOR[color]] * allocation[color])
    return basics[:count]


def _deck_hash(commanders: list[dict], mainboard: list[dict]) -> str:
    lines = [f"C|{card['quantity']}|{card['name']}" for card in commanders]
    lines.extend(f"M|{card['quantity']}|{card['name']}" for card in mainboard)
    return hashlib.sha256("\n".join(sorted(lines)).encode("utf-8")).hexdigest()


def build_deck_manifest(
    report_id: str,
    commanders: list[dict],
    target_bracket: int,
    edhrec_page: dict,
    game_changer_policy: dict,
    selection_evidence: dict | None = None,
) -> dict:
    from automation.export_report_data import fetch_scryfall_card, fetch_scryfall_cards

    if not 1 <= len(commanders) <= 2:
        raise ValueError("Commander configuration must contain one or two cards.")
    identity = combined_color_identity(commanders)
    archetype = detect_archetype(commanders)
    edhrec_index = edhrec_candidates(edhrec_page)
    commander_names = {card.get("name", "").casefold() for card in commanders}
    names = [item["name"] for item in edhrec_index.values() if item["name"].casefold() not in commander_names]
    lookup = fetch_scryfall_cards(names[:420]) if names else {}
    candidates: dict[str, dict] = {}
    for requested_name, card in lookup.items():
        if legal_for_deck(card, identity) and not blocked_casual_pattern(card, target_bracket):
            candidates[card["name"].casefold()] = card

    game_changers = set(game_changer_policy.get("cards") or [])
    queries = _fallback_queries(identity)
    role_supply = Counter()
    for card in candidates.values():
        role_supply.update(classify_roles(card, archetype["name"]))
    needed_queries = [role for role, minimum in ROLE_MINIMUMS.items() if role_supply[role] < minimum + 2]
    if len(candidates) < 105:
        needed_queries.append("general")
    for role in dict.fromkeys(needed_queries):
        try:
            for card in fetch_scryfall_search(queries[role], limit=90):
                if legal_for_deck(card, identity) and not blocked_casual_pattern(card, target_bracket):
                    candidates.setdefault(card["name"].casefold(), card)
        except Exception:
            continue
    try:
        for card in fetch_scryfall_search(queries["lands"], limit=100):
            if legal_for_deck(card, identity):
                candidates.setdefault(card["name"].casefold(), card)
    except Exception:
        pass

    land_target = _land_target(commanders)
    mainboard_target = 100 - len(commanders)
    nonland_target = mainboard_target - land_target
    if len([card for card in candidates.values() if "Land" not in type_line(card)]) < nonland_target:
        raise RuntimeError(
            f"Not enough legal nonland candidates to build {report_id}: "
            f"need {nonland_target}, found {len(candidates)} total candidates."
        )

    metadata_for = lambda card: edhrec_index.get(card["name"].casefold(), {})
    scored: list[tuple[float, str, dict]] = []
    for card in candidates.values():
        if "Land" in type_line(card):
            continue
        scored.append((utility_score(card, metadata_for(card), archetype), card["name"], card))
    scored.sort(key=lambda item: (-item[0], item[1]))

    max_game_changers = {1: 0, 2: 0, 3: 3, 4: None, 5: None}[target_bracket]
    selected_nonlands: list[dict] = []
    selected_names: set[str] = set()
    selected_role_counts: Counter = Counter()
    selected_primary_counts: Counter = Counter()
    selected_gc = 0
    selected_high_cmc = 0

    def allowed(card: dict) -> bool:
        nonlocal selected_gc, selected_high_cmc
        if card["name"].casefold() in selected_names:
            return False
        if card["name"] in game_changers and max_game_changers is not None and selected_gc >= max_game_changers:
            return False
        if float(card.get("cmc") or 0) >= 6 and selected_high_cmc >= 8:
            return False
        roles = classify_roles(card, archetype["name"])
        role = primary_role(roles)
        cap = PRIMARY_ROLE_CAPS.get(role)
        if cap is not None and selected_primary_counts[role] >= cap:
            return False
        return True

    while len(selected_nonlands) < nonland_target:
        unmet = {role for role, minimum in ROLE_MINIMUMS.items() if selected_role_counts[role] < minimum}
        best: tuple[float, str, dict] | None = None
        best_rank = -1.0
        for score, name, card in scored:
            if not allowed(card):
                continue
            roles = classify_roles(card, archetype["name"])
            coverage = len(unmet.intersection(roles))
            rank = score + coverage * 120 if unmet else score
            if unmet and coverage == 0:
                rank -= 80
            if rank > best_rank:
                best = (score, name, card)
                best_rank = rank
        if best is None:
            break
        card = best[2]
        selected_nonlands.append(card)
        selected_names.add(card["name"].casefold())
        selected_roles = classify_roles(card, archetype["name"])
        selected_role_counts.update(selected_roles)
        selected_primary_counts[primary_role(selected_roles)] += 1
        if card["name"] in game_changers:
            selected_gc += 1
        if float(card.get("cmc") or 0) >= 6:
            selected_high_cmc += 1

    if len(selected_nonlands) != nonland_target:
        raise RuntimeError(f"Deck builder stopped at {len(selected_nonlands)} of {nonland_target} nonlands.")

    land_candidates = [card for card in candidates.values() if "Land" in type_line(card)]
    try:
        command_tower = fetch_scryfall_card("Command Tower")
        if identity and legal_for_deck(command_tower, identity):
            land_candidates.append(command_tower)
    except Exception:
        pass
    unique_lands: dict[str, dict] = {card["name"].casefold(): card for card in land_candidates}
    def land_quality(card: dict) -> tuple[int, float, str]:
        text = oracle_text(card).lower()
        line = type_line(card)
        universal = "any color" in text or "commander's color identity" in text
        coverage = sum(
            1
            for color, basic_type in {"W": "Plains", "U": "Island", "B": "Swamp", "R": "Mountain", "G": "Forest"}.items()
            if color in identity and (universal or basic_type in line or "{" + color.lower() + "}" in text or "{" + color + "}" in oracle_text(card))
        )
        untapped_bonus = 1 if "enters tapped" not in text else 0
        return (coverage * 10 + untapped_bonus * 2 + (4 if universal else 0), utility_score(card, metadata_for(card), archetype), card["name"])

    ranked_lands = sorted(
        unique_lands.values(),
        key=lambda card: (-land_quality(card)[0], -land_quality(card)[1], land_quality(card)[2]),
    )
    nonbasic_by_colors = {0: 14, 1: 10, 2: 14, 3: 18, 4: 18, 5: 18}
    nonbasic_limit = min(land_target, nonbasic_by_colors[len(identity)])
    selected_lands = [card for card in ranked_lands if "Basic Land" not in type_line(card)][:nonbasic_limit]
    basic_names = _basic_mix(identity, land_target - len(selected_lands), selected_nonlands)
    basic_lookup = fetch_scryfall_cards(sorted(set(basic_names))) if basic_names else {}

    mainboard_records = [
        card_record(card, metadata_for(card), archetype, game_changers)
        for card in selected_nonlands + selected_lands
    ]
    for basic_name, quantity in Counter(basic_names).items():
        basic_card = basic_lookup[basic_name]
        mainboard_records.append(card_record(basic_card, {}, archetype, game_changers, quantity=quantity))
    mainboard_records.sort(key=lambda item: (item["section"], item["name"]))

    commander_records = []
    for commander in commanders:
        record = card_record(commander, {}, archetype, game_changers)
        record["section"] = "Commanders"
        record["primary_role"] = "commander"
        record["role"] = "commander"
        record["roles"] = ["commander"]
        record["package"] = "Command zone"
        record["why_in_deck"] = "Defines the deck's color identity and primary engine."
        commander_records.append(record)

    selected_record_names = {card["name"].casefold() for card in mainboard_records}
    budget_swaps: list[dict] = []
    expensive_cards = sorted(
        [card for card in mainboard_records if card.get("price_usd", 0) >= 8 and "land" not in card.get("roles", [])],
        key=lambda item: (-item.get("price_usd", 0), item["name"]),
    )
    for original in expensive_cards:
        original_roles = set(original.get("roles") or [])
        replacement = None
        for _, _, candidate in scored:
            if candidate["name"].casefold() in selected_record_names:
                continue
            if candidate["name"] in game_changers and max_game_changers is not None:
                continue
            candidate_price_text = (candidate.get("prices") or {}).get("usd") or (candidate.get("prices") or {}).get("usd_foil")
            candidate_price = float(candidate_price_text) if candidate_price_text else 0.0
            if candidate_price <= 0 or candidate_price >= original.get("price_usd", 0) * 0.65:
                continue
            candidate_roles = set(classify_roles(candidate, archetype["name"]))
            if not original_roles.intersection(candidate_roles):
                continue
            replacement = card_record(candidate, metadata_for(candidate), archetype, game_changers)
            break
        if replacement:
            budget_swaps.append(
                {
                    "out": original["name"],
                    "out_price_usd": original["price_usd"],
                    "in": replacement["name"],
                    "in_price_usd": replacement["price_usd"],
                    "shared_roles": sorted(original_roles.intersection(replacement.get("roles") or [])),
                    "reason": f"Keeps the {original['package'].lower()} slot while reducing estimated cost.",
                }
            )
        if len(budget_swaps) >= 4:
            break

    manifest = {
        "schema_version": 2,
        "report_id": report_id,
        "generated_at": utc_now_iso(),
        "selection_evidence": selection_evidence or {},
        "target": {"format": "Commander", "bracket": target_bracket, "language": "English"},
        "sources": {
            "scryfall": "https://scryfall.com/docs/api",
            "edhrec": "https://edhrec.com",
            "commander_rules": "https://magic.wizards.com/en/formats/commander",
            "banned_list": "https://magic.wizards.com/en/banned-restricted-list",
            "game_changers": game_changer_policy,
        },
        "color_identity": identity,
        "archetype": archetype,
        "commanders": commander_records,
        "mainboard": mainboard_records,
        "budget_swaps": budget_swaps,
    }
    manifest["deck_hash"] = _deck_hash(commander_records, mainboard_records)
    manifest["stats"] = manifest_stats(manifest)
    return manifest


def manifest_stats(manifest: dict) -> dict:
    cards = manifest.get("mainboard") or []
    role_counts: Counter = Counter()
    primary_role_counts: Counter = Counter()
    section_counts: Counter = Counter()
    nonland_cmc = 0.0
    nonland_quantity = 0
    price = sum(float(card.get("price_usd") or 0) * int(card.get("quantity") or 1) for card in cards + (manifest.get("commanders") or []))
    for card in cards:
        quantity = int(card.get("quantity") or 1)
        section_counts[card.get("section", "Other")] += quantity
        for role in card.get("roles") or []:
            role_counts[role] += quantity
        primary_role_counts[card.get("primary_role") or "value"] += quantity
        if "land" not in (card.get("roles") or []):
            nonland_cmc += float(card.get("cmc") or 0) * quantity
            nonland_quantity += quantity
    return {
        "total_cards": sum(int(card.get("quantity") or 1) for card in cards + (manifest.get("commanders") or [])),
        "commander_cards": sum(int(card.get("quantity") or 1) for card in manifest.get("commanders") or []),
        "mainboard_cards": sum(int(card.get("quantity") or 1) for card in cards),
        "land_count": role_counts["land"],
        "average_mana_value": round(nonland_cmc / nonland_quantity, 2) if nonland_quantity else 0,
        "role_counts": dict(sorted(role_counts.items())),
        "primary_role_counts": dict(sorted(primary_role_counts.items())),
        "section_counts": dict(sorted(section_counts.items())),
        "game_changer_count": sum(int(card.get("quantity") or 1) for card in cards if card.get("is_game_changer")),
        "deck_price_usd": round(price, 2),
    }


def write_manifest(manifest: dict) -> Path:
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    path = MANIFEST_DIR / f"{manifest['report_id']}.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_moxfield_decklist(manifest: dict) -> Path:
    DECKLIST_DIR.mkdir(parents=True, exist_ok=True)
    path = DECKLIST_DIR / f"{manifest['report_id']}.txt"
    lines = ["Commander"]
    lines.extend(f"{card['quantity']} {card['name']}" for card in manifest.get("commanders") or [])
    lines.append("")
    lines.append("Mainboard")
    for card in sorted(manifest.get("mainboard") or [], key=lambda item: (item["section"], item["name"])):
        lines.append(f"{card['quantity']} {card['name']}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    manifest_path = DECKLIST_DIR / "manifest_v2.json"
    rows = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else []
    row = {
        "report_id": manifest["report_id"],
        "commander": " + ".join(card["name"] for card in manifest.get("commanders") or []),
        "commanders": [card["name"] for card in manifest.get("commanders") or []],
        "commander_count": len(manifest.get("commanders") or []),
        "mainboard_count": manifest["stats"]["mainboard_cards"],
        "total_cards": manifest["stats"]["total_cards"],
        "deck_hash": manifest["deck_hash"],
        "validation_status": "pending_external_import",
        "file": path.resolve().relative_to(ROOT.resolve()).as_posix(),
    }
    rows = [existing for existing in rows if existing.get("report_id") != manifest["report_id"]]
    rows.append(row)
    manifest_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
