"""
auth_manager.py — Authentication Manager + AuthWindow
══════════════════════════════════════════════════════
รวม: auth_manager + Auth_UI

จัดการ login / signup / forgot-password / session
และ AuthWindow widget (Login ↔ Sign Up stack)

การส่ง OTP ทำจริงผ่าน SMTP (config.py)
ถ้ายังไม่ได้ตั้งค่า SMTP → แสดง code ใน popup (dev mode)
"""

import sys
import os

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import json
import random
import string
import smtplib
import threading
from datetime import datetime, timedelta
from email.mime.text      import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Tuple, Union

from PySide6.QtWidgets import QWidget, QVBoxLayout, QStackedWidget
from PySide6.QtCore    import Signal

from database import DatabaseManager, User

# ── Config (graceful fallback) ───────────────────────────────────────
try:
    from config import (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS,
                        RESET_CODE_EXPIRE, SESSION_FILENAME)
except ImportError:
    SMTP_HOST          = "smtp.gmail.com"
    SMTP_PORT          = 587
    SMTP_USER          = ""
    SMTP_PASS          = ""
    RESET_CODE_EXPIRE  = 10
    SESSION_FILENAME   = "session.json"

_SESSION_PATH = os.path.join(_ROOT, SESSION_FILENAME)


# ══════════════════════════════════════════════════════════════════════
#  AuthManager
# ══════════════════════════════════════════════════════════════════════

class AuthManager:
    """
    Singleton — ใช้ AuthManager.get_instance() เสมอ

    Public API:
        login(email, password)          → (bool, user_dict | error_str)
        signup(name, email, password)   → (bool, user_dict | error_str)
        send_reset_code(email)          → (smtp_ok: bool, code: str)
        verify_reset_code(email, code)  → bool
        mark_code_used(email)
        update_password(email, new_pw)  → bool
        is_valid_email(email)           → bool
        user_exists(email)              → bool
        save_session(email)
        load_session()                  → str | None
        clear_session()
    """

    _instance: Optional["AuthManager"] = None

    @classmethod
    def get_instance(cls) -> "AuthManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self.db = DatabaseManager.get_instance()

    # ── Login / Signup ────────────────────────────────────────────
    def login(self, email: str, password: str
              ) -> Tuple[bool, Union[dict, str]]:
        user = User.find_by_email(email)
        if user is None:
            return False, "account_not_found"
        if not user.check_password(password):
            return False, "wrong_password"
        return True, user.to_dict()

    def signup(self, name: str, email: str, password: str
               ) -> Tuple[bool, Union[dict, str]]:
        if User.find_by_email(email):
            return False, "email_exists"
        user = User.create(name, email, password)
        if user is None:
            return False, "db_error"
        return True, user.to_dict()

    # ── Forgot Password — OTP Flow ────────────────────────────────
    def send_reset_code(self, email: str) -> Tuple[bool, str]:
        code       = "".join(random.choices(string.digits, k=6))
        expires_at = (datetime.now() + timedelta(minutes=RESET_CODE_EXPIRE)).isoformat()
        self.db.save_reset_token(email, code, expires_at)

        if self._smtp_configured():
            thread = threading.Thread(
                target=self._send_otp_email, args=(email, code), daemon=True
            )
            thread.start()
            return True, code
        return False, code   # dev mode

    def verify_reset_code(self, email: str, code: str) -> bool:
        row = self.db.get_reset_token(email)
        if not row:
            return False
        try:
            if datetime.fromisoformat(row["expires_at"]) < datetime.now():
                return False
        except ValueError:
            return False
        return str(row["token"]) == str(code).strip()

    def mark_code_used(self, email: str) -> None:
        self.db.mark_token_used(email)

    def update_password(self, email: str, new_password: str) -> bool:
        return User.update_password(email, new_password)

    # ── Validation ────────────────────────────────────────────────
    @staticmethod
    def is_valid_email(email: str) -> bool:
        import re
        return bool(re.match(r"[^@]+@[^@]+\.[^@]+", email.strip()))

    def user_exists(self, email: str) -> bool:
        return User.find_by_email(email) is not None

    def find_user(self, email: str) -> Optional[dict]:
        user = User.find_by_email(email)
        return user.to_dict() if user else None

    # ── Session Management ────────────────────────────────────────
    def save_session(self, email: str) -> None:
        with open(_SESSION_PATH, "w", encoding="utf-8") as f:
            json.dump({"email": email.strip().lower()}, f)

    def load_session(self) -> Optional[str]:
        if not os.path.exists(_SESSION_PATH):
            return None
        try:
            with open(_SESSION_PATH, "r", encoding="utf-8") as f:
                return json.load(f).get("email")
        except (json.JSONDecodeError, OSError):
            return None

    def clear_session(self) -> None:
        try:
            if os.path.exists(_SESSION_PATH):
                os.remove(_SESSION_PATH)
        except OSError:
            pass

    # ── Private — Email ───────────────────────────────────────────
    def _smtp_configured(self) -> bool:
        return bool(SMTP_USER and SMTP_PASS)

    def _send_otp_email(self, to: str, code: str) -> None:
        try:
            body_html = f"""
            <div style="font-family:'Segoe UI',Arial,sans-serif;
                        max-width:480px;margin:0 auto;padding:32px;
                        background:#f8fafc;border-radius:16px;">
              <div style="text-align:center;margin-bottom:24px;">
                <span style="font-size:36px;">🛡️</span>
                <h2 style="color:#1e293b;margin:8px 0 4px;">RiskTrack</h2>
                <p style="color:#94a3b8;font-size:13px;margin:0;">Password Reset</p>
              </div>
              <div style="background:white;border-radius:12px;
                          padding:28px;border:1px solid #e2e8f0;text-align:center;">
                <p style="color:#475569;font-size:14px;margin:0 0 20px;">
                  Your verification code is:
                </p>
                <div style="font-size:40px;font-weight:900;letter-spacing:12px;
                            color:#4f46e5;background:#eef2ff;padding:16px 24px;
                            border-radius:10px;display:inline-block;">
                  {code}
                </div>
                <p style="color:#94a3b8;font-size:12px;margin:20px 0 0;">
                  ⏱&nbsp; Expires in <strong>{RESET_CODE_EXPIRE} minutes</strong>.<br>
                  If you did not request this, please ignore this email.
                </p>
              </div>
            </div>
            """
            msg            = MIMEMultipart("alternative")
            msg["Subject"] = "RiskTrack — Your Password Reset Code"
            msg["From"]    = SMTP_USER
            msg["To"]      = to
            msg.attach(MIMEText(body_html, "html", "utf-8"))

            if SMTP_PORT == 465:
                import ssl as _ssl
                ctx = _ssl.create_default_context()
                with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx, timeout=15) as srv:
                    srv.login(SMTP_USER, SMTP_PASS)
                    srv.sendmail(SMTP_USER, to, msg.as_string())
            else:
                with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as srv:
                    srv.ehlo(); srv.starttls()
                    srv.login(SMTP_USER, SMTP_PASS)
                    srv.sendmail(SMTP_USER, to, msg.as_string())
        except Exception:
            pass  # silently fail — OTP ยังอยู่ใน JSON ผู้ใช้ใช้ dev mode ได้


