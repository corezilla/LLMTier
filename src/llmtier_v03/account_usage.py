from __future__ import annotations

import hashlib
import hmac
import json
import os
import ssl
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .errors import ApiError, require
from .store import Store
from .usage import now


MINIMAX_USAGE_URL = "https://www.minimaxi.com/v1/token_plan/remains"
VOLC_USAGE_HOST = "ark.cn-beijing.volcengineapi.com"
VOLC_USAGE_VERSION = "2024-01-01"
VOLC_REGION = "cn-beijing"
VOLC_SERVICE = "ark"


def _urlopen(request: urllib.request.Request, *, timeout: int):
    try:
        import certifi  # type: ignore[import-not-found]
        context = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        context = ssl.create_default_context()
    return urllib.request.urlopen(request, timeout=timeout, context=context)


def _secret(ref: str | None) -> str:
    if not ref:
        return ""
    if ref.startswith("env:"):
        return os.environ.get(ref[4:], "").strip()
    if ref.startswith("file:"):
        try:
            return Path(ref[5:]).read_text(encoding="utf-8").strip()
        except OSError:
            return ""
    return ""


def _float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _reset(value: Any, divisor: int = 1) -> str:
    try:
        stamp = float(value) / divisor
    except (TypeError, ValueError):
        return ""
    return datetime.fromtimestamp(stamp, UTC).astimezone().strftime("%Y-%m-%d %H:%M") if stamp > 0 else ""


def _window(name: str, percent: float | None, reset_at: str, used: float | None = None, quota: float | None = None) -> dict[str, Any]:
    return {"name": name, "used": used, "quota": quota, "remaining": quota - used if used is not None and quota is not None else None, "percent": percent, "reset_at": reset_at}


def _snapshot(provider: str, source: str, status: str, *, windows=None, error="") -> dict[str, Any]:
    values = windows or []
    primary = next((item for item in values if item.get("name") == "weekly"), values[0] if values else {})
    return {"provider": provider, "source": source, "status": status, "used": primary.get("used"), "quota": primary.get("quota"), "remaining": primary.get("remaining"), "percent": primary.get("percent"), "reset_at": primary.get("reset_at", ""), "window": primary.get("name", ""), "windows": values, "checked_at": now(), "error": error}


def _volc_signing_key(secret_key: str, date: str) -> bytes:
    key = hmac.new(secret_key.encode(), date.encode(), hashlib.sha256).digest()
    key = hmac.new(key, VOLC_REGION.encode(), hashlib.sha256).digest()
    key = hmac.new(key, VOLC_SERVICE.encode(), hashlib.sha256).digest()
    return hmac.new(key, b"request", hashlib.sha256).digest()


def _volc_request(access_key: str, secret_key: str) -> dict[str, Any]:
    body = b"{}"
    current = datetime.now(UTC)
    x_date, short_date = current.strftime("%Y%m%dT%H%M%SZ"), current.strftime("%Y%m%d")
    query = f"Action=GetCodingPlanUsage&Version={VOLC_USAGE_VERSION}"
    payload_hash = hashlib.sha256(body).hexdigest()
    signed_headers = "host;x-content-sha256;x-date"
    canonical_headers = f"host:{VOLC_USAGE_HOST}\nx-content-sha256:{payload_hash}\nx-date:{x_date}\n"
    canonical_request = "\n".join(["POST", "/", query, canonical_headers, signed_headers, payload_hash])
    scope = f"{short_date}/{VOLC_REGION}/{VOLC_SERVICE}/request"
    string_to_sign = "\n".join(["HMAC-SHA256", x_date, scope, hashlib.sha256(canonical_request.encode()).hexdigest()])
    signature = hmac.new(_volc_signing_key(secret_key, short_date), string_to_sign.encode(), hashlib.sha256).hexdigest()
    request = urllib.request.Request(f"https://{VOLC_USAGE_HOST}/?{query}", data=body, method="POST", headers={"Content-Type": "application/json; charset=UTF-8", "Host": VOLC_USAGE_HOST, "X-Date": x_date, "X-Content-Sha256": payload_hash, "Authorization": f"HMAC-SHA256 Credential={access_key}/{scope}, SignedHeaders={signed_headers}, Signature={signature}"})
    with _urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode())


