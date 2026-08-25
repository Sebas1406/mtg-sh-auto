# Daily Commander Builder Automation

Run the validated Commander Builder V2 pipeline for the project.

1. Select one card through Scryfall's live random endpoint using:
   `legal:commander is:commander game:paper -is:funny -is:digital`.
2. Resolve any required legal configuration, including Background, Partner with, or Doctor's companion.
3. Use bracket 3 unless `COMMANDER_TARGET_BRACKET` explicitly supplies another bracket.
4. Load current EDHREC recommendations as synergy evidence. EDHREC is not a legality source and must not be used as a simple top-card list.
5. Refresh the official Commander Game Changers policy from Wizards.
6. Build a canonical deck manifest containing exactly 100 cards:
   - one commander plus 99 mainboard cards, or two commanders plus 98;
   - paper-legal Commander cards only;
   - strict combined color identity;
   - singleton except for basic lands and explicit Oracle-text exceptions;
   - functional mana, ramp, card advantage, interaction, board wipes, protection, and win conditions;
   - a balanced mana curve and sufficient colored sources;
   - bracket-compliant Game Changers and play patterns.
7. Give every card roles, a package, a utility score, and a concise English explanation of why it belongs.
8. Validate the manifest. Any critical failure must stop the run before rendering, staging, pushing, or publishing.
9. Export:
   - `deck_manifests/<report_id>.json`
   - `deck_validation/<report_id>.json`
   - `moxfield_decklists_100/<report_id>.txt`
   - `reports/<report_id>.md`
   - `report_data/<report_id>.json`
   - six English TikTok slides in `tiktok_assets/<report_id>/`
   - `publish_queue/<report_id>.json`
10. Only a queue item with `validation_status: pass`, matching deck hashes, and `status: ready_for_publish` may continue to TikTok.

The public carousel shows a curated subset of useful cards. The complete 100-card list remains authoritative and available as the decklist export.
