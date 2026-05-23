"""License framework for zk-doctor Pro.

Verification strategy: Polar's native customer-portal license-key API.
- `POST /v1/customer-portal/license-keys/validate` issues a public, unauthenticated
  validation call (Polar designed it for desktop / mobile clients exactly so the
  CLI doesn't have to embed an org-level API token).
- On first activation we also call `/activate` to bind the key to this machine
  (label = hostname). Polar tracks per-key activation count if the operator
  configured an activation limit on the benefit.

Cache: a SQLite DB at `~/.zk-pipeline-doctor/licenses.db` stores the most
recent successful validation. Subsequent invocations re-check the cache;
re-validation against Polar happens at most every 24h to avoid the doctor
hammering Polar on every run.

If Polar is unreachable (offline laptop), we fall through to the cached row
provided `cached_at` is within 7 days. Stricter than that and we treat the
session as un-licensed.

Threat model: this is anti-casual-piracy, not anti-determined-pirate. A
sufficiently motivated user can patch the binary or fake the cache; that
risk is inherent to any client-side check. The point is to make casual key
sharing painful (each activation is bound to a hostname, surfaces in the
operator's Polar dashboard) and to make the upgrade path obvious.
"""

from __future__ import annotations

import json
import os
import socket
import sqlite3
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


# Polar org ID for Battam1111. This is *public* (visible on storefront URLs)
# so embedding it in the CLI is fine. If you fork the project, change this.
POLAR_ORG_ID = "b23fe650-4bde-4d68-983a-67f93e39224f"

# Endpoints
POLAR_VALIDATE_URL = "https://api.polar.sh/v1/customer-portal/license-keys/validate"
POLAR_ACTIVATE_URL = "https://api.polar.sh/v1/customer-portal/license-keys/activate"

# Cache location
CACHE_DIR = Path.home() / ".zk-pipeline-doctor"
CACHE_DB = CACHE_DIR / "licenses.db"

# Re-validation cadence
REVALIDATE_AFTER_SEC = 24 * 60 * 60          # check Polar at most once per day
OFFLINE_GRACE_SEC = 7 * 24 * 60 * 60         # cached row valid for 7 days offline


@dataclass
class LicenseInfo:
    """Resolved license state."""
    tier: str                 # "free" | "pro"
    key_display: str          # masked key (e.g. "****-A1B2C3") for UI
    activation_id: str | None # Polar activation UUID, if any
    cached_at: int            # unix timestamp of last successful validation
    raw: dict[str, Any]       # the full Polar response (or {} for free)


# ---------- low-level cache plumbing ----------

def _ensure_cache_dir() -> None:
    """mkdir -p ~/.zk-pipeline-doctor with mode 0o700."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(CACHE_DIR, 0o700)
    except Exception:
        # Best-effort; on Windows / odd filesystems chmod may not stick.
        pass


def _open_db(db_path: Path | None = None) -> sqlite3.Connection:
    """Open the license cache DB, creating the schema if needed."""
    db_path = db_path or CACHE_DB
    if db_path is CACHE_DB:
        _ensure_cache_dir()
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS licenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL UNIQUE,
            activation_id TEXT,
            tier TEXT NOT NULL,
            cached_at INTEGER NOT NULL,
            raw_json TEXT NOT NULL
        )
        """
    )
    return conn


def _save_license(
    key: str,
    activation_id: str | None,
    tier: str,
    raw: dict[str, Any],
    db_path: Path | None = None,
) -> None:
    """Insert-or-replace a license row keyed by the license key string."""
    conn = _open_db(db_path)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO licenses (key, activation_id, tier, cached_at, raw_json) "
            "VALUES (?, ?, ?, ?, ?)",
            (key, activation_id, tier, int(time.time()), json.dumps(raw)),
        )
        conn.commit()
    finally:
        conn.close()


def _load_latest(db_path: Path | None = None) -> dict[str, Any] | None:
    """Return the most recently cached row, or None if the cache is empty."""
    db_path = db_path or CACHE_DB
    if not db_path.exists():
        return None
    conn = _open_db(db_path)
    try:
        cur = conn.execute(
            "SELECT key, activation_id, tier, cached_at, raw_json "
            "FROM licenses ORDER BY cached_at DESC LIMIT 1"
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "key": row[0],
            "activation_id": row[1],
            "tier": row[2],
            "cached_at": row[3],
            "raw": json.loads(row[4]) if row[4] else {},
        }
    finally:
        conn.close()


