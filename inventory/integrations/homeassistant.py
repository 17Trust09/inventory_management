# Home Assistant Integration für Lagerdatenbank:
# - Zwei Betriebsarten:
#     * API-Modus (Token, /api/... Endpoints)  → HA_URL/HA_API_TOKEN nötig
#     * WEBHOOK-Modus (Cloudhook/HA-Webhook)   → HA_WEBHOOK_URL genügt
# - Robuster Health-Check (/api und /api/), Diagnose, Fallbacks
# - Frontend-Statusmeldungen auf Deutsch

from __future__ import annotations

import os
import time
import requests
from typing import Any, Dict, Optional, List, Tuple
from django.conf import settings
from django.urls import reverse
from requests.exceptions import SSLError

# ──────────────────────────────────────────────────────────────────────────────
# Konfiguration aus .env / settings
# ──────────────────────────────────────────────────────────────────────────────

# API-Modus
HA_URL = (getattr(settings, "HA_URL", None) or os.getenv("HA_URL", "http://homeassistant.local:8123")).rstrip("/")
HA_TOKEN = getattr(settings, "HA_API_TOKEN", None) or os.getenv("HA_API_TOKEN", "")

# WEBHOOK-Modus (wenn gesetzt, hat Vorrang)
HA_WEBHOOK_URL = os.getenv("HA_WEBHOOK_URL", "").strip()

# Deeplink-Basis (optional; leer = dynamisch aus Request)
BASE_URL = (getattr(settings, "INVENTORY_BASE_URL", None) or os.getenv("INVENTORY_BASE_URL", "")).rstrip("/")

# Timeouts/SSL
TIMEOUT = int(os.getenv("HA_TIMEOUT", "6"))
VERIFY_SSL = os.getenv("HA_VERIFY_SSL", "true").lower() == "true"

# Cache & Diagnose
_LAST_CHECK_TS: float = 0.0
_IS_AVAILABLE: Optional[bool] = None
_CACHE_SECONDS = 60

_LAST_URL: Optional[str] = None
_LAST_ERROR: Optional[str] = None
_LAST_TRIES: Optional[List[Tuple[str, str]]] = None  # [(url, "OK|401|404|EXC…")]

# ──────────────────────────────────────────────────────────────────────────────

def _headers() -> Dict[str, str]:
    return {"Authorization": f"Bearer {HA_TOKEN}", "Content-Type": "application/json"}

def _use_webhook() -> bool:
    return bool(HA_WEBHOOK_URL)

def _has_api_config() -> bool:
    return bool(HA_URL and HA_TOKEN)

def _remember(url: str, error: Optional[Exception] = None, response: Optional[requests.Response] = None, tries: Optional[List[Tuple[str,str]]] = None):
    global _LAST_URL, _LAST_ERROR, _LAST_TRIES
    _LAST_URL = url
    _LAST_TRIES = tries
    if error is not None:
        _LAST_ERROR = f"{type(error).__name__}: {error}"
    elif response is not None and not response.ok:
        txt = (response.text or "")[:200].replace("\n", " ")
        _LAST_ERROR = f"HTTP {response.status_code}: {txt or 'HTTP error'}"
    else:
        _LAST_ERROR = None

def _health_ok_status(code: int) -> bool:
    # Für Erreichbarkeit: 200 oder 401 (Unauthorized = API lebt)
    return code in (200, 401)

