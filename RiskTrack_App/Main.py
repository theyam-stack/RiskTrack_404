"""
Main.py — RiskTrack Application Entry Point

QMainWindow หลัก  QStackedWidget:
  Index 0 → AuthWindow          (Login / Sign Up)
  Index 1 → risktrack.MainWindow (แอปหลัก)
  
"""

import sys
import os
import json

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget

from auth_manager import AuthManager, AuthWindow
from risktask import MainWindow as RiskTaskMainWindow

_PROFILE_JSON = os.path.join(_ROOT, "profile.json")
_PROFILE_DB_JSON = os.path.join(_ROOT, "profile_db.json")


# ── Helper ────────────────────────────────────────────────────────────
def _write_profile(user: dict) -> None:
    """
    เขียน profile.json จาก user dict ที่ login
    ถ้าเป็น user เดียวกับที่เคยแก้ profile ไว้ ให้คง first/last/nick/role/status/avatar
    (ไม่ให้ชื่อจาก DB ทับการแก้ใน Edit Profile)
    """
    name  = user.get("name", "")
    parts = name.strip().split()
    first = parts[0] if parts else ""
    last  = " ".join(parts[1:]) if len(parts) > 1 else ""

    cur_email = str(user.get("email", "")).strip().lower()

    data = {
        "first":  first,
        "last":   last,
        "nick":   first[:1].upper() if first else "U",
        "email":  user.get("email", ""),
        "role":   "Risk & Task Manager",
        "status": "Active",
        "avatar_path": "",
    }

    # Load per-user profile from scoped DB (preferred).
    existing: dict | None = None
    if cur_email and os.path.exists(_PROFILE_DB_JSON):
        try:
            with open(_PROFILE_DB_JSON, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict) and isinstance(raw.get("users"), dict):
                candidate = raw["users"].get(cur_email, None)
                if isinstance(candidate, dict):
                    existing = candidate
        except (json.JSONDecodeError, OSError):
            existing = None

    # Fallback: legacy single-file profile.json (only if it belongs to this user).
    if existing is None and os.path.exists(_PROFILE_JSON):
        try:
            with open(_PROFILE_JSON, "r", encoding="utf-8") as f:
                candidate = json.load(f)
            if isinstance(candidate, dict):
                candidate_email = str(candidate.get("email", "")).strip().lower()
                if candidate_email and cur_email and candidate_email != cur_email:
                    candidate = None
                existing = candidate
        except (json.JSONDecodeError, OSError):
            existing = None

    if isinstance(existing, dict) and existing:
        # Preserve user-edited profile fields across sessions.
        data["first"] = existing.get("first", data["first"])
        data["last"] = existing.get("last", data["last"])
        data["nick"] = existing.get("nick", data["nick"])
        data["role"] = existing.get("role", data["role"])
        data["status"] = existing.get("status", data["status"])
        data["avatar_path"] = existing.get("avatar_path", data["avatar_path"])
    data["email"] = user.get("email", data["email"])

    try:
        with open(_PROFILE_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except OSError:
        pass

    # Also persist into per-user scoped DB so each user has their own profile.
    if not cur_email:
        return
    scoped = {"users": {}}
    if os.path.exists(_PROFILE_DB_JSON):
        try:
            with open(_PROFILE_DB_JSON, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict) and isinstance(raw.get("users"), dict):
                scoped["users"] = raw["users"]
        except (json.JSONDecodeError, OSError):
            pass
    scoped["users"][cur_email] = dict(data)
    try:
        with open(_PROFILE_DB_JSON, "w", encoding="utf-8") as f:
            json.dump(scoped, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


# ── Main Application Window ───────────────────────────────────────────
class AppWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RiskTrack")
        self.resize(1280, 820)
        self.setMinimumSize(900, 600)

        self._auth      = AuthManager.get_instance()
        self._risktrack = None

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        # Index 0 → Auth
        self._auth_win = AuthWindow()
        self._stack.addWidget(self._auth_win)

        # เมื่อ login/signup สำเร็จ -> เปิดหน้า RiskTask
        self._auth_win.auth_complete.connect(self._on_auth_complete)

        self._restore_session()

    # ── Session ───────────────────────────────────────────────────
    def _restore_session(self) -> None:
        email = self._auth.load_session()
        if not email:
            return
        user = self._auth.find_user(email)
        if user:
            self._show_risktask(user)
        else:
            self._auth.clear_session()

    # ── Handlers ──────────────────────────────────────────────────
    def _on_auth_complete(self, user: dict) -> None:
        self._show_risktask(user)

    def _on_logout(self) -> None:
        if self._risktrack is not None:
            page = getattr(self._risktrack, "page_edit_profile", None)
            if page is not None:
                t = getattr(page, "_persist_timer", None)
                if t is not None:
                    t.stop()
                if getattr(page, "_form_fields_valid", lambda: False)():
                    page._persist_profile_auto()

        self._auth.clear_session()
        self._auth_win.reset_to_login()
        self._stack.setCurrentIndex(0)

        if self._risktrack is not None:
            self._stack.removeWidget(self._risktrack)
            self._risktrack.deleteLater()
            self._risktrack = None

    # ── Show RiskTask ──────────────────────────────────────────────
    def _show_risktask(self, user: dict) -> None:
        _write_profile(user)
        if self._risktrack is not None:
            self._stack.removeWidget(self._risktrack)
            self._risktrack.deleteLater()
        self._risktrack = RiskTaskMainWindow()
        try:
            self._risktrack.btn_logout.clicked.disconnect()
        except (RuntimeError, TypeError):
            pass
        self._risktrack.btn_logout.clicked.connect(self._on_logout)
        self._stack.addWidget(self._risktrack)
        self._stack.setCurrentWidget(self._risktrack)


# ── Entry Point ───────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet("* { font-family: 'Segoe UI', Arial, sans-serif; }")
    w = AppWindow()
    w.show()
    sys.exit(app.exec())