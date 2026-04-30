from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any
from urllib.parse import quote

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
QUEUE_DIR = ROOT / "publish_queue"
LEGAL_MEDIA_DIR = ROOT / "legal-site" / "media"


def _convert_to_jpg(source_path: Path, target_path: Path) -> Path:
    with Image.open(source_path) as image:
        converted = image.convert("RGB")
        converted.save(target_path, format="JPEG", quality=92, optimize=True)
    return target_path


def load_queue_entry(report_id: str) -> dict[str, Any]:
    queue_path = QUEUE_DIR / f"{report_id}.json"
    if not queue_path.exists():
        raise FileNotFoundError(f"Queue file not found: {queue_path}")
    return json.loads(queue_path.read_text(encoding="utf-8"))


def newest_queue_entry_path() -> Path | None:
    matches = sorted(path for path in QUEUE_DIR.glob("*.json") if path.name != ".gitkeep")
    return matches[-1] if matches else None


def resolve_report_id(report_id: str | None = None) -> str:
    if report_id:
        return report_id
    latest = newest_queue_entry_path()
    if latest is None:
        raise FileNotFoundError("No queue files found in publish_queue/.")
    return latest.stem


def stage_queue_media(report_id: str) -> list[Path]:
    data = load_queue_entry(report_id)
    target_dir = LEGAL_MEDIA_DIR / report_id
    target_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for source in data.get("images", []):
        source_path = Path(source)
        if not source_path.exists():
            raise FileNotFoundError(f"Image not found: {source_path}")
        if source_path.suffix.lower() == ".png":
            jpg_target = target_dir / f"{source_path.stem}.jpg"
            _convert_to_jpg(source_path, jpg_target)
            written.append(jpg_target)
        else:
            target_path = target_dir / source_path.name
            shutil.copy2(source_path, target_path)
            written.append(target_path)
    return written


def build_public_urls(report_id: str, media_base_url: str) -> list[str]:
    data = load_queue_entry(report_id)
    base = media_base_url.rstrip("/") + "/"
    target_dir = LEGAL_MEDIA_DIR / report_id
    urls = []
    for source in data.get("images", []):
        source_path = Path(source)
        preferred_jpg = target_dir / f"{source_path.stem}.jpg"
        if preferred_jpg.exists():
            name = preferred_jpg.name
        else:
            name = source_path.name
        urls.append(base + quote(report_id) + "/" + quote(name))
    return urls