# ══════════════════════════════════════════════════════════════════════
#  AuthWindow  (เดิมอยู่ใน Auth_UI.py)
# ══════════════════════════════════════════════════════════════════════

class AuthWindow(QWidget):
    """
    Self-contained auth widget (Login ↔ Sign Up)
    emit auth_complete(dict) เมื่อ login/signup สำเร็จ

    Import:
        from auth_manager import AuthWindow
    """

    auth_complete = Signal(dict)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._auth = AuthManager.get_instance()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._stack = QStackedWidget()

        # ── import ที่นี่เพื่อหลีกเลี่ยง circular import ────────
        from login_page  import LoginPage
        from signup_page import SignUpPage
        from ui_components import BasePopup

        self.login_page  = LoginPage()
        self.signup_page = SignUpPage()
        self._BasePopup  = BasePopup

        self._stack.addWidget(self.login_page)   # index 0
        self._stack.addWidget(self.signup_page)  # index 1
        layout.addWidget(self._stack)

        # Navigation
        self.login_page.go_signup.connect(lambda: self._stack.setCurrentIndex(1))
        self.signup_page.go_login.connect(lambda: self._stack.setCurrentIndex(0))

        # Auth results
        self.login_page.login_success.connect(self._on_auth)
        self.signup_page.signup_success.connect(self._on_signup)

    def _on_auth(self, user: dict) -> None:
        self.auth_complete.emit(user)

    def _on_signup(self, user: dict) -> None:
        self._BasePopup(
            self, "✅", "Account Created!",
            f"Welcome, {user['name']}!\n"
            "Your account has been created successfully.",
            ok_text="OK", show_cancel=False
        ).exec()
        self.login_page.clear_fields()
        self._stack.setCurrentIndex(0)

    def reset_to_login(self) -> None:
        """Return to login screen (called on logout)"""
        self.login_page.clear_fields()
        self._stack.setCurrentIndex(0)