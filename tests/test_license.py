"""Tests for the license framework.

We can't hit the real Polar API in unit tests (network, flake, key sharing),
so verification calls are monkey-patched. The cache layer is exercised against
a tempfile DB so we never touch ~/.zk-pipeline-doctor.
"""

from __future__ import annotations

import json
import tempfile
import time
import urllib.error
from pathlib import Path

import pytest

from zk_doctor import license as lic
from zk_doctor.pro import PRO_DETECTORS, pro_only, ProLocked


# ---------- cache layer ----------

def test_cache_empty_returns_free():
    with tempfile.TemporaryDirectory() as d:
        db = Path(d) / "lic.db"
        info = lic.current_license(db_path=db)
        assert info.tier == "free"
        assert info.key_display == ""


def test_save_and_load_round_trips():
    with tempfile.TemporaryDirectory() as d:
        db = Path(d) / "lic.db"
        lic._save_license(
            key="ABCDEFGH-IJKLMNOP-QRSTUVWX-YZ123456",
            activation_id="act-1",
            tier="pro",
            raw={"status": "granted"},
            db_path=db,
        )
        info = lic.current_license(db_path=db)
        assert info.tier == "pro"
        assert info.activation_id == "act-1"
        assert info.key_display.endswith("123456")
        assert info.raw == {"status": "granted"}


def test_expired_cache_resolves_to_free():
    """If cached_at is older than OFFLINE_GRACE_SEC, treat as free."""
    with tempfile.TemporaryDirectory() as d:
        db = Path(d) / "lic.db"
        # Save normally, then rewrite cached_at to be 8 days old
        lic._save_license(
            key="OLDKEY-1111", activation_id=None, tier="pro",
            raw={"status": "granted"}, db_path=db,
        )
        conn = lic._open_db(db)
        try:
            conn.execute(
                "UPDATE licenses SET cached_at = ?",
                (int(time.time()) - 8 * 24 * 60 * 60,),
            )
            conn.commit()
        finally:
            conn.close()

        info = lic.current_license(db_path=db)
        assert info.tier == "free"


def test_clear_cache_wipes_rows():
    with tempfile.TemporaryDirectory() as d:
        db = Path(d) / "lic.db"
        lic._save_license(
            key="X-2222", activation_id=None, tier="pro",
            raw={}, db_path=db,
        )
        assert lic.current_license(db_path=db).tier == "pro"
        lic._clear_cache(db_path=db)
        assert lic.current_license(db_path=db).tier == "free"


# ---------- verify_license_key against mocked Polar ----------

class _FakeResp:
    def __init__(self, body: dict):
        self._body = json.dumps(body).encode("utf-8")
    def read(self):
        return self._body
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False


def test_verify_granted_key_caches(monkeypatch):
    """A 'granted' status should validate, activate, and cache."""
    calls: list[str] = []

    def fake_urlopen(req, timeout=5.0):
        calls.append(req.full_url)
        if "validate" in req.full_url:
            return _FakeResp({
                "id": "lic-uuid",
                "key": "FAKE-FAKE-FAKE",
                "status": "granted",
                "customer": {"email": "x@example.com"},
            })
        if "activate" in req.full_url:
            return _FakeResp({"id": "activation-uuid", "label": "hostname"})
        raise AssertionError(f"unexpected URL: {req.full_url}")

    monkeypatch.setattr(lic.urllib.request, "urlopen", fake_urlopen)

    with tempfile.TemporaryDirectory() as d:
        db = Path(d) / "lic.db"
        result = lic.verify_license_key("FAKE-FAKE-FAKE", db_path=db)
        assert result is not None
        assert result["status"] == "granted"
        # Both endpoints hit
        assert any("validate" in u for u in calls)
        assert any("activate" in u for u in calls)
        # Cached as pro
        info = lic.current_license(db_path=db)
        assert info.tier == "pro"
        assert info.activation_id == "activation-uuid"


def test_verify_revoked_key_returns_none(monkeypatch):
    def fake_urlopen(req, timeout=5.0):
        return _FakeResp({"status": "revoked"})
    monkeypatch.setattr(lic.urllib.request, "urlopen", fake_urlopen)
    with tempfile.TemporaryDirectory() as d:
        db = Path(d) / "lic.db"
        assert lic.verify_license_key("REVOKED-KEY", db_path=db) is None
        # Nothing cached
        assert lic.current_license(db_path=db).tier == "free"


