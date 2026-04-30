from __future__ import annotations

import secrets

import requests
from flask import Flask, jsonify, make_response, redirect, render_template_string, request

from .config import load_settings
from .publish_helpers import build_public_urls, load_queue_entry, stage_queue_media
from .tiktok_api import TikTokAPI, TikTokAPIError
from .token_store import TokenStore
from .token_runtime import ensure_access_token, load_runtime_tokens


app = Flask(__name__)
settings = load_settings()
api = TikTokAPI(settings)
token_store = TokenStore(settings.token_store_path)


def split_caption(queue: dict) -> tuple[str, str]:
    caption = (queue.get("caption") or "").strip()
    if not caption:
        return ("MTG Auto Publisher", "")
    parts = [part.strip() for part in caption.splitlines() if part.strip()]
    if not parts:
        return ("MTG Auto Publisher", "")
    title = parts[0]
    description = "\n".join(parts[1:])
    return (title, description)


SUCCESS_PAGE = """
<!doctype html>
<html lang="en">
  <head><meta charset="utf-8"><title>TikTok Connected</title></head>
  <body style="font-family: Arial, sans-serif; padding: 32px;">
    <h1>TikTok authorization completed</h1>
    <p>You can close this tab and return to the app.</p>
    <pre>{{ payload }}</pre>
  </body>
</html>
"""


@app.get("/")
def home():
    return jsonify(
        {
            "app": "MTG Auto Publisher TikTok Integration",
            "routes": {
                "start_auth": "/auth/tiktok/start",
                "status": "/auth/tiktok/status",
                "stage_media": "/api/tiktok/stage-media/<report_id>",
                "creator_info": "/api/tiktok/creator-info",
                "publish_queue_post": "/api/tiktok/publish/<report_id>",
                "publish_status": "/api/tiktok/publish-status/<publish_id>",
            },
        }
    )


@app.get("/auth/tiktok/start")
def auth_start():
    state = secrets.token_urlsafe(24)
    response = make_response(redirect(api.build_authorize_url(state)))
    response.set_cookie("tiktok_oauth_state", state, max_age=600, httponly=True, samesite="Lax")
    return response


@app.get("/auth/tiktok/local-callback")
def auth_local_callback():
    error = request.args.get("error")
    if error:
        return jsonify({"ok": False, "error": error, "error_description": request.args.get("error_description")}), 400

    expected_state = request.cookies.get("tiktok_oauth_state")
    incoming_state = request.args.get("state")
    if not expected_state or expected_state != incoming_state:
        return jsonify({"ok": False, "error": "state_mismatch"}), 400

    code = request.args.get("code", "").strip()
    if not code:
        return jsonify({"ok": False, "error": "missing_code"}), 400

    token_response = api.exchange_code(code)
    token_store.save(token_store.with_expirations(token_response))
    rendered = render_template_string(SUCCESS_PAGE, payload=token_response)
    response = make_response(rendered)
    response.delete_cookie("tiktok_oauth_state")
    return response


@app.get("/auth/tiktok/status")
def auth_status():
    data = load_runtime_tokens(token_store)
    return jsonify(
        {
            "connected": bool(data.get("access_token")),
            "token_path": str(settings.token_store_path),
            "token_fields": sorted(data.keys()),
        }
    )


@app.post("/api/tiktok/refresh")
def refresh_token():
    try:
        _, merged = ensure_access_token(api, token_store)
    except RuntimeError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify({"ok": True, "saved_to": str(settings.token_store_path), "fields": sorted(merged.keys())})


@app.get("/api/tiktok/creator-info")
def creator_info():
    try:
        token, _ = ensure_access_token(api, token_store)
    except RuntimeError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify(api.creator_info(token))


@app.post("/api/tiktok/stage-media/<report_id>")
def stage_media(report_id: str):
    written = stage_queue_media(report_id)
    return jsonify(
        {
            "ok": True,
            "report_id": report_id,
            "written_files": [str(path) for path in written],
            "netlify_next_step": "Redeploy the legal-site folder to Netlify so these files become public.",
        }
    )


@app.get("/api/tiktok/public-urls/<report_id>")
def public_urls(report_id: str):
    urls = build_public_urls(report_id, settings.media_base_url)
    return jsonify({"ok": True, "report_id": report_id, "image_urls": urls})


@app.post("/api/tiktok/publish/<report_id>")
def publish_photo_post(report_id: str):
    try:
        access_token, _ = ensure_access_token(api, token_store)
    except RuntimeError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400

    queue = load_queue_entry(report_id)
    image_urls = build_public_urls(report_id, settings.media_base_url)
    privacy_level = request.args.get("privacy_level", "SELF_ONLY")
    requested_mode = request.args.get("mode", "auto").upper()
    title, description = split_caption(queue)

    def send(post_mode: str):
        return api.init_photo_post(
            access_token,
            image_urls=image_urls,
            title=title,
            description=description,
            privacy_level=privacy_level,
            post_mode=post_mode,
        )

    try:
        if requested_mode == "MEDIA_UPLOAD":
            response = send("MEDIA_UPLOAD")
            effective_mode = "MEDIA_UPLOAD"
        elif requested_mode == "DIRECT_POST":
            response = send("DIRECT_POST")
            effective_mode = "DIRECT_POST"
        else:
            try:
                response = send("DIRECT_POST")
                effective_mode = "DIRECT_POST"
            except requests.HTTPError as exc:
                cause = exc.__cause__
                if isinstance(cause, TikTokAPIError):
                    error_code = cause.error_payload.get("error", {}).get("code")
                    if error_code == "unaudited_client_can_only_post_to_private_accounts":
                        response = send("MEDIA_UPLOAD")
                        effective_mode = "MEDIA_UPLOAD"
                    else:
                        raise
                else:
                    raise
    except requests.HTTPError as exc:
        cause = exc.__cause__
        if isinstance(cause, TikTokAPIError):
            return (
                jsonify(
                    {
                        "ok": False,
                        "report_id": report_id,
                        "image_urls": image_urls,
                        "status_code": cause.status_code,
                        "tiktok_error": cause.error_payload,
                        "request_payload": cause.request_payload,
                        "requested_mode": requested_mode,
                    }
                ),
                cause.status_code,
            )
        raise
    return jsonify(
        {
            "ok": True,
            "report_id": report_id,
            "image_urls": image_urls,
            "post_mode_used": effective_mode,
            "publish_response": response,
        }
    )


@app.get("/api/tiktok/publish-status/<path:publish_id>")
def publish_status(publish_id: str):
    try:
        access_token, _ = ensure_access_token(api, token_store)
    except RuntimeError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    response = api.fetch_publish_status(access_token, publish_id)
    return jsonify({"ok": True, "publish_id": publish_id, "status_response": response})


def main() -> None:
    app.run(host=settings.flask_host, port=settings.flask_port, debug=True)


if __name__ == "__main__":
    main()