def _clear_cache(db_path: Path | None = None) -> None:
    """Wipe all cached licenses (used by `zk-doctor license-status --clear`)."""
    db_path = db_path or CACHE_DB
    if not db_path.exists():
        return
    conn = _open_db(db_path)
    try:
        conn.execute("DELETE FROM licenses")
        conn.commit()
    finally:
        conn.close()


# ---------- Polar API plumbing ----------

def _polar_post(url: str, body: dict[str, Any], timeout: float = 5.0) -> dict[str, Any]:
    """POST JSON to Polar. Returns parsed response on success; raises on HTTP error.

    Uses urllib so the CLI has zero extra runtime deps beyond stdlib.
    """
    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "zk-pipeline-doctor (license-check)",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _mask_key(key: str) -> str:
    """Render a key as `****-LAST6` for display."""
    if len(key) <= 6:
        return "****"
    return f"****-{key[-6:].upper()}"


# ---------- public API ----------

def verify_license_key(
    key: str,
    db_path: Path | None = None,
    org_id: str = POLAR_ORG_ID,
) -> dict[str, Any] | None:
    """Verify a key against Polar and (if granted) record an activation.

    Returns the full Polar response dict on success, or None if the key is
    invalid / revoked / wrong-org / network-error-with-no-cache.

    Side effect: on success, caches the row in the SQLite DB.
    """
    if not key or not key.strip():
        return None
    key = key.strip()

    # Step 1: validate
    try:
        validated = _polar_post(
            POLAR_VALIDATE_URL,
            {"key": key, "organization_id": org_id},
        )
    except urllib.error.HTTPError as e:
        # 404 = key not found; 403 = revoked; treat all 4xx as "not licensed"
        if 400 <= e.code < 500:
            return None
        # 5xx -> Polar is down; surface as failure (caller can decide UX)
        return None
    except (urllib.error.URLError, socket.timeout, TimeoutError):
        # Network down → no point caching; treat as failure for this call
        return None
    except Exception:
        return None

    # Polar returns status "granted" | "revoked" | "disabled"
    status = validated.get("status")
    if status != "granted":
        return None

    # Step 2: activate this machine (best-effort; failure is non-fatal — the
    # key is still valid, we just can't bind to a hostname slot)
    activation_id: str | None = None
    try:
        host_label = socket.gethostname() or "unknown-host"
        activation = _polar_post(
            POLAR_ACTIVATE_URL,
            {
                "key": key,
                "organization_id": org_id,
                "label": f"zk-doctor@{host_label}",
            },
        )
        activation_id = activation.get("id")
    except Exception:
        # Activation limits hit / network blip / endpoint changed: don't fail
        # the whole flow over it.
        activation_id = None

    # Step 3: cache
    _save_license(
        key=key,
        activation_id=activation_id,
        tier="pro",
        raw=validated,
        db_path=db_path,
    )
    return validated


def current_license(db_path: Path | None = None) -> LicenseInfo:
    """Return the current license state for this machine.

    - If a granted key is cached and we're inside the 24h revalidation window,
      return it as `tier="pro"` from cache.
    - If we're past the window but inside the 7-day offline grace, still serve
      pro from cache (we'll lazily re-check on next run).
    - Otherwise, return `tier="free"`.

    This function never raises; failure modes always degrade to free tier.
    """
    try:
        row = _load_latest(db_path=db_path)
    except Exception:
        row = None

    if not row or row["tier"] != "pro":
        return LicenseInfo(tier="free", key_display="", activation_id=None, cached_at=0, raw={})

    age = int(time.time()) - row["cached_at"]
    if age > OFFLINE_GRACE_SEC:
        # Cached row is too old to trust offline. Treat as free until the user
        # runs `zk-doctor activate <key>` again (or we re-validate in-process).
        return LicenseInfo(tier="free", key_display="", activation_id=None, cached_at=0, raw={})

    return LicenseInfo(
        tier="pro",
        key_display=_mask_key(row["key"]),
        activation_id=row["activation_id"],
        cached_at=row["cached_at"],
        raw=row["raw"],
    )


def is_pro() -> bool:
    """Convenience: True iff the current license resolves to pro tier."""
    return current_license().tier == "pro"
