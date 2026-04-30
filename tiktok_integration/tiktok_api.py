from __future__ import annotations

from typing import Any

import requests

from .config import Settings


AUTHORIZE_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
CREATOR_INFO_URL = "https://open.tiktokapis.com/v2/post/publish/creator_info/query/"
PHOTO_POST_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/content/init/"
PUBLISH_STATUS_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"
REFRESH_GRANT = "refresh_token"
AUTH_CODE_GRANT = "authorization_code"


class TikTokAPI:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def build_authorize_url(self, state: str) -> str:
        params = {
            "client_key": self.settings.client_key,
            "scope": self.settings.scopes,
            "response_type": "code",
            "redirect_uri": self.settings.redirect_uri,
            "state": state,
        }
        request = requests.Request("GET", AUTHORIZE_URL, params=params).prepare()
        return request.url

    def exchange_code(self, code: str) -> dict[str, Any]:
        data = {
            "client_key": self.settings.client_key,
            "client_secret": self.settings.client_secret,
            "code": code,
            "grant_type": AUTH_CODE_GRANT,
            "redirect_uri": self.settings.redirect_uri,
        }
        response = requests.post(TOKEN_URL, data=data, timeout=30)
        response.raise_for_status()
        return response.json()

    def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        data = {
            "client_key": self.settings.client_key,
            "client_secret": self.settings.client_secret,
            "grant_type": REFRESH_GRANT,
            "refresh_token": refresh_token,
        }
        response = requests.post(TOKEN_URL, data=data, timeout=30)
        response.raise_for_status()
        return response.json()

    def creator_info(self, access_token: str) -> dict[str, Any]:
        response = requests.post(
            CREATOR_INFO_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
            json={},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def fetch_publish_status(self, access_token: str, publish_id: str) -> dict[str, Any]:
        response = requests.post(
            PUBLISH_STATUS_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
            json={"publish_id": publish_id},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def init_photo_post(
        self,
        access_token: str,
        *,
        image_urls: list[str],
        title: str,
        description: str | None = None,
        post_mode: str = "DIRECT_POST",
        privacy_level: str = "SELF_ONLY",
        disable_comment: bool = False,
        auto_add_music: bool = True,
        brand_content_toggle: bool = False,
        brand_organic_toggle: bool = False,
    ) -> dict[str, Any]:
        post_info: dict[str, Any] = {
            "title": title[:90],
        }
        if description:
            post_info["description"] = description[:4000]
        if post_mode == "DIRECT_POST":
            post_info.update(
                {
                    "privacy_level": privacy_level,
                    "disable_comment": disable_comment,
                    "auto_add_music": auto_add_music,
                    "brand_content_toggle": brand_content_toggle,
                    "brand_organic_toggle": brand_organic_toggle,
                }
            )

        payload = {
            "post_info": post_info,
            "source_info": {
                "source": "PULL_FROM_URL",
                "photo_images": image_urls,
            },
            "post_mode": post_mode,
            "media_type": "PHOTO",
        }
        response = requests.post(
            PHOTO_POST_INIT_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
            json=payload,
            timeout=30,
        )
        if not response.ok:
            error_payload: dict[str, Any]
            try:
                error_payload = response.json()
            except ValueError:
                error_payload = {"raw_text": response.text}
            raise requests.HTTPError(
                f"TikTok photo post init failed with status {response.status_code}",
                response=response,
            ) from TikTokAPIError(response.status_code, error_payload, payload)
        return response.json()


class TikTokAPIError(Exception):
    def __init__(self, status_code: int, error_payload: dict[str, Any], request_payload: dict[str, Any]) -> None:
        super().__init__(f"TikTok API error {status_code}")
        self.status_code = status_code
        self.error_payload = error_payload
        self.request_payload = request_payload
