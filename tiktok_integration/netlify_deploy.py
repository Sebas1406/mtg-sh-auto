from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Any

import requests


NETLIFY_API = "https://api.netlify.com/api/v1"


class NetlifyDeployError(Exception):
    pass


def build_site_zip(source_dir: Path) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source_dir.rglob("*")):
            if path.is_dir():
                continue
            archive.write(path, arcname=path.relative_to(source_dir).as_posix())
    return buffer.getvalue()


def create_deploy(*, auth_token: str, site_id: str, source_dir: Path, production: bool = True) -> dict[str, Any]:
    if not auth_token:
        raise NetlifyDeployError("Missing NETLIFY_AUTH_TOKEN")
    if not site_id:
        raise NetlifyDeployError("Missing NETLIFY_SITE_ID")

    zip_bytes = build_site_zip(source_dir)
    response = requests.post(
        f"{NETLIFY_API}/sites/{site_id}/deploys",
        params={"production": str(production).lower()},
        headers={
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/zip",
        },
        data=zip_bytes,
        timeout=120,
    )
    response.raise_for_status()
    return response.json()


def get_deploy(*, auth_token: str, deploy_id: str) -> dict[str, Any]:
    response = requests.get(
        f"{NETLIFY_API}/deploys/{deploy_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()