def test_verify_404_returns_none(monkeypatch):
    """Polar returning 404 = key not found = unlicensed."""
    def fake_urlopen(req, timeout=5.0):
        raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, None)
    monkeypatch.setattr(lic.urllib.request, "urlopen", fake_urlopen)
    with tempfile.TemporaryDirectory() as d:
        db = Path(d) / "lic.db"
        assert lic.verify_license_key("NOT-A-KEY", db_path=db) is None


def test_verify_network_error_returns_none(monkeypatch):
    """If Polar is unreachable, verification fails (caller stays free)."""
    def fake_urlopen(req, timeout=5.0):
        raise urllib.error.URLError("DNS fail")
    monkeypatch.setattr(lic.urllib.request, "urlopen", fake_urlopen)
    with tempfile.TemporaryDirectory() as d:
        db = Path(d) / "lic.db"
        assert lic.verify_license_key("WHATEVER", db_path=db) is None


def test_verify_malformed_key_returns_none(monkeypatch):
    """Empty or whitespace-only key short-circuits without a network call."""
    called = []
    def fake_urlopen(req, timeout=5.0):
        called.append(True)
        return _FakeResp({"status": "granted"})
    monkeypatch.setattr(lic.urllib.request, "urlopen", fake_urlopen)
    with tempfile.TemporaryDirectory() as d:
        db = Path(d) / "lic.db"
        assert lic.verify_license_key("", db_path=db) is None
        assert lic.verify_license_key("   ", db_path=db) is None
        assert called == []  # no network calls were made


def test_activation_failure_does_not_block_validation(monkeypatch):
    """If /activate fails (e.g. activation limit), the key is still valid."""
    def fake_urlopen(req, timeout=5.0):
        if "validate" in req.full_url:
            return _FakeResp({"status": "granted", "id": "lic-uuid"})
        if "activate" in req.full_url:
            raise urllib.error.HTTPError(req.full_url, 403, "limit reached", {}, None)
        raise AssertionError("unexpected url")
    monkeypatch.setattr(lic.urllib.request, "urlopen", fake_urlopen)
    with tempfile.TemporaryDirectory() as d:
        db = Path(d) / "lic.db"
        result = lic.verify_license_key("FOO", db_path=db)
        assert result is not None  # still granted
        info = lic.current_license(db_path=db)
        assert info.tier == "pro"
        assert info.activation_id is None  # but activation failed


# ---------- @pro_only decorator ----------

def test_pro_only_decorator_blocks_free_tier(monkeypatch):
    """Decorated functions return a ProLocked when is_pro() is False."""
    monkeypatch.setattr(lic, "current_license", lambda db_path=None: lic.LicenseInfo(
        tier="free", key_display="", activation_id=None, cached_at=0, raw={}
    ))

    @pro_only(name="dummy", summary="test only")
    def some_detector(path):
        return {"score": 9, "notes": "should not run"}

    out = some_detector(Path("/tmp"))
    assert isinstance(out, ProLocked)
    assert out.locked is True
    assert out.score == 0
    assert "upgrade" in out.notes.lower() or "locked" in out.notes.lower()


def test_pro_only_decorator_runs_on_pro_tier(monkeypatch):
    """Decorated functions run normally when is_pro() returns True."""
    monkeypatch.setattr(lic, "is_pro", lambda: True)

    @pro_only(name="dummy2", summary="test only")
    def some_detector(path):
        return {"score": 9, "notes": "ran"}

    out = some_detector(Path("/tmp"))
    assert out == {"score": 9, "notes": "ran"}


def test_pro_detectors_registry_includes_known_names():
    """All 4 v0.3.0 pro detectors register themselves at import time."""
    # Importing the package above already triggered registration.
    # We import the four pro modules to make absolutely sure they registered.
    from zk_doctor.detectors import (
        circuit_complexity, proving_system_pitfalls,
        verifier_soundness, multi_file_consistency,
    )
    _ = (circuit_complexity, proving_system_pitfalls,
         verifier_soundness, multi_file_consistency)

    names = {d["name"] for d in PRO_DETECTORS}
    assert "circuit_complexity" in names
    assert "proving_system_pitfalls" in names
    assert "verifier_soundness" in names
    assert "multi_file_consistency" in names