def check_available(force: bool = False) -> bool:
    """
    Prüft Erreichbarkeit:
      - WEBHOOK-Modus: true (wir können senden; kein Ping möglich)
      - API-Modus: GET auf /api und /api/ (200/401 -> erreichbar)
    Ergebnis 60s gecacht.
    """
    global _LAST_CHECK_TS, _IS_AVAILABLE
    now = time.monotonic()
    if not force and _IS_AVAILABLE is not None and (now - _LAST_CHECK_TS) < _CACHE_SECONDS:
        return bool(_IS_AVAILABLE)

    if _use_webhook() and not _has_api_config():
        _IS_AVAILABLE = True
        _LAST_CHECK_TS = now
        _remember(HA_WEBHOOK_URL)
        return True

    if not _has_api_config():
        _IS_AVAILABLE = False
        _LAST_CHECK_TS = now
        _remember("N/A (HA_URL/HA_TOKEN fehlen)")
        return False

    tries: List[Tuple[str, str]] = []
    for path in ("/api", "/api/"):
        url = f"{HA_URL}{path}"
        try:
            r = requests.get(url, headers=_headers(), timeout=TIMEOUT, verify=VERIFY_SSL)
            tries.append((url, str(r.status_code)))
            if _health_ok_status(r.status_code):
                _IS_AVAILABLE = True
                _LAST_CHECK_TS = now
                _remember(url, response=r, tries=tries)
                return True
        except Exception as e:
            tries.append((url, f"EXC:{type(e).__name__}"))

    _IS_AVAILABLE = False
    _LAST_CHECK_TS = now
    try:
        _remember(url, tries=tries)  # type: ignore[name-defined]
    except Exception:
        _remember("N/A", tries=tries)
    return False

def get_status_tuple() -> tuple[bool, str]:
    """
    Liefert (available, message) für den UI-Badge.
    """
    if _use_webhook() and not _has_api_config():
        return True, "Feedbacks werden online per Webhook übertragen"
    if not _has_api_config():
        return False, "Keine HA-Konfiguration (.env) – Token/URL fehlen"
    if check_available():
        return True, "Feedbacks werden online übertragen"
    return False, "Keine Internet-Verbindung oder Server nicht erreichbar – Feedbacks werden nicht übertragen"

def get_diagnostics() -> Dict[str, Any]:
    return {
        "mode": "webhook" if _use_webhook() else "api",
        "ha_url": HA_URL,
        "webhook_url_set": bool(HA_WEBHOOK_URL),
        "verify_ssl": VERIFY_SSL,
        "timeout": TIMEOUT,
        "last_url": _LAST_URL,
        "last_error": _LAST_ERROR,
        "tries": _LAST_TRIES,
    }

# ──────────────────────────────────────────────────────────────────────────────
# Senden
# ──────────────────────────────────────────────────────────────────────────────

def _build_absolute_url(path: str) -> str:
    if BASE_URL:
        return f"{BASE_URL}{path}"
    try:
        from ..middleware import get_current_request
        req = get_current_request()
        if req is not None:
            return req.build_absolute_uri(path)
    except Exception:
        pass
    return path

def _feedback_payload(feedback) -> Dict[str, Any]:
    try:
        detail_path = reverse('feedback-detail', args=[feedback.id])
    except Exception:
        detail_path = "/"
    url = _build_absolute_url(detail_path)
    return {
        "id": getattr(feedback, "id", None),
        "title": getattr(feedback, "title", None),
        "status": getattr(feedback, "status", None),
        "status_display": feedback.get_status_display() if hasattr(feedback, "get_status_display") else None,
        "created_by": getattr(getattr(feedback, "created_by", None), "username", None),
        "assignee": getattr(getattr(feedback, "assignee", None), "username", None),
        "created_at": getattr(feedback, "created_at", None).isoformat() if getattr(feedback, "created_at", None) else None,
        "url": url,
    }

def _api_try_urls(urls: List[str], method: str, json: Dict[str, Any]) -> bool:
    last_url = None
    for u in urls:
        try:
            last_url = u
            if method == "post":
                r = requests.post(u, json=json, headers=_headers(), timeout=TIMEOUT, verify=VERIFY_SSL)
            else:
                r = requests.get(u, headers=_headers(), timeout=TIMEOUT, verify=VERIFY_SSL)
            _remember(u, response=r)
            r.raise_for_status()
            return True
        except Exception as e:
            _remember(u, error=e)
    if last_url:
        print(f"[HA] letzter Versuch fehlgeschlagen: {last_url}")
    return False

