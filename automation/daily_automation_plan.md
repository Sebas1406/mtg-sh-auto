# Daily Commander Automation Plan

- Schedule: every day at 08:00 America/Lima.
- Windows task: `MTG SH Full Generate And Publish Daily`.
- Entry point: `automation/run_full_daily_publish.ps1`.
- Default target: Commander bracket 3.

## Sequence

1. Select and resolve a legal commander configuration.
2. Refresh EDHREC, Scryfall, and official Game Changers data.
3. Build the canonical 100-card manifest.
4. Run strict Commander and deck-quality validation.
5. Stop immediately on any critical failure.
6. Write the English Report V2 and Moxfield-ready full list.
7. Render six vertical slides.
8. Create the hash-locked queue.
9. Stage public media.
10. Run the final bundle verifier.
11. Commit and push only a verified `ready_for_publish` bundle.
12. GitHub Pages and TikTok workflows handle external delivery.

The task must remain disabled while `automation/publish_mode.json` is `draft_only`.
