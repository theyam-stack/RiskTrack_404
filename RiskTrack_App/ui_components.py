"""
ui_components.py — Shared PySide6 UI Components
═════════════════════════════════════════════════
รวมมาจาก ui_helpers.py

ทุก widget / helper ที่ใช้ร่วมกัน:
  BasePage, GradientBG, BasePopup, OTPDialog,
  NewPasswordDialog, PasswordUpdatedDialog,
  CustomCheckBox, make_input, gradient_btn,
  ghost_btn, link_btn, field_label, shadow
"""

import sys
import os

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from PySide6.QtWidgets import (
    QWidget, QDialog, QFrame, QLabel, QPushButton, QLineEdit,
    QVBoxLayout, QHBoxLayout, QCheckBox, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QByteArray, QSize, QRect, QPoint
from PySide6.QtGui  import (
    QColor, QPainter, QLinearGradient, QIcon, QPixmap,
    QPen, QFont, QBrush
)
from PySide6.QtSvg  import QSvgRenderer


# ── Constants ──────────────────────────────────────────────────────
CARD_STYLE = "QFrame#card { background: white; border-radius: 20px; }"

EYE_OPEN_SVG = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"
  fill="none" stroke="#94a3b8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
  <circle cx="12" cy="12" r="3"/>
</svg>"""

EYE_CLOSED_SVG = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"
  fill="none" stroke="#94a3b8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
  <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
  <line x1="1" y1="1" x2="23" y2="23"/>
</svg>"""


# ── Shadow effect ──────────────────────────────────────────────────
def shadow(w: QWidget) -> None:
    s = QGraphicsDropShadowEffect(w)
    s.setBlurRadius(40)
    s.setOffset(0, 8)
    s.setColor(QColor(0, 0, 0, 35))
    w.setGraphicsEffect(s)


# ── Label helpers ──────────────────────────────────────────────────
def field_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet("font-size:12px; font-weight:600; color:#475569;")
    return lbl


# ── Eye toggle button ──────────────────────────────────────────────
def _make_eye_btn(line_edit: QLineEdit) -> QPushButton:
    btn = QPushButton()
    btn.setFixedSize(28, 28)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setCheckable(True)
    btn.setStyleSheet("""
        QPushButton { border:none; background:transparent; border-radius:6px; padding:3px; }
        QPushButton:hover   { background:#f1f5f9; }
        QPushButton:checked { background:#ede9fe; }
    """)

    def _svg_icon(svg_bytes: bytes) -> QIcon:
        renderer = QSvgRenderer(QByteArray(svg_bytes))
        pm = QPixmap(22, 22)
        pm.fill(Qt.transparent)
        painter = QPainter(pm)
        renderer.render(painter)
        painter.end()
        return QIcon(pm)

    icon_open   = _svg_icon(EYE_OPEN_SVG)
    icon_closed = _svg_icon(EYE_CLOSED_SVG)
    btn.setIcon(icon_open)
    btn.setIconSize(QSize(18, 18))

    def toggle(checked: bool) -> None:
        line_edit.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)
        btn.setIcon(icon_closed if checked else icon_open)

    btn.clicked.connect(toggle)
    return btn


# ── Input widget ───────────────────────────────────────────────────
def make_input(placeholder: str, password: bool = False,
               icon: str = "") -> tuple:
    """Returns (container_frame, QLineEdit)"""
    wrap = QFrame()
    wrap.setFixedHeight(44)
    wrap.setObjectName("inp")
    wrap.setStyleSheet(
        "QFrame#inp { background:white; border:1.5px solid #e2e8f0; border-radius:10px; }"
    )
    row = QHBoxLayout(wrap)
    row.setContentsMargins(12, 0, 10, 0)
    row.setSpacing(6)

    if icon:
        ic = QLabel(icon)
        ic.setStyleSheet(
            "color:#94a3b8; font-size:13px; background:transparent; border:none;"
        )
        row.addWidget(ic)

    inp = QLineEdit()
    inp.setPlaceholderText(placeholder)
    if password:
        inp.setEchoMode(QLineEdit.Password)
    inp.setStyleSheet(
        "QLineEdit { border:none; background:transparent; font-size:13px; color:#334155; }"
    )
    row.addWidget(inp, 1)

    if password:
        row.addWidget(_make_eye_btn(inp))

    return wrap, inp


