# Validated TikTok Content Pipeline

```text
Live random commander
        ↓
Legal commander configuration
        ↓
Canonical 100-card manifest
        ↓
Strict rules and deck-quality validation
        ↓
English builder report
        ↓
Six-slide warm tavern carousel
        ↓
Hash-locked publish queue
        ↓
Stage, verify, push, publish
```

## Critical artifacts

- `commander_selection_runs/<report_id>.json`: random-selection evidence.
- `deck_manifests/<report_id>.json`: complete authoritative deck.
- `deck_validation/<report_id>.json`: machine-readable gates and status.
- `reports/<report_id>.md`: full English builder report.
- `report_data/<report_id>.json`: renderer-ready Report V2 data.
- `moxfield_decklists_100/<report_id>.txt`: complete import-ready list.
- `tiktok_assets/<report_id>/`: six PNG slides.
- `publish_queue/<report_id>.json`: hash-locked publishing payload.

## Publishing contract

`verify_publish_bundle.py` blocks publication unless:

- validation is `pass` with zero critical errors;
- manifest total is exactly 100;
- manifest, validation, report, and queue have the same deck hash;
- the queue has exactly six rendered images;
- staging has exactly six public images;
- every featured card exists in the manifest;
- queue status is `ready_for_publish`.

`shadow_ready` bundles may be checked locally with `ALLOW_SHADOW_BUNDLE=1`, but they cannot be sent to TikTok.

## Daily entry point

```powershell
powershell -ExecutionPolicy Bypass -File automation/run_full_daily_publish.ps1
```

The Windows task `MTG SH Full Generate And Publish Daily` runs at 08:00 America/Lima.
