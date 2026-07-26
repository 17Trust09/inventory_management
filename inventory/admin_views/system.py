"""
Admin-System: Systemstatus, Tailscale, ESP32, Updates, Backup.
"""
import os
import shutil
import subprocess
import json
from pathlib import Path
from datetime import timedelta

from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.conf import settings
from django.utils import timezone

from ..models import GlobalSettings
from .helpers import staff_required, superuser_required, _get_global_settings, _get_tailscale_status

logger = __import__('logging').getLogger(__name__)


# ---------------------------------------------------------------------------
# System-Status
# ---------------------------------------------------------------------------
@staff_required
def admin_system_status(request):
    import platform
    ctx = {
        "python_version": platform.python_version(),
        "django_version": __import__('django').get_version(),
        "platform": platform.platform(),
        "hostname": platform.node(),
        "tailscale": _get_tailscale_status(),
    }
    return render(request, 'inventory/admin_system_status.html', ctx)


# ---------------------------------------------------------------------------
# Tailscale
# ---------------------------------------------------------------------------
@staff_required
def admin_tailscale_setup(request):
    settings_obj = _get_global_settings()
    tailscale = _get_tailscale_status()
    steps_complete = settings_obj.tailscale_setup_step

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "step_complete":
            settings_obj.tailscale_setup_step = min(steps_complete + 1, 4)
            settings_obj.save()
        elif action == "finish":
            settings_obj.tailscale_setup_complete = True
            settings_obj.save()
        elif action == "ignore":
            settings_obj.tailscale_setup_ignored = True
            settings_obj.save()
        return redirect("admin_tailscale_setup")

    return render(request, 'inventory/admin_tailscale_setup.html', {
        "tailscale": tailscale,
        "steps_complete": steps_complete,
    })


# ---------------------------------------------------------------------------
# ESP32
# ---------------------------------------------------------------------------
@staff_required
def admin_esp32_setup(request):
    from ..models import ItemMark
    settings_obj = _get_global_settings()

    if request.method == "POST":
        secs_str = request.POST.get("esp_mark_auto_clear_seconds", "").strip()
        if secs_str:
            try:
                secs = int(secs_str)
                if secs >= 0:
                    settings_obj.esp_mark_auto_clear_seconds = secs
                    settings_obj.save(update_fields=["esp_mark_auto_clear_seconds"])
                    messages.success(request, f"Auto-Clear auf {secs} Sekunden gesetzt.")
                else:
                    messages.error(request, "Wert muss >= 0 sein.")
            except ValueError:
                messages.error(request, "Ungültige Zahl.")
        else:
            messages.error(request, "Bitte einen Wert eingeben.")
        return redirect("admin_esp32_setup")

    marks = ItemMark.objects.select_related("item", "marked_by").order_by("-marked_at")[:50]
    return render(request, 'inventory/admin_esp32_setup.html', {
        "marks": marks,
        "settings": settings_obj,
    })


# ---------------------------------------------------------------------------
# Git/Update-Helper
# ---------------------------------------------------------------------------
def fetch_all_branches() -> list[str]:
    repo_url = getattr(settings, "UPDATE_REPO_URL_MAIN", "").strip()
    if not repo_url:
        logger.error("UPDATE_REPO_URL_MAIN ist nicht konfiguriert.")
        return []
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--heads", repo_url],
            cwd=settings.BASE_DIR, capture_output=True, text=True, timeout=20,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.exception("Remote-Branches konnten nicht abgerufen werden: %s", exc)
        return []
    if result.returncode != 0:
        logger.error("git ls-remote fehlgeschlagen: %s", (result.stderr or result.stdout or "Unbekannter Fehler").strip())
        return []
    branches = []
    for line in (result.stdout or "").splitlines():
        parts = line.strip().split()
        if len(parts) < 2:
            continue
        ref = parts[1]
        if not ref.startswith("refs/heads/"):
            continue
        branch_name = ref.removeprefix("refs/heads/").strip()
        if branch_name and branch_name != "HEAD":
            branches.append(branch_name)
    return sorted(set(branches))