# ── Button styles ──────────────────────────────────────────────────
def gradient_btn(text: str, h: int = 46) -> QPushButton:
    b = QPushButton(text)
    b.setFixedHeight(h)
    b.setCursor(Qt.PointingHandCursor)
    b.setStyleSheet("""
        QPushButton {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 #6C63FF, stop:1 #4F8EF7);
            color:white; border:none; border-radius:11px;
            font-size:14px; font-weight:700;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 #5550e8, stop:1 #3b7de0);
        }
    """)
    return b


def ghost_btn(text: str, h: int = 38) -> QPushButton:
    b = QPushButton(text)
    b.setFixedHeight(h)
    b.setCursor(Qt.PointingHandCursor)
    b.setStyleSheet("""
        QPushButton {
            background:white; color:#64748b;
            border:1.5px solid #e2e8f0;
            border-radius:9px; font-size:13px; font-weight:600;
        }
        QPushButton:hover { border-color:#94a3b8; color:#334155; }
    """)
    return b


def link_btn(text: str) -> QPushButton:
    b = QPushButton(text)
    b.setCursor(Qt.PointingHandCursor)
    b.setStyleSheet("""
        QPushButton { border:none; background:transparent;
            color:#4f46e5; font-size:12px; font-weight:700; }
        QPushButton:hover { color:#3730a3; }
    """)
    return b


