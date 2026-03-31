"""
login_page.py — Login Page Widget
════════════════════════════════════════
Forgot-password flow ส่ง OTP จริงผ่าน SMTP (config.py)
ถ้า SMTP ยังไม่ตั้งค่า → แสดง dev-mode popup พร้อม code
"""

import sys
import os

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from PySide6.QtWidgets import QLabel, QPushButton, QDialog, QVBoxLayout, QHBoxLayout
from PySide6.QtCore    import Qt, Signal

from auth_manager  import AuthManager
from ui_components import (
    BasePage, BasePopup, OTPDialog, NewPasswordDialog, PasswordUpdatedDialog,
    CustomCheckBox, make_input, gradient_btn, link_btn, field_label
)


class LoginPage(BasePage):
    """
    Signals
    -------
    go_signup     — navigate to Sign Up page
    login_success — emits user dict on successful login
    """

    go_signup     = Signal()
    login_success = Signal(dict)

    def __init__(self) -> None:
        super().__init__(380)
        self._auth = AuthManager.get_instance()
        self._build_ui()

    # ── Build ─────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        cl = self._cl

        # Logo
        logo = QLabel("R")
        logo.setFixedSize(46, 46)
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet("""
            background:qlineargradient(x1:0,y1:0,x2:1,y2:1,
                stop:0 #6C63FF, stop:1 #4F8EF7);
            border-radius:13px; color:white;
            font-size:20px; font-weight:900;
        """)
        lr = QHBoxLayout()
        lr.setAlignment(Qt.AlignCenter)
        lr.addWidget(logo)
        cl.addLayout(lr)
        cl.addSpacing(14)

        ttl = QLabel("RiskTrack")
        ttl.setAlignment(Qt.AlignCenter)
        ttl.setStyleSheet("font-size:22px;font-weight:800;color:#1e293b;")
        cl.addWidget(ttl)

        sub = QLabel("Welcome back")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("font-size:13px;color:#94a3b8;")
        cl.addWidget(sub)
        cl.addSpacing(24)

        # Email
        cl.addWidget(field_label("Email Address"))
        cl.addSpacing(6)
        ef, self._email = make_input("name@company.com", icon="✉")
        cl.addWidget(ef)
        cl.addSpacing(14)

        # Password + forgot link
        phr = QHBoxLayout()
        phr.addWidget(field_label("Password"))
        phr.addStretch()
        self._btn_forgot = link_btn("Forgot password?")
        phr.addWidget(self._btn_forgot)
        cl.addLayout(phr)
        cl.addSpacing(6)
        pf, self._pw = make_input("••••••••", password=True, icon="🔒")
        cl.addWidget(pf)
        cl.addSpacing(12)

        # Remember me
        kr = QHBoxLayout()
        kr.setSpacing(8)
        self._chk = CustomCheckBox("Keep me log in")
        kr.addWidget(self._chk)
        cl.addLayout(kr)
        cl.addSpacing(20)

        # Login button
        self._btn_login = gradient_btn("Log In →")
        cl.addWidget(self._btn_login)
        cl.addSpacing(16)

        # Sign-up link
        sr = QHBoxLayout()
        sr.setAlignment(Qt.AlignCenter)
        dn = QLabel("Don't have an account? ")
        dn.setStyleSheet("font-size:12px;color:#94a3b8;")
        self._btn_signup = link_btn("Sign up")
        sr.addWidget(dn)
        sr.addWidget(self._btn_signup)
        cl.addLayout(sr)

        # Connections
        self._btn_login.clicked.connect(self._do_login)
        self._btn_signup.clicked.connect(self.go_signup)
        self._btn_forgot.clicked.connect(self._do_forgot)

    # ── Login Logic ───────────────────────────────────────────────
    def _do_login(self) -> None:
        em = self._email.text().strip()
        pw = self._pw.text()

        if not em or not pw:
            lines = []
            if not em: lines.append("• Email address is required")
            if not pw: lines.append("• Password must not be empty")
            BasePopup(self, "⚠️", "Missing Credentials",
                      "\n".join(lines), ok_text="OK", show_cancel=False).exec()
            return

        if not self._auth.is_valid_email(em):
            dlg = BasePopup(self, "⚠️", "Invalid Email Address",
                            "Please enter a valid email to continue.",
                            show_input=True, input_ph="email@example.com",
                            ok_text="Retry", ok_color="#4f46e5")
            if dlg.exec() == QDialog.Accepted and dlg.input_value():
                self._email.setText(dlg.input_value())
            return

        success, result = self._auth.login(em, pw)

        if not success:
            if result == "account_not_found":
                BasePopup(self, "⚠️", "Account Not Found",
                          "No account is registered with this email address.",
                          ok_text="OK", show_cancel=False).exec()
                return

            if result == "wrong_password":
                dlg = BasePopup(
                    self, "⚠️", "Incorrect Password",
                    "Please re-enter your password to continue.",
                    show_input=True, input_ph="Re-enter your password",
                    input_pw=True, ok_text="Retry", ok_color="#4f46e5"
                )
                if dlg.exec() == QDialog.Accepted:
                    ok2, res2 = self._auth.login(em, dlg.input_value())
                    if ok2:
                        self._finish_login(res2)
                    else:
                        BasePopup(self, "⚠️", "Incorrect Password",
                                  "Password is still incorrect.\n"
                                  "Please use 'Forgot password?' to reset it.",
                                  ok_text="OK", show_cancel=False).exec()
                return

        self._finish_login(result)

    def _finish_login(self, user: dict) -> None:
        if self._chk.isChecked():
            self._auth.save_session(user["email"])
        else:
            self._auth.clear_session()
        self.login_success.emit(user)

    # ── Forgot Password Flow ──────────────────────────────────────
    def _do_forgot(self) -> None:
        s1 = BasePopup(
            self, "🛡️", "Reset Password", "Enter your Email Address",
            show_input=True, input_ph="email@example.com",
            ok_text="Send Code", ok_color="#4f46e5", width=320
        )
        if s1.exec() != QDialog.Accepted:
            return
        email = s1.input_value().strip() or self._email.text().strip()

        if not email or not self._auth.is_valid_email(email):
            BasePopup(self, "⚠️", "Invalid Email",
                      "Please enter a valid email address.",
                      ok_text="OK", show_cancel=False).exec()
            return

        if not self._auth.user_exists(email):
            BasePopup(self, "⚠️", "Account Not Found",
                      "No account is registered with this email address.",
                      ok_text="OK", show_cancel=False).exec()
            return

        smtp_ok, code = self._auth.send_reset_code(email)

        if not smtp_ok:
            BasePopup(
                self, "⚙️", "SMTP Not Configured",
                f"config.py ยังไม่มี SMTP settings\n\n"
                f"🔑  Test Code (dev only):\n\n"
                f"   {code}\n\n"
                f"กรุณาตั้งค่า SMTP_USER / SMTP_PASS ใน config.py\n"
                f"เพื่อส่ง email จริงในระบบ production",
                ok_text="Got it", show_cancel=False, width=360
            ).exec()

        s2 = OTPDialog(
            self, email,
            verify_fn=lambda c: self._auth.verify_reset_code(email, c)
        )
        if s2.exec() != QDialog.Accepted:
            return

        self._auth.mark_code_used(email)

        s3 = NewPasswordDialog(self)
        if s3.exec() != QDialog.Accepted:
            return

        new_pw, _ = s3.get_passwords()
        self._auth.update_password(email, new_pw)
        PasswordUpdatedDialog(self).exec()

    # ── Public ───────────────────────────────────────────────────
    def clear_fields(self) -> None:
        self._email.clear()
        self._pw.clear()
        self._chk.setChecked(False)