from __future__ import annotations

import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / ".cache" / "edhrec"
EDHREC_JSON_BASE = "https://json.edhrec.com/pages/commanders"
EDHREC_CACHE_TTL_HOURS = int(os.environ.get("EDHREC_CACHE_TTL_HOURS", "24"))

CORE_TAGS = {
    "highsynergycards",
    "topcards",
    "creatures",
    "instants",
    "sorceries",
    "utilityartifacts",
    "manaartifacts",
    "enchantments",
    "planeswalkers",
    "utilitylands",
}

RECENCY_TAGS = {"newcards"}
POWER_TAGS = {"gamechangers"}


@dataclass(frozen=True)
class EdhrecCard:
    name: str
    tag: str
    header: str
    synergy: float
    inclusion: int
    potential_decks: int

    @property
    def inclusion_rate(self) -> float:
        if self.potential_decks <= 0:
            return 0.0
        return self.inclusion / self.potential_decks

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "tag": self.tag,
            "header": self.header,
            "synergy": round(self.synergy, 4),
            "inclusion": self.inclusion,
            "potential_decks": self.potential_decks,
            "inclusion_rate": round(self.inclusion_rate, 4),
        }


def commander_slug(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_name = ascii_name.lower().replace("&", " and ")
    ascii_name = re.sub(r"[^a-z0-9]+", "-", ascii_name)
    return ascii_name.strip("-")


def fetch_commander_page(commander_name: str) -> dict:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    slug = commander_slug(commander_name)
    cache_path = CACHE_DIR / f"{slug}.json"
    cache_is_fresh = cache_path.exists() and time.time() - cache_path.stat().st_mtime <= EDHREC_CACHE_TTL_HOURS * 3600
    if cache_is_fresh:
        return json.loads(cache_path.read_text(encoding="utf-8"))

    url = f"{EDHREC_JSON_BASE}/{slug}.json"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "codex-mtg-agent/0.3",
            "Accept": "application/json;q=0.9,*/*;q=0.8",
        },
    )
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.load(response)
            cache_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            time.sleep(0.15)
            return data
        except urllib.error.HTTPError as exc:
            if exc.code not in {429, 500, 502, 503, 504} or attempt == 3:
                raise
            time.sleep(1.5 * (attempt + 1))

    raise RuntimeError(f"No se pudo consultar EDHREC para {commander_name}")


def extract_cards(page: dict) -> dict[str, EdhrecCard]:
    cardlists = page.get("container", {}).get("json_dict", {}).get("cardlists", [])
    cards: dict[str, EdhrecCard] = {}
    for cardlist in cardlists:
        tag = cardlist.get("tag", "")
        header = cardlist.get("header", tag)
        for card in cardlist.get("cardviews", []):
            name = card.get("name", "").strip()
            if not name:
                continue
            key = name.lower()
            candidate = EdhrecCard(
                name=name,
                tag=tag,
                header=header,
                synergy=float(card.get("synergy") or 0),
                inclusion=int(card.get("num_decks") or card.get("inclusion") or 0),
                potential_decks=int(card.get("potential_decks") or 0),
            )
            current = cards.get(key)
            if current is None or card_priority(candidate) > card_priority(current):
                cards[key] = candidate
    return cards


def card_priority(card: EdhrecCard) -> tuple[int, float, float, int]:
    tag_score = 2 if card.tag in CORE_TAGS else 1 if card.tag in POWER_TAGS else 0
    return (tag_score, card.synergy, card.inclusion_rate, card.inclusion)


def ranked_recommendations(cards: dict[str, EdhrecCard], limit: int = 30) -> list[dict]:
    core_cards = [card for card in cards.values() if card.tag in CORE_TAGS]
    ranked = sorted(core_cards, key=card_priority, reverse=True)
    return [card.as_dict() for card in ranked[:limit]]


def audit_deck(commander_name: str, deck_cards: list[str]) -> dict:
    page = fetch_commander_page(commander_name)
    edhrec_cards = extract_cards(page)
    deck_keys = {card.lower(): card for card in deck_cards}
    matched = [edhrec_cards[key] for key in deck_keys if key in edhrec_cards]
    core_matches = [card for card in matched if card.tag in CORE_TAGS]
    high_synergy_matches = [card for card in matched if card.tag == "highsynergycards"]
    game_changer_matches = [card for card in matched if card.tag in POWER_TAGS]
    new_card_matches = [card for card in matched if card.tag in RECENCY_TAGS]

    ranked = ranked_recommendations(edhrec_cards, limit=30)
    ranked_names = {card["name"].lower() for card in ranked}
    missing_ranked = [card for card in ranked if card["name"].lower() not in deck_keys][:12]

    total_nonlands = len([card for card in deck_cards if card.lower() not in {"plains", "island", "swamp", "mountain", "forest", "wastes"}])
    coverage = len(core_matches) / total_nonlands if total_nonlands else 0.0
    top30_coverage = len([card for card in deck_keys if card in ranked_names]) / 30.0
    avg_synergy = sum(card.synergy for card in core_matches) / len(core_matches) if core_matches else 0.0

    return {
        "source": f"https://edhrec.com/commanders/{commander_slug(commander_name)}",
        "json_source": f"{EDHREC_JSON_BASE}/{commander_slug(commander_name)}.json",
        "available_recommendations": len(edhrec_cards),
        "matched_recommendations": len(matched),
        "core_recommendation_coverage": round(coverage, 4),
        "top_30_coverage": round(top30_coverage, 4),
        "average_core_synergy": round(avg_synergy, 4),
        "high_synergy_cards_in_deck": [card.as_dict() for card in sorted(high_synergy_matches, key=card_priority, reverse=True)[:15]],
        "game_changers_in_deck": [card.as_dict() for card in sorted(game_changer_matches, key=card_priority, reverse=True)[:10]],
        "new_cards_in_deck": [card.as_dict() for card in sorted(new_card_matches, key=card_priority, reverse=True)[:8]],
        "missing_top_recommendations": missing_ranked,
        "quality_flags": quality_flags(coverage, top30_coverage, avg_synergy, missing_ranked),
    }


def quality_flags(coverage: float, top30_coverage: float, avg_synergy: float, missing_ranked: list[dict]) -> list[str]:
    flags: list[str] = []
    if coverage < 0.22:
        flags.append("EDHREC coverage is low; review whether the list is drifting away from the commander page.")
    if top30_coverage < 0.25:
        flags.append("Few top EDHREC recommendations are present; justify omissions or add more commander staples.")
    if avg_synergy < 0.08:
        flags.append("Average synergy is low; prioritize high-synergy cards over generic goodstuff.")
    if len(missing_ranked) >= 10 and top30_coverage < 0.25:
        flags.append("Many high-ranked EDHREC cards are missing; check theme, budget, and bracket before publishing.")
    return flags