def _run_git(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=settings.BASE_DIR, capture_output=True, text=True,
    )


def _ensure_git_origin(repo_url: str) -> str | None:
    base_dir = settings.BASE_DIR
    if not (base_dir / ".git").exists():
        init = _run_git(["init"])
        if init.returncode != 0:
            return init.stderr.strip() or init.stdout.strip() or "Git-Repository konnte nicht initialisiert werden."
    remote_url = _run_git(["remote", "get-url", "origin"])
    if remote_url.returncode != 0:
        add_remote = _run_git(["remote", "add", "origin", repo_url])
        if add_remote.returncode != 0:
            return add_remote.stderr.strip() or add_remote.stdout.strip() or "Git-Remote konnte nicht gesetzt werden."
    elif remote_url.stdout.strip() != repo_url:
        set_remote = _run_git(["remote", "set-url", "origin", repo_url])
        if set_remote.returncode != 0:
            return set_remote.stderr.strip() or set_remote.stdout.strip() or "Git-Remote konnte nicht aktualisiert werden."
    return None


def _git_stdout(args: list[str]) -> str:
    result = _run_git(args)
    if result.returncode != 0:
        return ""
    return (result.stdout or "").strip()


def _git_count(args: list[str]) -> int:
    output = _git_stdout(args)
    try:
        return int(output)
    except (TypeError, ValueError):
        return 0


def _get_git_status_dynamic(branch_name: str) -> dict[str, str | int | bool]:
    branch_name = (branch_name or "").strip()
    repo_url = getattr(settings, "UPDATE_REPO_URL_MAIN", "").strip()
    status = {
        "branch": branch_name, "behind_count": 0, "ahead_count": 0,
        "current_sha": "", "current_sha_short": "", "remote_sha": "", "remote_sha_short": "",
        "last_commit": "", "last_commit_short": "", "is_current": False,
    }
    if not branch_name or not repo_url:
        status["error"] = "Kein Branch oder Repository nicht konfiguriert."
        return status
    origin_error = _ensure_git_origin(repo_url)
    if origin_error:
        status["error"] = origin_error
        return status
    fetch = _run_git(["fetch", "origin", branch_name])
    if fetch.returncode != 0:
        status["error"] = fetch.stderr.strip() or fetch.stdout.strip() or "Git fetch fehlgeschlagen."
        return status
    current_sha = _git_stdout(["rev-parse", "HEAD"])
    remote_sha = _git_stdout(["rev-parse", f"origin/{branch_name}"])
    if not remote_sha:
        fetch_tracking = _run_git(["fetch", "origin", f"{branch_name}:refs/remotes/origin/{branch_name}"])
        if fetch_tracking.returncode != 0:
            status["error"] = fetch_tracking.stderr.strip() or fetch_tracking.stdout.strip() or "Remote-Branch konnte nicht aktualisiert werden."
            return status
        remote_sha = _git_stdout(["rev-parse", f"origin/{branch_name}"])
    behind_count = _git_count(["rev-list", "--count", f"HEAD..origin/{branch_name}"])
    ahead_count = _git_count(["rev-list", "--count", f"origin/{branch_name}..HEAD"])
    status.update({
        "behind_count": behind_count, "ahead_count": ahead_count,
        "current_sha": current_sha, "current_sha_short": current_sha[:7] if current_sha else "",
        "remote_sha": remote_sha, "remote_sha_short": remote_sha[:7] if remote_sha else "",
        "last_commit": remote_sha, "last_commit_short": remote_sha[:7] if remote_sha else "",
        "is_current": bool(current_sha and remote_sha and current_sha == remote_sha),
    })
    return status


_get_git_status = _get_git_status_dynamic  # Rückwärtskompatibilität


