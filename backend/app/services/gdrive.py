"""Google Drive uploads over the REST API.

Deliberately raw httpx rather than google-api-python-client: this needs a
token refresh and two file calls, which is not worth six transitive
dependencies in the image.

Auth is an OAuth **refresh token**, not a service account. A service account
on a personal Google account has its own Drive identity with zero storage
quota, so uploading into a folder you shared with it fails with "storage
quota exceeded" no matter how the folder is shared. Acting as the user avoids
that entirely, and the files end up genuinely owned by them.

Uploads are two requests — create metadata, then PATCH the bytes — rather
than one multipart/related request. Slightly chattier, but it avoids hand
-building a multipart body that httpx does not natively produce, which is the
usual source of silent 400s here.
"""
from __future__ import annotations

import json
import logging
import time

import httpx

from app import config
from app.services import settings

log = logging.getLogger("hodegos")

TOKEN_URL = "https://oauth2.googleapis.com/token"
FILES_URL = "https://www.googleapis.com/drive/v3/files"
UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files"
FOLDER_MIME = "application/vnd.google-apps.folder"
FOLDER_KEY = "gdrive_folder_id"

_token: dict = {"value": "", "expires_at": 0.0}


class DriveError(RuntimeError):
    pass


def configured() -> bool:
    return bool(
        config.GOOGLE_CLIENT_ID
        and config.GOOGLE_CLIENT_SECRET
        and config.GOOGLE_REFRESH_TOKEN
    )


def _access_token() -> str:
    """Exchange the refresh token, cached until just before it expires."""
    if _token["value"] and time.time() < _token["expires_at"]:
        return _token["value"]
    if not configured():
        raise DriveError(
            "Google Drive is not configured. Set GOOGLE_CLIENT_ID, "
            "GOOGLE_CLIENT_SECRET and GOOGLE_REFRESH_TOKEN — run "
            "scripts/google_auth.py to obtain them."
        )
    try:
        r = httpx.post(
            TOKEN_URL,
            data={
                "client_id": config.GOOGLE_CLIENT_ID,
                "client_secret": config.GOOGLE_CLIENT_SECRET,
                "refresh_token": config.GOOGLE_REFRESH_TOKEN,
                "grant_type": "refresh_token",
            },
            timeout=30,
        )
        r.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise DriveError(
            f"Token refresh failed ({exc.response.status_code}): "
            f"{exc.response.text[:300]}. If this says invalid_grant, the "
            "refresh token was revoked — re-run scripts/google_auth.py."
        ) from exc
    except httpx.HTTPError as exc:
        raise DriveError(f"Could not reach Google: {exc}") from exc

    payload = r.json()
    _token["value"] = payload["access_token"]
    # 60s of slack so a long job can't run past the expiry mid-upload.
    _token["expires_at"] = time.time() + payload.get("expires_in", 3600) - 60
    return _token["value"]


def _headers() -> dict:
    return {"Authorization": f"Bearer {_access_token()}"}


def folder_id() -> str:
    """The archive folder, created on first use and then remembered.

    Creating our own folder is what lets the drive.file scope be enough: the
    app can only ever touch files it made, so a bug here cannot reach the rest
    of the user's Drive. GDRIVE_FOLDER_ID overrides it for an existing folder.
    """
    if config.GDRIVE_FOLDER_ID:
        return config.GDRIVE_FOLDER_ID
    cached = settings.get(FOLDER_KEY)
    if cached:
        return cached
    r = httpx.post(
        FILES_URL,
        headers=_headers(),
        json={"name": config.GDRIVE_FOLDER_NAME, "mimeType": FOLDER_MIME},
        params={"fields": "id"},
        timeout=30,
    )
    if r.status_code >= 300:
        raise DriveError(f"Could not create the Drive folder: {r.text[:300]}")
    new_id = r.json()["id"]
    settings.set(FOLDER_KEY, new_id)
    log.warning("Created Drive folder %r (%s)", config.GDRIVE_FOLDER_NAME, new_id)
    return new_id


def _create(name: str, parent: str, mime: str) -> str:
    r = httpx.post(
        FILES_URL,
        headers=_headers(),
        json={"name": name, "parents": [parent], "mimeType": mime},
        params={"fields": "id"},
        timeout=30,
    )
    if r.status_code >= 300:
        raise DriveError(f"Create failed for {name}: {r.text[:300]}")
    return r.json()["id"]


def _upload_bytes(drive_id: str, data: bytes, mime: str) -> None:
    r = httpx.patch(
        f"{UPLOAD_URL}/{drive_id}",
        headers={**_headers(), "Content-Type": mime},
        params={"uploadType": "media"},
        content=data,
        timeout=120,
    )
    if r.status_code >= 300:
        raise DriveError(f"Upload failed for {drive_id}: {r.text[:300]}")


def upsert(
    name: str,
    data: bytes,
    mime: str = "text/markdown",
    drive_id: str | None = None,
) -> str:
    """Write `data` to Drive, replacing `drive_id` in place when given.

    Updating in place is what keeps an hourly job from accumulating 500 copies
    of the same journal entry as it gains a summary and gets edited.
    """
    parent = folder_id()
    if drive_id:
        try:
            _upload_bytes(drive_id, data, mime)
            return drive_id
        except DriveError as exc:
            # The file was deleted in Drive, or its id went stale. Fall through
            # and make a new one rather than failing the whole run.
            log.warning("Re-creating %s after update failed: %s", name, exc)
    new_id = _create(name, parent, mime)
    _upload_bytes(new_id, data, mime)
    return new_id


def folder_link() -> str | None:
    try:
        return f"https://drive.google.com/drive/folders/{folder_id()}"
    except DriveError:
        return None