# ── Custom Checkbox ────────────────────────────────────────────────
class CustomCheckBox(QCheckBox):
    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(text, parent)
        self.setStyleSheet("QCheckBox { spacing: 0px; }")
        self.setCursor(Qt.PointingHandCursor)

    def sizeHint(self) -> QSize:
        sh = super().sizeHint()
        return QSize(sh.width() + 4, max(sh.height(), 22))

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        BOX = 16
        y    = (self.height() - BOX) // 2
        rect = QRect(0, y, BOX, BOX)

        if self.isChecked():
            p.setBrush(QColor("#4f46e5"))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(rect, 4, 4)
            pen = QPen(QColor("white"), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawPolyline([QPoint(3, y + 8), QPoint(6, y + 11), QPoint(13, y + 5)])
        else:
            p.setBrush(QColor("white"))
            p.setPen(QPen(QColor("#cbd5e1"), 1.5))
            p.drawRoundedRect(rect, 4, 4)

        if self.text():
            p.setPen(QColor("#64748b"))
            p.setFont(self.font())
            fm = p.fontMetrics()
            tx = BOX + 8
            ty = (self.height() + fm.ascent() - fm.descent()) // 2
            p.drawText(tx, ty, self.text())


# ── Gradient Background ────────────────────────────────────────────
class GradientBG(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, False)

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        g = QLinearGradient(0, 0, self.width(), self.height())
        g.setColorAt(0.0,  QColor("#a78bfa"))
        g.setColorAt(0.45, QColor("#6C63FF"))
        g.setColorAt(1.0,  QColor("#4F8EF7"))
        p.fillRect(self.rect(), g)


# ── Base Page (gradient BG + centered card) ────────────────────────
class BasePage(QWidget):
    def __init__(self, card_width: int = 380) -> None:
        super().__init__()
        self._bg = GradientBG(self)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addStretch(1)

        mid = QHBoxLayout()
        mid.addStretch(1)
        self._card = QFrame()
        self._card.setObjectName("card")
        self._card.setFixedWidth(card_width)
        self._card.setStyleSheet(CARD_STYLE)
        shadow(self._card)

        self._cl = QVBoxLayout(self._card)
        self._cl.setContentsMargins(36, 34, 36, 34)
        self._cl.setSpacing(0)

        mid.addWidget(self._card, 0, Qt.AlignVCenter)
        mid.addStretch(1)
        outer.addLayout(mid)
        outer.addStretch(1)

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        self._bg.setGeometry(self.rect())


# ── Base Popup Dialog ──────────────────────────────────────────────
class BasePopup(QDialog):
    def __init__(self, parent, icon_txt: str, title: str, sub: str,
                 show_input: bool = False, input_ph: str = "",
                 input_pw: bool = False,
                 ok_text: str = "OK", cancel_text: str = "Cancel",
                 show_cancel: bool = True, ok_color: str = "#4f46e5",
                 width: int = 340) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        self._inp = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)

        card = QFrame()
        card.setObjectName("pc")
        card.setFixedWidth(width)
        card.setStyleSheet("QFrame#pc { background:white; border-radius:16px; }")
        shadow(card)
        outer.addWidget(card)

        cl = QVBoxLayout(card)
        cl.setContentsMargins(28, 22, 28, 22)
        cl.setSpacing(0)

        xr = QHBoxLayout()
        xr.addStretch()
        xb = QPushButton("✕")
        xb.setFixedSize(22, 22)
        xb.setCursor(Qt.PointingHandCursor)
        xb.setStyleSheet(
            "QPushButton{border:none;background:transparent;color:#94a3b8;font-size:13px;}"
        )
        xb.clicked.connect(self.reject)
        xr.addWidget(xb)
        cl.addLayout(xr)

        ic = QLabel(icon_txt)
        ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet("font-size:30px;")
        cl.addWidget(ic)
        cl.addSpacing(10)

        t = QLabel(title)
        t.setAlignment(Qt.AlignCenter)
        t.setWordWrap(True)
        t.setStyleSheet("font-size:14px; font-weight:800; color:#1e293b;")
        cl.addWidget(t)
        cl.addSpacing(6)

        s = QLabel(sub)
        s.setAlignment(Qt.AlignCenter)
        s.setWordWrap(True)
        s.setStyleSheet("font-size:12px; color:#64748b; line-height:1.5;")
        cl.addWidget(s)
        cl.addSpacing(14)

        if show_input:
            wrap, self._inp = make_input(
                input_ph, password=input_pw, icon="🔒" if input_pw else ""
            )
            cl.addWidget(wrap)
            cl.addSpacing(6)
            self._err = QLabel()
            self._err.setStyleSheet("font-size:11px;color:#ef4444;")
            self._err.hide()
            cl.addWidget(self._err)
            cl.addSpacing(8)

            if input_pw:
                fp = link_btn("Forgot password")
                fp.setStyleSheet(
                    "QPushButton{border:none;background:transparent;"
                    "color:#4f46e5;font-size:11px;font-weight:600;}"
                )
                cl.addWidget(fp)
                cl.addSpacing(8)

        br = QHBoxLayout()
        br.setSpacing(10)
        if show_cancel:
            cb = ghost_btn(cancel_text)
            cb.clicked.connect(self.reject)
            br.addWidget(cb)

        ok = QPushButton(ok_text)
        ok.setFixedHeight(38)
        ok.setCursor(Qt.PointingHandCursor)
        ok.setStyleSheet(f"""
            QPushButton {{ background:{ok_color}; color:white; border:none;
                border-radius:9px; font-size:13px; font-weight:700; }}
            QPushButton:hover {{ background:#3730a3; }}
        """)
        ok.clicked.connect(self.accept)
        br.addWidget(ok)
        cl.addLayout(br)

    def input_value(self) -> str:
        return self._inp.text() if self._inp else ""

    def show_error(self, msg: str) -> None:
        if hasattr(self, "_err"):
            self._err.setText(msg)
            self._err.show()


