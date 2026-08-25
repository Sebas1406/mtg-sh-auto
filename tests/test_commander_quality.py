from __future__ import annotations

import copy
import unittest

from automation.commander_deck_engine import _deck_hash, manifest_stats
from automation.export_report_data import card_matches_requested_name
from automation.validate_commander_deck import _valid_pair, validate_manifest


def fake_card(name: str, *, roles: list[str], color_identity: list[str] | None = None, type_line: str = "Artifact") -> dict:
    slug = name.lower().replace(" ", "-")
    return {
        "name": name,
        "quantity": 1,
        "scryfall_id": f"scryfall-{slug}",
        "oracle_id": f"oracle-{slug}",
        "mana_cost": "{1}{B}",
        "cmc": 2,
        "type_line": type_line,
        "oracle_text": "Useful test card.",
        "color_identity": ["B"] if color_identity is None else color_identity,
        "legalities": {"commander": "legal"},
        "games": ["paper"],
        "security_stamp": None,
        "image_url": f"https://img.example/{slug}.jpg",
        "roles": roles,
        "primary_role": roles[0],
        "role": roles[0],
        "section": "Artifacts",
        "is_game_changer": False,
        "price_usd": 1,
    }


def valid_manifest() -> dict:
    commander = fake_card("Test Commander", roles=["commander"], type_line="Legendary Creature — Wizard")
    commander["oracle_text"] = "Whenever you cast a spell, scry 1."
    commander["section"] = "Commanders"
    cards = []
    role_plan = (
        [["ramp"]] * 10
        + [["draw"]] * 10
        + [["interaction"]] * 8
        + [["interaction", "board_wipe"]] * 2
        + [["protection"]] * 3
        + [["wincon"]] * 4
        + [["value"]] * 27
    )
    for index, roles in enumerate(role_plan):
        cards.append(fake_card(f"Card {index:02d}", roles=roles))
    swamp = fake_card("Swamp", roles=["land"], color_identity=[], type_line="Basic Land — Swamp")
    swamp["quantity"] = 35
    swamp["oracle_text"] = "{T}: Add {B}."
    swamp["section"] = "Lands"
    cards.append(swamp)
    manifest = {
        "schema_version": 2,
        "report_id": "fixture",
        "target": {"bracket": 3},
        "sources": {"game_changers": {"source_kind": "live_official"}},
        "color_identity": ["B"],
        "commanders": [commander],
        "mainboard": cards,
    }
    manifest["deck_hash"] = _deck_hash(manifest["commanders"], manifest["mainboard"])
    manifest["stats"] = manifest_stats(manifest)
    return manifest


class CommanderValidationTests(unittest.TestCase):
    def test_valid_manifest_passes(self) -> None:
        result = validate_manifest(valid_manifest(), verify_live_data=False)
        self.assertEqual("pass", result["status"])
        self.assertEqual(0, result["critical_error_count"])

    def test_exact_card_count_blocks_99_cards(self) -> None:
        manifest = valid_manifest()
        manifest["mainboard"][-1]["quantity"] = 34
        manifest["stats"] = manifest_stats(manifest)
        manifest["deck_hash"] = _deck_hash(manifest["commanders"], manifest["mainboard"])
        result = validate_manifest(manifest, verify_live_data=False)
        failed = {gate["name"] for gate in result["gates"] if gate["status"] == "fail"}
        self.assertIn("exactly_100_cards", failed)

    def test_off_color_card_blocks_deck(self) -> None:
        manifest = valid_manifest()
        manifest["mainboard"][0]["color_identity"] = ["U"]
        result = validate_manifest(manifest, verify_live_data=False)
        failed = {gate["name"] for gate in result["gates"] if gate["status"] == "fail"}
        self.assertIn("color_identity", failed)

    def test_banned_card_blocks_deck(self) -> None:
        manifest = valid_manifest()
        manifest["mainboard"][0]["legalities"]["commander"] = "banned"
        result = validate_manifest(manifest, verify_live_data=False)
        failed = {gate["name"] for gate in result["gates"] if gate["status"] == "fail"}
        self.assertIn("commander_legality", failed)

    def test_nonbasic_duplicate_blocks_deck(self) -> None:
        manifest = valid_manifest()
        manifest["mainboard"][0]["quantity"] = 2
        manifest["mainboard"].pop(1)
        manifest["stats"] = manifest_stats(manifest)
        manifest["deck_hash"] = _deck_hash(manifest["commanders"], manifest["mainboard"])
        result = validate_manifest(manifest, verify_live_data=False)
        failed = {gate["name"] for gate in result["gates"] if gate["status"] == "fail"}
        self.assertIn("singleton", failed)

    def test_missing_card_identity_data_blocks_deck(self) -> None:
        manifest = valid_manifest()
        manifest["mainboard"][0]["scryfall_id"] = ""
        result = validate_manifest(manifest, verify_live_data=False)
        failed = {gate["name"] for gate in result["gates"] if gate["status"] == "fail"}
        self.assertIn("data_integrity", failed)

    def test_card_cache_name_mismatch_is_rejected(self) -> None:
        self.assertFalse(card_matches_requested_name("Boros Charm", {"name": "Thrilling Discovery"}))
        self.assertTrue(card_matches_requested_name("Boros Charm", {"name": "Boros Charm"}))

    def test_choose_a_background_pair_is_valid(self) -> None:
        leader = fake_card("Leader", roles=["commander"], type_line="Legendary Creature — Human")
        leader["oracle_text"] = "Choose a Background"
        background = fake_card("Quiet Study", roles=["commander"], type_line="Legendary Enchantment — Background")
        self.assertTrue(_valid_pair([leader, background]))

    def test_game_changer_limit_blocks_bracket_three(self) -> None:
        manifest = valid_manifest()
        for card in manifest["mainboard"][:4]:
            card["is_game_changer"] = True
        manifest["stats"] = manifest_stats(manifest)
        result = validate_manifest(manifest, verify_live_data=False)
        failed = {gate["name"] for gate in result["gates"] if gate["status"] == "fail"}
        self.assertIn("bracket_game_changers", failed)


if __name__ == "__main__":
    unittest.main()
