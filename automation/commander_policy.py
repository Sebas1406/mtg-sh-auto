from __future__ import annotations

import html
import json
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLICY_CACHE_DIR = ROOT / ".cache" / "commander_policy"
GAME_CHANGERS_CACHE = POLICY_CACHE_DIR / "game_changers.json"
OFFICIAL_COMMANDER_URL = "https://magic.wizards.com/en/formats/commander"
OFFICIAL_BANNED_URL = "https://magic.wizards.com/en/banned-restricted-list"
POLICY_TTL_HOURS = 24

# Last-known official list, used only when the live official page and a fresh cache
# are both unavailable. The validation artifact records which source was used.
FALLBACK_GAME_CHANGERS = {
    "Ad Nauseam",
    "Ancient Tomb",
    "Aura Shards",
    "Biorhythm",
    "Bolas's Citadel",
    "Braids, Cabal Minion",
    "Chrome Mox",
    "Coalition Victory",
    "Consecrated Sphinx",
    "Crop Rotation",
    "Cyclonic Rift",
    "Demonic Tutor",
    "Drannith Magistrate",
    "Enlightened Tutor",
    "Farewell",
    "Field of the Dead",
    "Fierce Guardianship",
    "Force of Will",
    "Gaea's Cradle",
    "Gamble",
    "Gifts Ungiven",
    "Glacial Chasm",
    "Grand Arbiter Augustin IV",
    "Grim Monolith",
    "Humility",
    "Imperial Seal",
    "Intuition",
    "Jeska's Will",
    "Lion's Eye Diamond",
    "Mana Vault",
    "Mishra's Workshop",
    "Mox Diamond",
    "Mystical Tutor",
    "Narset, Parter of Veils",
    "Natural Order",
    "Necropotence",
    "Notion Thief",
    "Opposition Agent",
    "Orcish Bowmasters",
    "Panoptic Mirror",
    "Rhystic Study",
    "Seedborn Muse",
    "Serra's Sanctum",
    "Smothering Tithe",
    "Survival of the Fittest",
    "Teferi's Protection",
    "Tergrid, God of Fright",
    "Thassa's Oracle",
    "The One Ring",
    "The Tabernacle at Pendrell Vale",
    "Trouble in Pairs",
    "Underworld Breach",
    "Vampiric Tutor",
    "Worldly Tutor",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _cache_is_fresh(path: Path) -> bool:
    if not path.exists():
        return False
    return time.time() - path.stat().st_mtime <= POLICY_TTL_HOURS * 3600


def _fetch_official_page() -> str:
    request = urllib.request.Request(
        OFFICIAL_COMMANDER_URL,
        headers={
            "User-Agent": "mtg-sh-auto/2.0 commander-policy",
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_game_changers(page_html: str) -> list[str]:
    blocks = re.findall(
        r'entryTitle:"Formats \| Commander Refresh \| Game Changer Wiki [^"]+".*?copy:"(.*?)"\}',
        page_html,
        flags=re.DOTALL,
    )
    cards: set[str] = set()
    for block in blocks:
        for encoded_name in re.findall(
            r"\\u003Cauto-card\\u003E(.*?)\\u003C\\u002Fauto-card\\u003E",
            block,
        ):
            decoded = encoded_name.replace("\\u002F", "/")
            decoded = bytes(decoded, "utf-8").decode("unicode_escape")
            cards.add(html.unescape(decoded).strip())
    if len(cards) < 40:
        raise ValueError(f"Official Commander page yielded only {len(cards)} Game Changers.")
    return sorted(cards)


def load_game_changers(force_refresh: bool = False) -> dict:
    POLICY_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if not force_refresh and _cache_is_fresh(GAME_CHANGERS_CACHE):
        cached = json.loads(GAME_CHANGERS_CACHE.read_text(encoding="utf-8"))
        if len(cached.get("cards", [])) >= 40:
            return cached

    try:
        cards = parse_game_changers(_fetch_official_page())
        payload = {
            "source": OFFICIAL_COMMANDER_URL,
            "source_kind": "live_official",
            "checked_at": _utc_now_iso(),
            "cards": cards,
        }
        GAME_CHANGERS_CACHE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload
    except (OSError, ValueError, urllib.error.URLError, urllib.error.HTTPError) as exc:
        if GAME_CHANGERS_CACHE.exists():
            cached = json.loads(GAME_CHANGERS_CACHE.read_text(encoding="utf-8"))
            if len(cached.get("cards", [])) >= 40:
                cached = dict(cached)
                cached["source_kind"] = "stale_official_cache"
                cached["refresh_error"] = str(exc)
                return cached
        return {
            "source": OFFICIAL_COMMANDER_URL,
            "source_kind": "embedded_fallback",
            "checked_at": _utc_now_iso(),
            "refresh_error": str(exc),
            "cards": sorted(FALLBACK_GAME_CHANGERS),
        }


def maximum_game_changers(bracket: int) -> int | None:
    if bracket in {1, 2}:
        return 0
    if bracket == 3:
        return 3
    if bracket in {4, 5}:
        return None
    raise ValueError(f"Unsupported Commander bracket: {bracket}")