# ---------------------------------------------------------------------------
# Backup-Helper
# ---------------------------------------------------------------------------
def _get_backup_root(settings_obj: GlobalSettings | None = None) -> tuple[Path, str | None]:
    if settings_obj is None:
        settings_obj = _get_global_settings()
    configured = (settings_obj.backup_storage_path or "").strip()
    if configured:
        backup_root = Path(configured)
        if not backup_root.exists():
            return backup_root, "Backup-Speicherort existiert nicht."
        return backup_root, None
    return settings.BASE_DIR / "backup", None


def _get_external_backup_paths() -> list[tuple[str, str]]:
    candidates = []
    for base in (Path("/mnt"), Path("/media"), Path("/run/media")):
        if base.exists():
            for entry in base.iterdir():
                if entry.is_dir():
                    candidates.append(entry)
    return [(str(p), str(p)) for p in candidates]


def _get_backup_entries() -> list[dict[str, str]]:
    backup_root, _ = _get_backup_root()
    if not backup_root.exists():
        return []
    entries = []
    for item in sorted(backup_root.iterdir(), reverse=True):
        if not item.is_dir():
            continue
        db_path = item / "db.sqlite3"
        media_path = item / "media"
        entries.append({"name": item.name, "path": str(item), "has_db": db_path.exists(), "has_media": media_path.exists()})
    return entries


def _create_backup() -> tuple[bool, str]:
    settings_obj = _get_global_settings()
    backup_root, error = _get_backup_root(settings_obj)
    if error:
        return False, error
    backup_root.mkdir(parents=True, exist_ok=True)
    backup_dir = backup_root / timezone.now().strftime("%Y-%m-%d_%H-%M-%S")
    db_source = settings.BASE_DIR / "db.sqlite3"
    media_source = settings.BASE_DIR / "media"
    if not db_source.exists():
        return False, "db.sqlite3 nicht gefunden."
    if not media_source.exists():
        return False, "media-Ordner nicht gefunden."
    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(db_source, backup_dir / "db.sqlite3")
        shutil.copytree(media_source, backup_dir / "media")
    except OSError as exc:
        return False, f"Backup fehlgeschlagen: {exc}"
    settings_obj.last_backup_at = timezone.now()
    settings_obj.save(update_fields=["last_backup_at"])
    return True, f"Backup erstellt: {backup_dir.name}"


def _prune_backups(keep_count: int) -> int:
    if keep_count <= 0:
        return 0
    backup_root, _ = _get_backup_root()
    if not backup_root.exists():
        return 0
    entries = [item for item in sorted(backup_root.iterdir(), reverse=True) if item.is_dir()]
    removed = 0
    for item in entries[keep_count:]:
        try:
            shutil.rmtree(item)
            removed += 1
        except OSError:
            continue
    return removed


def _restore_backup(backup_dir: str) -> tuple[bool, str]:
    backup_root, error = _get_backup_root()
    if error:
        return False, error
    backup_path = backup_root / backup_dir
    if not backup_path.exists():
        return False, "Backup-Verzeichnis nicht gefunden."
    db_source = backup_path / "db.sqlite3"
    media_source = backup_path / "media"
    if not db_source.exists():
        return False, "Backup enthält keine db.sqlite3."
    if not media_source.exists():
        return False, "Backup enthält keinen media-Ordner."
    db_target = settings.BASE_DIR / "db.sqlite3"
    media_target = settings.BASE_DIR / "media"
    try:
        shutil.copy2(db_source, db_target)
        if media_target.exists():
            shutil.rmtree(media_target)
        shutil.copytree(media_source, media_target)
    except OSError as exc:
        return False, f"Rollback fehlgeschlagen: {exc}"
    return True, "Rollback abgeschlossen."


# ---------------------------------------------------------------------------
# Admin Updates
# ---------------------------------------------------------------------------
@superuser_required
def admin_updates(request):
    """Zeigt Update-Anleitung fuer Unraid und Raspberry Pi."""
    try:
        import subprocess
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, cwd=settings.BASE_DIR
        )
        active_branch = result.stdout.strip() or "unbekannt"
    except Exception:
        active_branch = "unbekannt"

    return render(request, 'inventory/admin_updates.html', {
        "active_git_branch": active_branch,
    })