# ── OTP Dialog ─────────────────────────────────────────────────────
class OTPDialog(QDialog):
    def __init__(self, parent, email: str = "", verify_fn=None) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        self._verify_fn = verify_fn
        self.boxes = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)

        card = QFrame()
        card.setObjectName("pc2")
        card.setFixedWidth(340)
        card.setStyleSheet("QFrame#pc2{background:white;border-radius:16px;}")
        shadow(card)
        outer.addWidget(card)

        cl = QVBoxLayout(card)
        cl.setContentsMargins(28, 22, 28, 22)
        cl.setSpacing(0)

        xr = QHBoxLayout()
        xr.addStretch()
        xb = QPushButton("✕")
        xb.setFixedSize(22, 22)
        xb.setCursor(Qt.PointingHandCursor)
        xb.setStyleSheet(
            "QPushButton{border:none;background:transparent;color:#94a3b8;font-size:13px;}"
        )
        xb.clicked.connect(self.reject)
        xr.addWidget(xb)
        cl.addLayout(xr)

        ic = QLabel("✉️")
        ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet("font-size:28px;")
        cl.addWidget(ic)
        cl.addSpacing(8)

        t = QLabel("Verification Code")
        t.setAlignment(Qt.AlignCenter)
        t.setStyleSheet("font-size:15px;font-weight:800;color:#1e293b;")
        cl.addWidget(t)
        cl.addSpacing(4)

        s1 = QLabel("Code sent to")
        s1.setAlignment(Qt.AlignCenter)
        s1.setStyleSheet("font-size:12px;color:#64748b;")
        cl.addWidget(s1)

        s2 = QLabel(email or "your email")
        s2.setAlignment(Qt.AlignCenter)
        s2.setStyleSheet("font-size:12px;font-weight:600;color:#334155;")
        cl.addWidget(s2)
        cl.addSpacing(16)

        otp_row = QHBoxLayout()
        otp_row.setSpacing(8)
        otp_row.setAlignment(Qt.AlignCenter)
        for i in range(6):
            b = QLineEdit()
            b.setFixedSize(40, 44)
            b.setAlignment(Qt.AlignCenter)
            b.setMaxLength(1)
            b.setStyleSheet("""
                QLineEdit { border:1.5px solid #e2e8f0; border-radius:9px;
                    font-size:18px; font-weight:700;
                    color:#1e293b; background:white; }
                QLineEdit:focus { border-color:#4f46e5; }
            """)
            b.textChanged.connect(lambda txt, idx=i: self._jump(idx, txt))
            otp_row.addWidget(b)
            self.boxes.append(b)
        cl.addLayout(otp_row)
        cl.addSpacing(8)

        self._err_lbl = QLabel("")
        self._err_lbl.setAlignment(Qt.AlignCenter)
        self._err_lbl.setStyleSheet("font-size:11px;color:#ef4444;")
        self._err_lbl.hide()
        cl.addWidget(self._err_lbl)
        cl.addSpacing(4)

        rr = QHBoxLayout()
        rr.setAlignment(Qt.AlignCenter)
        rl = QLabel("Did not receive the code?")
        rl.setStyleSheet("font-size:11px;color:#64748b;")
        rr.addWidget(rl)
        rb = link_btn("Resend")
        rr.addWidget(rb)
        cl.addLayout(rr)
        cl.addSpacing(16)

        br = QHBoxLayout()
        br.setSpacing(10)
        cb = ghost_btn("Cancel")
        cb.clicked.connect(self.reject)
        br.addWidget(cb)

        vb = QPushButton("Verify")
        vb.setFixedHeight(38)
        vb.setCursor(Qt.PointingHandCursor)
        vb.setStyleSheet(
            "QPushButton{background:#4f46e5;color:white;border:none;"
            "border-radius:9px;font-size:13px;font-weight:700;}"
            "QPushButton:hover{background:#3730a3;}"
        )
        vb.clicked.connect(self._on_verify)
        br.addWidget(vb)
        cl.addLayout(br)

    def _jump(self, idx: int, txt: str) -> None:
        if txt and idx < 5:
            self.boxes[idx + 1].setFocus()

    def _on_verify(self) -> None:
        code = self.get_code()
        if len(code) < 6:
            self._show_error("Please enter all 6 digits.")
            return
        if self._verify_fn and not self._verify_fn(code):
            self._show_error("Invalid or expired code. Please try again.")
            for box in self.boxes:
                box.clear()
            self.boxes[0].setFocus()
            return
        self.accept()

    def _show_error(self, msg: str) -> None:
        self._err_lbl.setText(msg)
        self._err_lbl.show()

    def get_code(self) -> str:
        return "".join(b.text() for b in self.boxes)