# ── NEU: robuster Webhook-POST mit TLS-Fallback ───────────────────────────────
def _post_webhook_with_fallback(url: str, payload: Dict[str, Any]) -> bool:
    # 1) Normaler Versuch mit explizitem Connection: close (hilft gg. SSLEOFError)
    try:
        r = requests.post(url, json=payload, timeout=TIMEOUT, verify=VERIFY_SSL, headers={"Connection": "close"})
        _remember(url, response=r)
        r.raise_for_status()
        return True
    except SSLError as e:
        # 2) Einmaliger Fallback mit verify=False (nur, wenn VERIFY_SSL aktiv war)
        try:
            if VERIFY_SSL:
                r2 = requests.post(url, json=payload, timeout=TIMEOUT, verify=False, headers={"Connection": "close"})
                _remember(url, response=r2)
                r2.raise_for_status()
                return True
        except Exception as e2:
            _remember(url, error=e2)
            print(f"[HA] webhook fallback (verify=False) fehlgeschlagen: {e2}")
        _remember(url, error=e)
        print(f"[HA] webhook SSL-Fehler: {e}")
        return False
    except Exception as e:
        _remember(url, error=e)
        print(f"[HA] webhook send fehlgeschlagen: {e}")
        return False

def call_service(domain: str, service: str, data: Dict[str, Any]) -> bool:
    """
    API-Modus: HA Service aufrufen.
    WEBHOOK-Modus: kein direkter Service-Call möglich → False + Hinweis.
    """
    if _use_webhook():
        print("[HA] call_service im Webhook-Modus nicht verfügbar.")
        _remember(HA_WEBHOOK_URL)
        return False
    if not _has_api_config():
        print("[HA] call_service: HA_URL/HA_TOKEN fehlen – übersprungen.")
        _remember("N/A (HA_URL/HA_TOKEN fehlen)")
        return False
    base = f"{HA_URL}/api/services/{domain}/{service}"
    urls = [base, base + "/"]
    return _api_try_urls(urls, "post", data)

def fire_event(event_type: str, data: Dict[str, Any]) -> bool:
    """
    API-Modus: eigenes Event in HA feuern.
    WEBHOOK-Modus: stattdessen direkt per Webhook senden.
    """
    if _use_webhook():
        payload = {"event_type": event_type, **data}
        return _post_webhook_with_fallback(HA_WEBHOOK_URL, payload)

    if not _has_api_config():
        print("[HA] fire_event: HA_URL/HA_TOKEN fehlen – übersprungen.")
        _remember("N/A (HA_URL/HA_TOKEN fehlen)")
        return False

    base = f"{HA_URL}/api/events/{event_type}"
    urls = [base, base + "/"]
    return _api_try_urls(urls, "post", data)

def notify_feedback_event(kind: str, feedback, extra: Optional[Dict[str, Any]] = None) -> None:
    """
    Einheitlicher Eingang: baut Payload + sendet je nach Modus (API oder Webhook).
    Im API-Modus zusätzlich sichtbare Persistent Notification in HA.
    """
    payload = _feedback_payload(feedback)
    if extra:
        payload.update(extra)
    payload["kind"] = kind

    # 1) Event/Webhook
    fire_event("inventory_feedback", payload)

    # 2) Sichtbare Notification (nur im API-Modus; im Webhook-Modus übernimmt das die Automation)
    if not _use_webhook():
        title_map = {
            "created": "Neues Feedback",
            "updated": "Feedback aktualisiert",
            "status_changed": "Feedback-Status geändert",
            "comment_added": "Neuer Kommentar",
        }
        title = f"{title_map.get(kind, 'Feedback')}: {payload.get('title')}"
        msg_lines = [
            f"Status: {payload.get('status_display')}",
            f"Von: {payload.get('created_by')}",
            f"Link: {payload.get('url')}",
        ]
        if kind == "status_changed":
            old = payload.get("old_status_display") or payload.get("old_status") or (extra and extra.get("old_status"))
            if old:
                msg_lines.insert(1, f"Alt: {old} → Neu: {payload.get('status_display')}")
        if kind == "comment_added" and extra:
            author = extra.get("author")
            text = (extra.get("comment") or "").strip()
            msg_lines.insert(1, f"Kommentar von {author}: {(text if len(text)<400 else text[:397]+'…')}")
        call_service("persistent_notification", "create", {
            "title": title,
            "message": "\n".join(msg_lines),
            "notification_id": f"feedback_{payload.get('id')}",
        })
