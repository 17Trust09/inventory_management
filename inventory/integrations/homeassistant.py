# Home Assistant Integration für Lagerdatenbank:
# - Zwei Betriebsarten:
#     * API-Modus (Token, /api/... Endpoints)  → HA_URL/HA_API_TOKEN nötig
#     * WEBHOOK-Modus (Cloudhook/HA-Webhook)   → HA_WEBHOOK_URL genügt
# - Robuster Health-Check (/api und /api/), Diagnose, Fallbacks
# - Frontend-Statusmeldungen auf Deutsch

from __future__ import annotations

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, Future
import requests
from typing import Any, Dict, Optional, List, Tuple
from django.conf import settings
from django.urls import reverse
from django.utils.timezone import now
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

# Item-Markierung (optional, für LED/Schubladen)
HA_MARK_EVENT = os.getenv("HA_MARK_EVENT", "inventory_item_marked").strip()
HA_MARK_SERVICE = os.getenv("HA_MARK_SERVICE", "").strip()  # z. B. "light.turn_on"
HA_MARK_ENTITY_ID = os.getenv("HA_MARK_ENTITY_ID", "").strip()

# Cache & Diagnose
_LAST_CHECK_TS: float = 0.0
_IS_AVAILABLE: Optional[bool] = None
_CACHE_SECONDS = 60
_STATUS_REFRESH_FUTURE: Optional[Future] = None
_LAST_STATUS_MESSAGE: Optional[str] = None
_STATUS_LOCK = threading.Lock()
_HA_EXECUTOR = ThreadPoolExecutor(max_workers=2)

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

def _refresh_status_background() -> None:
    global _LAST_STATUS_MESSAGE
    available = check_available(force=True)
    _LAST_STATUS_MESSAGE = (
        "Feedbacks werden online übertragen" if available
        else "Keine Internet-Verbindung oder Server nicht erreichbar – Feedbacks werden nicht übertragen"
    )

def get_status_tuple() -> tuple[bool, str]:
    """
    Liefert (available, message) für den UI-Badge.
    """
    if _use_webhook() and not _has_api_config():
        return True, "Feedbacks werden online per Webhook übertragen"
    if not _has_api_config():
        return False, "Keine HA-Konfiguration (.env) – Token/URL fehlen"
    async_status = os.getenv("HA_STATUS_ASYNC", "true").lower() == "true"
    if async_status:
        global _STATUS_REFRESH_FUTURE
        now = time.monotonic()
        cache_valid = _IS_AVAILABLE is not None and (now - _LAST_CHECK_TS) < _CACHE_SECONDS
        if not cache_valid:
            with _STATUS_LOCK:
                if _STATUS_REFRESH_FUTURE is None or _STATUS_REFRESH_FUTURE.done():
                    _STATUS_REFRESH_FUTURE = _HA_EXECUTOR.submit(_refresh_status_background)
        if _IS_AVAILABLE is None:
            return False, _LAST_STATUS_MESSAGE or "Status wird geprüft…"
        return (
            True if _IS_AVAILABLE else False,
            _LAST_STATUS_MESSAGE
            or ("Feedbacks werden online übertragen" if _IS_AVAILABLE else "Keine Internet-Verbindung oder Server nicht erreichbar – Feedbacks werden nicht übertragen"),
        )
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
        "mark_event": HA_MARK_EVENT,
        "mark_service": HA_MARK_SERVICE or None,
        "mark_entity_id": HA_MARK_ENTITY_ID or None,
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


def _item_payload(item, user=None) -> Dict[str, Any]:
    try:
        detail_path = reverse("edit-item", args=[item.id])
    except Exception:
        detail_path = "/"
    url = _build_absolute_url(detail_path)

    storage_location = getattr(item, "storage_location", None)
    return {
        "id": getattr(item, "id", None),
        "name": getattr(item, "name", None),
        "barcode": getattr(item, "barcode", None),
        "quantity": getattr(item, "quantity", None),
        "item_type": getattr(item, "item_type", None),
        "category": getattr(getattr(item, "category", None), "name", None),
        "overview": getattr(getattr(item, "overview", None), "slug", None),
        "overview_name": getattr(getattr(item, "overview", None), "name", None),
        "location_letter": getattr(item, "location_letter", None),
        "location_number": getattr(item, "location_number", None),
        "location_shelf": getattr(item, "location_shelf", None),
        "storage_location": storage_location.get_full_path() if storage_location else None,
        "ha_entity_id": getattr(storage_location, "ha_entity_id", None) if storage_location else None,
        "marked_by": getattr(user, "username", None) if user else None,
        "marked_at": now().isoformat(),
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

def _notify_feedback_event_sync(kind: str, feedback, extra: Optional[Dict[str, Any]] = None) -> None:
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


def notify_feedback_event(kind: str, feedback, extra: Optional[Dict[str, Any]] = None) -> None:
    async_send = os.getenv("HA_FEEDBACK_ASYNC", "true").lower() == "true"
    if async_send:
        _HA_EXECUTOR.submit(_notify_feedback_event_sync, kind, feedback, extra)
        return
    _notify_feedback_event_sync(kind, feedback, extra)

def notify_item_marked(item, user=None) -> bool:
    """
    Sendet ein Event (oder Webhook) an Home Assistant, wenn ein Item markiert wurde.
    Optionaler Service-Call, falls HA_MARK_SERVICE gesetzt ist.
    """
    payload = _item_payload(item, user=user)
    event_type = HA_MARK_EVENT or "inventory_item_marked"
    ok = fire_event(event_type, payload)

    if HA_MARK_SERVICE:
        try:
            domain, service = HA_MARK_SERVICE.split(".", 1)
        except ValueError:
            domain, service = "", ""
        if domain and service:
            service_data = {"entity_id": HA_MARK_ENTITY_ID or payload.get("ha_entity_id")}
            service_data.update(payload)
            ok = call_service(domain, service, service_data) and ok
    return ok
