"""
signup_page.py — Sign Up Page Widget
"""

import sys
import os

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QHBoxLayout
from PySide6.QtCore    import Qt, Signal

from auth_manager  import AuthManager
from ui_components import (
    BasePage, BasePopup, CustomCheckBox,
    make_input, gradient_btn, link_btn, field_label
)

class SignUpPage(BasePage):
    """
    Signals
    -------
    go_login       — navigate to Login page
    signup_success — emits user dict on successful sign up
    """

    go_login       = Signal()
    signup_success = Signal(dict)

    def __init__(self) -> None:
        super().__init__(420)
        self._auth = AuthManager.get_instance()
        self._build_ui()

    # ── Build ─────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        cl = self._cl

        # Back button
        br = QHBoxLayout()
        self._btn_back = QPushButton("← Back")
        self._btn_back.setCursor(Qt.PointingHandCursor)
        self._btn_back.setStyleSheet(
            "QPushButton { border:none; background:transparent; "
            "color:#4f46e5; font-size:13px; font-weight:1000; } "
            "QPushButton:hover { color:#3730a3; }"
        )
        br.addWidget(self._btn_back)
        br.addStretch()
        cl.addLayout(br)
        cl.addSpacing(8)

        ttl = QLabel("Create your account")
        ttl.setAlignment(Qt.AlignCenter)
        ttl.setStyleSheet("font-size:20px;font-weight:800;color:#1e293b;")
        cl.addWidget(ttl)

        sub = QLabel("Join us and start managing project risks effectively.")
        sub.setAlignment(Qt.AlignCenter)
        sub.setWordWrap(True)
        sub.setStyleSheet("font-size:12px;color:#94a3b8;padding:4px 0 18px;")
        cl.addWidget(sub)

        # Full Name
        cl.addWidget(field_label("Full Name"))
        cl.addSpacing(5)
        fn_f, self._fn = make_input("Wednesday Adams", icon="👤")
        cl.addWidget(fn_f)
        cl.addSpacing(12)

        # Email
        cl.addWidget(field_label("Email Address"))
        cl.addSpacing(5)
        em_f, self._em = make_input("name@company.com", icon="✉")
        cl.addWidget(em_f)
        cl.addSpacing(12)

        # Password
        cl.addWidget(field_label("Password"))
        cl.addSpacing(5)
        pw_f, self._pw = make_input("••••••••", password=True, icon="🔒")
        cl.addWidget(pw_f)
        cl.addSpacing(12)

        # Confirm Password
        cl.addWidget(field_label("Confirm Password"))
        cl.addSpacing(5)
        cp_f, self._cpw = make_input("••••••••", password=True, icon="🔒")
        cl.addWidget(cp_f)
        cl.addSpacing(14)

        # Terms checkbox
        tr = QHBoxLayout()
        tr.setSpacing(6)
        tr.setAlignment(Qt.AlignTop)
        self._chk = CustomCheckBox()
        tl = QLabel(
            'I agree to the '
            '<a href="#" style="color:#4f46e5;font-weight:600;">'
            'Terms of Service</a>'
            ' and <a href="#" style="color:#4f46e5;font-weight:600;">'
            'Privacy Policy</a>.'
        )
        tl.setOpenExternalLinks(False)
        tl.setWordWrap(True)
        tl.setStyleSheet("font-size:11px;color:#64748b;")
        tr.addWidget(self._chk, 0, Qt.AlignTop)
        tr.addWidget(tl, 1)
        cl.addLayout(tr)
        cl.addSpacing(18)

        # Sign up button
        self._btn_create = gradient_btn("Sign up →")
        cl.addWidget(self._btn_create)
        cl.addSpacing(14)

        # Sign-in link
        sr = QHBoxLayout()
        sr.setAlignment(Qt.AlignCenter)
        al = QLabel("Already have an account?")
        al.setStyleSheet("font-size:12px;color:#94a3b8;")
        self._btn_signin = QPushButton("Sign In")
        self._btn_signin.setCursor(Qt.PointingHandCursor)
        self._btn_signin.setStyleSheet(
            "QPushButton { border:none; background:transparent; "
            "color:#4f46e5; font-size:12px; font-weight:700; } "
            "QPushButton:hover { color:#3730a3; }"
        )
        sr.addWidget(al)
        sr.addWidget(self._btn_signin)
        cl.addLayout(sr)

        # Connections
        self._btn_back.clicked.connect(self._navigate_to_login)
        self._btn_signin.clicked.connect(self._navigate_to_login)
        self._btn_create.clicked.connect(self._do_signup)

    # ── Navigate away ─────────────────────────────────────────────
    def _navigate_to_login(self) -> None:
        self.clear_fields()
        self.go_login.emit()

    # ── Signup Logic ──────────────────────────────────────────────
    def _do_signup(self) -> None:
        fn  = self._fn.text().strip()
        em  = self._em.text().strip()
        pw  = self._pw.text()
        cpw = self._cpw.text()

        if not fn or not em or not pw or not cpw:
            BasePopup(self, "⚠️", "Missing Information",
                      "All fields are required to create an account.",
                      ok_text="OK", show_cancel=False).exec()
            return

        if not self._auth.is_valid_email(em):
            BasePopup(self, "⚠️", "Invalid Email Address",
                      "Please enter a valid email to continue.",
                      ok_text="OK", show_cancel=False).exec()
            return

        if len(pw) < 6:
            BasePopup(self, "⚠️", "Password Too Short",
                      "Password must be at least 6 characters long.",
                      ok_text="OK", show_cancel=False).exec()
            return

        if pw != cpw:
            BasePopup(self, "⚠️", "Passwords Do Not Match",
                      "Please make sure both passwords are identical.",
                      ok_text="OK", show_cancel=False).exec()
            return

        if not self._chk.isChecked():
            BasePopup(self, "⚠️", "Terms & Conditions",
                      "Please agree to the Terms of Service and Privacy Policy.",
                      ok_text="OK", show_cancel=False).exec()
            return

        success, result = self._auth.signup(fn, em, pw)
        if not success:
            if result == "email_exists":
                BasePopup(self, "⚠️", "Email Already Registered",
                          "An account with this email already exists.\n"
                          "Please sign in instead.",
                          ok_text="OK", show_cancel=False).exec()
            else:
                BasePopup(self, "❌", "Registration Failed",
                          "Something went wrong. Please try again.",
                          ok_text="OK", show_cancel=False).exec()
            return

        self.clear_fields()
        self.signup_success.emit(result)

    # ── Public ────────────────────────────────────────────────────
    def clear_fields(self) -> None:
        self._fn.clear()
        self._em.clear()
        self._pw.clear()
        self._cpw.clear()
        self._chk.setChecked(False)