class AccountUsageService:
    """Read provider-account quota only on an explicit operator refresh."""

    def __init__(self, store: Store):
        self.store = store

    def latest(self, provider_id: str) -> dict[str, Any]:
        if self.store.one("SELECT id FROM providers WHERE id=?", (provider_id,)) is None:
            raise ApiError(404, "not_found", "Provider not found")
        row = self.store.one("SELECT snapshot_json FROM provider_usage_snapshots WHERE provider_id=?", (provider_id,))
        if row:
            return json.loads(row["snapshot_json"])
        profile = self.store.one("SELECT usage_provider FROM provider_usage_profiles WHERE provider_id=?", (provider_id,))
        return _snapshot(profile["usage_provider"] if profile else "none", "store", "not_refreshed")

    def _minimax(self, provider, profile) -> dict[str, Any]:
        api_key = _secret(profile["usage_api_key_ref"]) or _secret(provider["secret_ref"])
        if not api_key:
            return _snapshot("minimax", "credentials_missing", "unavailable", error="minimax_usage_requires_api_key")
        request = urllib.request.Request(MINIMAX_USAGE_URL, method="GET", headers={"Authorization": f"Bearer {api_key}"})
        with _urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode())
        base = payload.get("base_resp") if isinstance(payload.get("base_resp"), dict) else {}
        if int(base.get("status_code") or 0) != 0:
            return _snapshot("minimax", "provider_api_error", "unavailable", error=str(base.get("status_msg") or "minimax_usage_failed")[:160])
        remains = [item for item in payload.get("model_remains", []) if isinstance(item, dict)]
        item = next((value for value in remains if str(value.get("model_name", "")).lower() == "general"), remains[0] if remains else None)
        if item is None:
            return _snapshot("minimax", "provider_api", "unavailable", error="minimax_usage_empty_result")
        def used_percent(value): return round(max(0.0, min(100.0, 100 - _float(value))), 1) if value is not None else None
        interval_quota, weekly_quota = item.get("current_interval_total_count"), item.get("current_weekly_total_count")
        windows = [
            _window("5hour", used_percent(item.get("current_interval_remaining_percent")), _reset(item.get("end_time"), 1000), _float(item.get("current_interval_usage_count")) if interval_quota else None, _float(interval_quota) if interval_quota else None),
            _window("weekly", used_percent(item.get("current_weekly_remaining_percent")), _reset(item.get("weekly_end_time"), 1000), _float(item.get("current_weekly_usage_count")) if weekly_quota else None, _float(weekly_quota) if weekly_quota else None),
        ]
        return _snapshot("minimax", "provider_api", "ok", windows=windows)

    def _volc(self, profile) -> dict[str, Any]:
        access_key, secret_key = _secret(profile["usage_access_key_ref"]), _secret(profile["usage_secret_key_ref"])
        if not access_key or not secret_key:
            return _snapshot("volc", "credentials_missing", "unavailable", error="volc_get_coding_plan_usage_requires_ak_sk")
        payload = _volc_request(access_key, secret_key)
        result = payload.get("Result") if isinstance(payload.get("Result"), dict) else {}
        items = result.get("QuotaUsage") if isinstance(result.get("QuotaUsage"), list) else []
        names = {"5h": "5hour", "5hour": "5hour", "session": "5hour", "week": "weekly", "weekly": "weekly", "month": "monthly", "monthly": "monthly"}
        windows = []
        for item in items:
            raw = str(item.get("Level") or "").strip().lower().replace("_", "")
            name = names.get(raw, raw)
            if name:
                windows.append(_window(name, round(_float(item.get("Percent")), 1), _reset(item.get("ResetTimestamp"))))
        return _snapshot("volc", "provider_api", "ok", windows=windows) if windows else _snapshot("volc", "provider_api", "unavailable", error="volc_get_coding_plan_usage_empty_result")

    def refresh(self, provider_id: str, confirm_external_call: bool) -> dict[str, Any]:
        require(confirm_external_call is True, 400, "confirmation_required", "Usage refresh requires explicit confirmation")
        provider = self.store.one("SELECT * FROM providers WHERE id=?", (provider_id,))
        profile = self.store.one("SELECT * FROM provider_usage_profiles WHERE provider_id=?", (provider_id,))
        if provider is None or profile is None:
            raise ApiError(404, "not_found", "Provider not found")
        usage_provider = profile["usage_provider"]
        try:
            if usage_provider == "minimax": snapshot = self._minimax(provider, profile)
            elif usage_provider == "volc": snapshot = self._volc(profile)
            elif usage_provider == "local": snapshot = _snapshot("local", "quota_config", "unlimited")
            else: snapshot = _snapshot(usage_provider, "unsupported", "unsupported", error="provider_usage_unsupported")
        except urllib.error.HTTPError as exc:
            snapshot = _snapshot(usage_provider, "provider_api_error", "unavailable", error=f"usage_http_{exc.code}")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            snapshot = _snapshot(usage_provider, "provider_api_error", "unavailable", error=f"{exc.__class__.__name__}:{str(exc)[:120]}")
        with self.store.transaction(True) as conn:
            conn.execute("INSERT INTO provider_usage_snapshots(provider_id,snapshot_json,checked_at) VALUES(?,?,?) ON CONFLICT(provider_id) DO UPDATE SET snapshot_json=excluded.snapshot_json,checked_at=excluded.checked_at", (provider_id, json.dumps(snapshot, separators=(",", ":")), snapshot["checked_at"]))
        return snapshot