# ── New Password Dialog ────────────────────────────────────────────
class NewPasswordDialog(QDialog):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)

        card = QFrame()
        card.setObjectName("pc3")
        card.setFixedWidth(340)
        card.setStyleSheet("QFrame#pc3{background:white;border-radius:16px;}")
        shadow(card)
        outer.addWidget(card)

        cl = QVBoxLayout(card)
        cl.setContentsMargins(28, 22, 28, 22)
        cl.setSpacing(0)

        xr = QHBoxLayout()
        xr.addStretch()
        xb = QPushButton("✕")
        xb.setFixedSize(22, 22)
        xb.setCursor(Qt.PointingHandCursor)
        xb.setStyleSheet(
            "QPushButton{border:none;background:transparent;color:#94a3b8;font-size:13px;}"
        )
        xb.clicked.connect(self.reject)
        xr.addWidget(xb)
        cl.addLayout(xr)

        ic = QLabel("🔐")
        ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet("font-size:28px;")
        cl.addWidget(ic)
        cl.addSpacing(8)

        t = QLabel("Forgot Password")
        t.setAlignment(Qt.AlignCenter)
        t.setStyleSheet("font-size:15px;font-weight:800;color:#1e293b;")
        cl.addWidget(t)

        s = QLabel("Set a new password for your account")
        s.setAlignment(Qt.AlignCenter)
        s.setStyleSheet("font-size:12px;color:#64748b;padding:4px 0 14px;")
        cl.addWidget(s)

        cl.addWidget(field_label("New Password"))
        cl.addSpacing(5)
        pw_f, self.pw = make_input("Enter new password", password=True, icon="🔒")
        cl.addWidget(pw_f)
        cl.addSpacing(12)

        cl.addWidget(field_label("Confirm Password"))
        cl.addSpacing(5)
        cp_f, self.cpw = make_input("Confirm new password", password=True, icon="🔒")
        cl.addWidget(cp_f)
        cl.addSpacing(16)

        br = QHBoxLayout()
        br.setSpacing(10)
        cb = ghost_btn("Cancel")
        cb.clicked.connect(self.reject)
        br.addWidget(cb)
        ok = QPushButton("OK")
        ok.setFixedHeight(38)
        ok.setCursor(Qt.PointingHandCursor)
        ok.setStyleSheet(
            "QPushButton{background:#4f46e5;color:white;border:none;"
            "border-radius:9px;font-size:13px;font-weight:700;}"
            "QPushButton:hover{background:#3730a3;}"
        )
        ok.clicked.connect(self._validate)
        br.addWidget(ok)
        cl.addLayout(br)

    def _validate(self) -> None:
        pw, cpw = self.pw.text(), self.cpw.text()
        if not pw:
            BasePopup(self, "⚠️", "Password Required", "Please enter a new password.",
                      ok_text="OK", show_cancel=False).exec()
            return
        if len(pw) < 6:
            BasePopup(self, "⚠️", "Password Too Short",
                      "Password must be at least 6 characters.",
                      ok_text="OK", show_cancel=False).exec()
            return
        if pw != cpw:
            BasePopup(self, "⚠️", "Passwords Do Not Match",
                      "Please make sure both passwords are identical.",
                      ok_text="OK", show_cancel=False).exec()
            return
        self.accept()

    def get_passwords(self) -> tuple:
        return self.pw.text(), self.cpw.text()


# ── Password Updated Dialog ────────────────────────────────────────
class PasswordUpdatedDialog(QDialog):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)

        card = QFrame()
        card.setObjectName("pc4")
        card.setFixedWidth(320)
        card.setStyleSheet("QFrame#pc4{background:white;border-radius:16px;}")
        shadow(card)
        outer.addWidget(card)

        cl = QVBoxLayout(card)
        cl.setContentsMargins(32, 30, 32, 30)
        cl.setSpacing(0)

        ic = QLabel("✅")
        ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet("font-size:36px;")
        cl.addWidget(ic)
        cl.addSpacing(12)

        t = QLabel("Password Updated\nSuccessfully!")
        t.setAlignment(Qt.AlignCenter)
        t.setWordWrap(True)
        t.setStyleSheet("font-size:16px;font-weight:800;color:#1e293b;line-height:1.4;")
        cl.addWidget(t)
        cl.addSpacing(8)

        s = QLabel(
            "Your password has been successfully reset.\n"
            "You may now sign in with your new credentials."
        )
        s.setAlignment(Qt.AlignCenter)
        s.setWordWrap(True)
        s.setStyleSheet("font-size:12px;color:#64748b;line-height:1.5;")
        cl.addWidget(s)
        cl.addSpacing(20)

        rb = QPushButton("Return to Sign In")
        rb.setFixedHeight(42)
        rb.setCursor(Qt.PointingHandCursor)
        rb.setStyleSheet(
            "QPushButton{background:#4f46e5;color:white;border:none;"
            "border-radius:10px;font-size:13px;font-weight:700;}"
            "QPushButton:hover{background:#3730a3;}"
        )
        rb.clicked.connect(self.accept)
        cl.addWidget(rb)