import sys
import json
import os
import re
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QFrame, QSizePolicy, QProgressBar,
    QDialog, QLineEdit, QTextEdit, QDateEdit, QStackedWidget, QSlider,
    QGridLayout, QMainWindow, QCalendarWidget, QComboBox, QMessageBox,
    QFileDialog, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal, QDate, QTimer, QRectF, QPoint, QEvent, QSize, QByteArray
from PySide6.QtGui import QFont, QColor, QPainter, QPen, QPixmap, QIcon, QBrush
from PySide6.QtSvg import QSvgRenderer
from datetime import datetime, date, timedelta


# =====================================================================
# DATABASE  —  ไฟล์เดียว (tasks + alerts แยก key)
# =====================================================================
TASK_DB_FILE  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tasks_db.json")
ALERT_DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "risktrack_db.json")
PROFILE_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profile.json")
PROFILE_DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profile_db.json")

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

_CUR_YEAR = datetime.now().year

# =====================================================================
# mock_tasks  — ข้อมูลเริ่มต้น 6 tasks (จากไฟล์ reference)
# =====================================================================
DEFAULT_TASKS = [
    {"id": 1, "name": "#01 User Authentication system",  "tag": "Backend",      "tag_color": "#22c55e", "progress": 78,  "bar": "#ef4444", "status": "In Progress", "status_width": 90, "status_style": "background:#e0e7ff; color:#4f46e5;", "due": "Apr 15", "due_date": "Apr 15 2026", "risk": "Medium",   "risk_color": "#eab308", "risk_bg": "#fefce8"},
    {"id": 2, "name": "#02 Database Schema Design",      "tag": "Architecture", "tag_color": "#22c55e", "progress": 100, "bar": "#22c55e", "status": "Done",        "status_width": 60, "status_style": "background:#dcfce7; color:#16a34a;", "due": "Mar 20", "due_date": "Mar 20 2026", "risk": "Low",      "risk_color": "#22c55e", "risk_bg": "#f0fdf4"},
    {"id": 3, "name": "#03 Risk Calculation Engine",     "tag": "Core Logic",   "tag_color": "#f97316", "progress": 45,  "bar": "#f97316", "status": "In Progress", "status_width": 90, "status_style": "background:#e0e7ff; color:#4f46e5;", "due": "Apr 2",  "due_date": "Apr 2 2026",  "due_color": "#f97316", "due_text_color": "#f97316", "risk": "High",     "risk_color": "#f97316", "risk_bg": "#fff7ed"},
    {"id": 4, "name": "#04 Dashboard UI / Charts",       "tag": "Frontend",     "tag_color": "#ef4444", "progress": 20,  "bar": "#ef4444", "status": "To do",       "status_width": 60, "status_style": "background:#f1f5f9; color:#64748b;", "due": "Apr 1",  "due_date": "Apr 1 2026",  "due_color": "#ef4444", "due_text_color": "#ef4444", "risk": "Critical", "risk_color": "#ef4444", "risk_bg": "#fef2f2"},
    {"id": 5, "name": "#05 Member Assignment Module",    "tag": "Backend",      "tag_color": "#eab308", "progress": 68,  "bar": "#22c55e", "status": "In Progress", "status_width": 90, "status_style": "background:#e0e7ff; color:#4f46e5;", "due": "May 10", "due_date": "May 10 2026", "risk": "Low",      "risk_color": "#22c55e", "risk_bg": "#f0fdf4"},
    {"id": 6, "name": "#06 Alert Notification System",  "tag": "Core Logic",   "tag_color": "#eab308", "progress": 10,  "bar": "#eab308", "status": "To do",       "status_width": 60, "status_style": "background:#f1f5f9; color:#64748b;", "due": "Apr 10", "due_date": "Apr 10 2026", "risk": "High",     "risk_color": "#f97316", "risk_bg": "#fff7ed"},
]

mock_tasks: list[dict] = []

def _current_user_key() -> str:
    """Return a stable per-user key from profile.json."""
    try:
        if os.path.exists(PROFILE_JSON):
            with open(PROFILE_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
            email = str(data.get("email", "") or "").strip().lower()
            if email:
                return email
    except Exception:
        pass
    return "__default__"


def _load_scoped_object(path: str, *, key: str) -> dict:
    """Load a single object for a given user key from {users:{key:{...}}} storage."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("users"), dict):
            obj = data["users"].get(key, {})
            return obj if isinstance(obj, dict) else {}
    except Exception:
        pass
    return {}


def _save_scoped_object(path: str, *, key: str, obj: dict) -> None:
    """Save a single object for a given user key while preserving other users."""
    scoped: dict = {"users": {}}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            if isinstance(existing, dict) and isinstance(existing.get("users"), dict):
                scoped["users"] = existing["users"]
        except Exception:
            pass
    scoped["users"][key] = dict(obj or {})
    with open(path, "w", encoding="utf-8") as f:
        json.dump(scoped, f, ensure_ascii=False, indent=2)


def _load_scoped_records(path: str) -> list[dict]:
    """
    Load records for current user.
    Backward compatible:
      - legacy format: [ ...records... ]
      - scoped format: {"users": {"email@example.com": [ ... ]}}
    """
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            # Legacy format: shared list for all users.
            # Migrate it to scoped format under the currently logged-in user
            # so other users won't see the same shared records anymore.
            key = _current_user_key()
            if key != "__default__":
                _save_scoped_records(path, data)
                return data
            return []
        if isinstance(data, dict):
            users = data.get("users", {})
            if isinstance(users, dict):
                rows = users.get(_current_user_key(), [])
                if isinstance(rows, list):
                    return rows
    except Exception:
        pass
    return []


def _save_scoped_records(path: str, rows: list[dict]) -> None:
    """Save records only for current user while preserving other users."""
    scoped: dict = {"users": {}}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            if isinstance(existing, dict) and isinstance(existing.get("users"), dict):
                scoped["users"] = existing["users"]
        except Exception:
            pass
    scoped["users"][_current_user_key()] = rows
    with open(path, "w", encoding="utf-8") as f:
        json.dump(scoped, f, ensure_ascii=False, indent=2)


def progress_bar_color(progress: int | float) -> str:
    """สีแถบ progress: แดง (0%) → ส้ม → เหลือง → เขียว (100%)."""
    p = max(0.0, min(100.0, float(progress or 0)))
    stops = [
        (0.0,    (239, 68, 68)),   # red
        (33.333, (249, 115, 22)), # orange
        (66.667, (234, 179, 8)), # yellow
        (100.0,  (34, 197, 94)), # green
    ]
    if p <= stops[0][0]:
        r, g, b = stops[0][1]
    elif p >= stops[-1][0]:
        r, g, b = stops[-1][1]
    else:
        r, g, b = stops[-1][1]
        for i in range(len(stops) - 1):
            p0, c0 = stops[i]
            p1, c1 = stops[i + 1]
            if p0 <= p <= p1:
                tinterp = (p - p0) / (p1 - p0) if p1 > p0 else 0.0
                r = int(round(c0[0] + (c1[0] - c0[0]) * tinterp))
                g = int(round(c0[1] + (c1[1] - c0[1]) * tinterp))
                b = int(round(c0[2] + (c1[2] - c0[2]) * tinterp))
                break
    return f"#{r:02x}{g:02x}{b:02x}"


def progress_slider_stylesheet(accent: str, groove: str = "#e2e8f0") -> str:
    """QSS สำหรับ QSlider แนวนอน (รูปแบบเดียวที่ Qt บน Windows parse ได้เสถียร)."""
    return (
        "QSlider::groove:horizontal { height: 6px; background: %s; border-radius: 3px; } "
        "QSlider::sub-page:horizontal { background: %s; border-radius: 3px; } "
        "QSlider::handle:horizontal { background: %s; border: 2px solid #ffffff; width: 14px; height: 14px; "
        "margin-top: -5px; margin-bottom: -5px; border-radius: 8px; }"
        % (groove, accent, accent)
    )


def load_all_data():
    global mock_tasks
    data = _load_scoped_records(TASK_DB_FILE)
    if data:
        mock_tasks = data
        # Remove legacy "Review" and align status with progress rule.
        for t in mock_tasks:
            p = int(t.get("progress", 0) or 0)
            t["bar"] = progress_bar_color(p)
            if p <= 0:
                t["status"] = "To do"
                t["status_style"] = "background:#f1f5f9; color:#64748b;"
                t["status_width"] = 60
            elif p >= 100:
                t["status"] = "Done"
                t["status_style"] = "background:#dcfce7; color:#16a34a;"
                t["status_width"] = 60
            else:
                t["status"] = "In Progress"
                t["status_style"] = "background:#e0e7ff; color:#4f46e5;"
                t["status_width"] = 90
        return
    # New users should start with empty tasks.
    # Existing users keep their own saved data in scoped storage.
    mock_tasks = []

load_all_data()


# =====================================================================
# Style maps  — single source of truth สำหรับสี risk/status
# =====================================================================
RISK_STYLE_MAP = {
    "Low":      {"risk_color": "#22c55e", "risk_bg": "#f0fdf4"},
    "Medium":   {"risk_color": "#eab308", "risk_bg": "#fefce8"},
    "High":     {"risk_color": "#f97316", "risk_bg": "#fff7ed"},
    "Critical": {"risk_color": "#ef4444", "risk_bg": "#fef2f2"},
}
# badge สี (text) ตรงกับ RISK_STYLE_MAP
RISK_BADGE_COLOR = {k: v["risk_color"] for k, v in RISK_STYLE_MAP.items()}

TAG_COLOR_MAP = {
    "Backend":      "#22c55e",
    "Frontend":     "#ef4444",
    "Core Logic":   "#f97316",
    "Architecture": "#22c55e",
    "Design":       "#8b5cf6",
    "DevOps":       "#06b6d4",
    "Testing":      "#eab308",
    "Other":        "#64748b",
}

STATUS_STYLE_MAP = {
    "To do":       {"status_style": "background:#f1f5f9; color:#64748b;",  "status_width": 60},
    "In Progress": {"status_style": "background:#e0e7ff; color:#4f46e5;",  "status_width": 90},
    "Done":        {"status_style": "background:#dcfce7; color:#16a34a;",  "status_width": 60},
}


def status_from_progress(progress: int) -> str:
    p = int(progress or 0)
    if p <= 0:
        return "To do"
    if p >= 100:
        return "Done"
    return "In Progress"


# =====================================================================
# Risk Engine
# =====================================================================
def parse_due_date(due_str: str) -> date | None:
    s = str(due_str or "").strip()
    if not s:
        return None

    # Common full-date formats.
    for fmt in ["%b %d %Y", "%b %d, %Y", "%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y"]:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass

    # If user/UI stores month+day without year (e.g. "Apr 1" / "Apr 1,"), assume current year.
    s2 = s.replace(",", "")
    for fmt in ["%b %d", "%b %d"]:
        try:
            d = datetime.strptime(s2, fmt).date()
            return date(date.today().year, d.month, d.day)
        except ValueError:
            pass
    return None


def compute_task_severity(task: dict) -> str:
    """
    Priority:
    - If user selected an explicit risk level (Low/High/Critical), keep it as-is.
    - Only allow "Medium" to be bumped to "Critical" by overdue/near-deadline heuristics.
    """
    manual_risk = task.get("risk", "Medium")
    if manual_risk in ("Low", "High", "Critical"):
        return manual_risk

    progress = task.get("progress", 0)
    due_str = task.get("due_date", "")
    due = parse_due_date(due_str)
    today = date.today()

    if due:
        days_left = (due - today).days
        if (days_left < 0 and progress < 100) or (0 <= days_left <= 3):
            return "Critical"

        total_duration = task.get("total_days", 60)
        time_elapsed_ratio = 1 - (days_left / total_duration) if total_duration > 0 else 1
        if progress < 30 and time_elapsed_ratio > 0.50:
            return "Critical"

    return "Medium"


def should_alert_task(task: dict) -> bool:
    # Alert only for tasks approaching deadline (no overdue).
    due = parse_due_date(task.get("due_date", "") or "")
    if not due:
        return False
    # Use current local date as the reference for "now".
    days_left = (due - datetime.now().date()).days
    # Notify when due date is within 3 days (including due-today).
    if not (0 <= days_left <= 3):
        return False
    return True


def build_alert_from_task(task: dict, alert_id: int, *, is_new_task: bool = False) -> dict:
    LOW_PROGRESS_THRESHOLD = 30
    severity = compute_task_severity(task)
    progress = task.get("progress", 0)
    due_str  = task.get("due_date", "")
    due      = parse_due_date(due_str)
    today    = date.today()

    # Compose alert messages: deadline-only.
    messages: list[str] = []
    days_left: int | None = None
    if due:
        days_left = (due - today).days
        if days_left == 0:
            messages.append("Due today.")
        else:
            messages.append(f"Due soon: {days_left} day(s) left.")
    messages.append(f"Progress: {progress}%. Risk: {severity}.")

    computed_description = "\n".join(messages)
    # If user edited the task's description in the UI, persist it.
    user_description = str(task.get("description", "") or "").strip()
    description = user_description if user_description else computed_description

    icon = "⚠️" if severity == "Critical" else "⚠"
    if days_left is None:
        meta_prefix = "Invalid due date"
    elif days_left == 0:
        meta_prefix = "Due today"
    else:
        meta_prefix = f"Due in {days_left} day(s)"
    return {
        "id":          alert_id,
        "icon":        icon,
        "title":       f"{task['name']} — {severity} Risk",
        "description": description,
        "meta":        f"{meta_prefix} · {today.strftime('%b %d, %Y')}",
        "severity":    severity,
        "project":     task.get("project", ""),
        "status":      task.get("status", ""),
        "progress":    progress,
        "due_date":    task.get("due_date", ""),
        "role":        task.get("role", ""),
        "read":        False,
        # When dismissed, we keep it persisted but hide it from the alert list UI.
        "dismissed":   False,
        "task_id":     task.get("id", 0),
        "source":      "risk_engine",
    }


def sync_alerts_from_tasks(existing_alerts: list[dict], tasks: list[dict]) -> list[dict]:
    max_id = max((a.get("id", 0) for a in existing_alerts), default=0)
    next_id = max_id + 1

    existing_by_task: dict[int, dict] = {
        a["task_id"]: a
        for a in existing_alerts
        if a.get("source") == "risk_engine"
    }
    manual_alerts = [a for a in existing_alerts if a.get("source") != "risk_engine"]
    new_alerts: list[dict] = []

    for task in tasks:
        tid = task.get("id", 0)
        if not should_alert_task(task):
            continue
        if tid in existing_by_task:
            old     = existing_by_task[tid]
            updated = build_alert_from_task(task, old["id"], is_new_task=False)
            updated["read"] = old.get("read", False)
            updated["dismissed"] = old.get("dismissed", False)
            new_alerts.append(updated)
        else:
            new_alerts.append(build_alert_from_task(task, next_id, is_new_task=True))
            next_id += 1

    return manual_alerts + new_alerts


# ── DB helpers ──────────────────────────────────────────────────────
def db_load() -> list[dict]:
    existing: list[dict] = []
    data = _load_scoped_records(ALERT_DB_FILE)
    if isinstance(data, list):
        for item in data:
            item.setdefault("read",   False)
            item.setdefault("dismissed", False)
            item.setdefault("source", "manual")
        existing = data
    # Always sync from latest tasks on disk so alerts work for both old and new tasks.
    tasks = _load_scoped_records(TASK_DB_FILE)
    synced = sync_alerts_from_tasks(existing, tasks)
    db_save(synced)
    return synced


def db_save(alerts: list[dict]):
    _save_scoped_records(ALERT_DB_FILE, alerts)


def db_update_alert(alert_id: int, updated: dict, alerts: list[dict]) -> list[dict]:
    # Merge update into existing alert so fields like `dismissed` are not lost.
    new_list = [
        {**dict(a), **dict(updated)} if a.get("id") == alert_id else dict(a)
        for a in alerts
    ]
    db_save(new_list)
    return new_list


def db_remove_alert(alert_id: int, alerts: list[dict]) -> list[dict]:
    new_list = [a for a in alerts if a.get("id") != alert_id]
    db_save(new_list)
    return new_list


def save_tasks():
    _save_scoped_records(TASK_DB_FILE, mock_tasks)


# =====================================================================
# build_task_row_dict  — สร้าง task dict ที่ TaskRow ใช้ได้เลย
# =====================================================================
def build_task_row_dict(task_id: int, name: str, tag: str, status: str,
                         risk: str, due_date_str: str, progress: int = 0) -> dict:
    resolved_status = status_from_progress(progress) or status
    due_display   = ""
    due_date_full = ""
    if due_date_str:
        for fmt in ["%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d"]:
            try:
                d = datetime.strptime(due_date_str.strip(), fmt)
                due_display   = d.strftime("%b %-d") if sys.platform != "win32" else d.strftime("%b %#d")
                due_date_full = d.strftime("%b %d %Y")
                break
            except ValueError:
                pass
    if not due_display:
        due_display   = due_date_str
        due_date_full = due_date_str

    rs = RISK_STYLE_MAP.get(risk, RISK_STYLE_MAP["Medium"])
    si = STATUS_STYLE_MAP.get(resolved_status, STATUS_STYLE_MAP["To do"])
    tag_color = TAG_COLOR_MAP.get(tag, "#64748b")
    return {
        "id":           task_id,
        "name":         f"#{task_id:02d} {name}",
        "tag":          tag,
        "tag_color":    tag_color,
        "progress":     progress,
        "bar":          progress_bar_color(progress),
        "status":       resolved_status,
        "status_width": si["status_width"],
        "status_style": si["status_style"],
        "due":          due_display,
        "due_date":     due_date_full,
        "risk":         risk,
        "risk_color":   rs["risk_color"],
        "risk_bg":      rs["risk_bg"],
        # extra fields ที่ alert/detail page ใช้
        "title":        name,
        "description":  "",
        "role":         "",
        "project":      "",
        "severity":     risk,
    }


# =====================================================================
# GaugeWidget
# =====================================================================
class GaugeWidget(QWidget):
    def __init__(self, value=62, parent=None):
        super().__init__(parent)
        self.target = value
        self._v     = 0.0
        self.setFixedSize(160, 120)
        t = QTimer(self)
        t.timeout.connect(self._tick)
        t.start(12)

    def _tick(self):
        if self._v < self.target:
            self._v = min(self._v + 1.5, float(self.target))
            self.update()

    def _color(self):
        if self._v >= 75: return QColor("#ef4444")
        if self._v >= 50: return QColor("#f97316")
        if self._v >= 25: return QColor("#eab308")
        return QColor("#22c55e")

    def paintEvent(self, _):
        p  = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        W, H       = self.width(), self.height()
        cx, cy, r  = W / 2, H * 0.65, 52
        rect       = QRectF(cx - r, cy - r, r * 2, r * 2)
        pen        = QPen(QColor("#e2e8f0"), 9, Qt.SolidLine, Qt.RoundCap)
        p.setPen(pen)
        p.drawArc(rect, 210 * 16, -240 * 16)
        pen2 = QPen(self._color(), 9, Qt.SolidLine, Qt.RoundCap)
        p.setPen(pen2)
        p.drawArc(rect, 210 * 16, int(-240 * 16 * self._v / 100))
        p.setPen(QColor("#1e293b"))
        p.setFont(QFont("Segoe UI", 22, QFont.Bold))
        p.drawText(QRectF(0, cy - 18, W, 36), Qt.AlignHCenter, str(int(self._v)))
        p.setPen(QColor("#94a3b8"))
        p.setFont(QFont("Segoe UI", 8))
        p.drawText(QRectF(0, cy + 14, W, 16), Qt.AlignHCenter, "/ 100")


# =====================================================================
# AnimBar
# =====================================================================
class AnimBar(QProgressBar):
    def __init__(self, value, color, parent=None):
        super().__init__(parent)
        self._t = value
        self._v = 0
        self.setRange(0, 100)
        self.setValue(0)
        self.setTextVisible(False)
        self.setFixedHeight(6)
        self.setStyleSheet(f"""
            QProgressBar {{ background:#e5e7eb; border-radius:3px; border:none; }}
            QProgressBar::chunk {{ background:{color}; border-radius:3px; }}
        """)
        t = QTimer(self)
        t.timeout.connect(self._tick)
        t.start(12)

    def _tick(self):
        if self._v < self._t:
            self._v = min(self._v + 2, self._t)
            self.setValue(self._v)


# =====================================================================
# AnalyzeRiskDialog  — Smart Risk Analysis Popup
# =====================================================================
def compute_risk_analysis() -> dict:
    """Compute full risk analysis from mock_tasks. Returns analysis dict."""
    today = date.today()
    total = len(mock_tasks)
    if total == 0:
        return {
            "overall": 0, "label": "Low", "timeline": 0, "workload": 0, "scope": 0,
            "issues": [], "recommendations": [], "health": 100,
            "completion_rate": 0, "total": 0, "done": 0,
        }

    def _is_completed(t: dict) -> bool:
        return t.get("status") == "Done" or int(t.get("progress", 0) or 0) >= 100

    # ── Timeline Risk: overdue + near-deadline ───────────────────
    overdue_count  = 0
    near_deadline  = 0
    total_days_left = 0
    for t in mock_tasks:
        d = parse_due_date(t.get("due_date", ""))
        if d:
            dl = (d - today).days
            if dl < 0 and t.get("progress", 0) < 100:
                overdue_count += 1
            elif 0 <= dl <= 5:
                near_deadline += 1
            total_days_left += max(dl, 0)
    timeline_risk = min(100, int((overdue_count * 30 + near_deadline * 15)))

    # ── Workload Risk: unfinished tasks / capacity ───────────────
    active_tasks    = [t for t in mock_tasks if not _is_completed(t)]
    avg_progress    = sum(t.get("progress", 0) for t in active_tasks) / max(len(active_tasks), 1)
    workload_risk   = min(100, int(len(active_tasks) * 10 + (100 - avg_progress) * 0.4))

    # ── Scope Risk: tasks in Critical/High with low progress ─────
    critical_stalled = sum(1 for t in mock_tasks
                           if t.get("risk") in ("Critical","High") and t.get("progress",0) < 40)
    scope_risk = min(100, critical_stalled * 25)

    # ── Overall weighted score ───────────────────────────────────
    overall = int(timeline_risk * 0.45 + workload_risk * 0.35 + scope_risk * 0.20)
    overall = min(100, overall)

    if overall >= 75:   label = "Critical"
    elif overall >= 50: label = "High"
    elif overall >= 25: label = "Medium"
    else:               label = "Low"

    # ── Issues Found ─────────────────────────────────────────────
    issues = []
    for t in mock_tasks:
        d = parse_due_date(t.get("due_date", ""))
        prog = t.get("progress", 0)
        name_short = t.get("name", "Task")[:22]
        if d:
            dl = (d - today).days
            if dl < 0 and prog < 100:
                sev = "critical"
                issues.append({"sev": sev, "text": f"{name_short} — {abs(dl)}d overdue, {prog}% done"})
            elif 0 <= dl <= 3 and prog < 60:
                issues.append({"sev": "high", "text": f"{name_short} — {dl}d left, only {prog}% complete"})
        if t.get("risk") in ("High","Critical") and prog < 30:
            issues.append({"sev": "high", "text": f"{name_short} — {t.get('risk')} risk, stalled at {prog}%"})

    # ── Recommendations ──────────────────────────────────────────
    recs = []
    if overdue_count > 0:
        recs.append(f"⏰  Reschedule {overdue_count} overdue task(s) immediately")
    if critical_stalled > 0:
        recs.append(f"🚨  Unblock {critical_stalled} critical task(s) with low progress")
    if workload_risk > 60:
        recs.append("👥  Consider redistributing tasks across team members")
    if scope_risk > 40:
        recs.append("📋  Review scope — too many high-risk tasks unstarted")
    if not recs:
        recs.append("✅  Project looks healthy — maintain current pace")

    # ── Project Health Score (inverse of overall) ────────────────
    health = 100 - overall
    done_count = sum(1 for t in mock_tasks if _is_completed(t))
    completion_rate = int(done_count / total * 100) if total > 0 else 0

    return {
        "overall": overall, "label": label,
        "timeline": timeline_risk, "workload": workload_risk, "scope": scope_risk,
        "issues": issues[:5], "recommendations": recs[:4],
        "health": health, "completion_rate": completion_rate,
        "total": total, "done": done_count,
    }


class AnalyzeRiskDialog(QDialog):
    """
    Smart Analyze Risk popup — ให้ข้อมูลมากกว่า gauge บน Dashboard:
    - Overall Risk Score (animated gauge)
    - Risk by Dimension (Timeline / Workload / Scope)
    - Issues Found (จาก task data จริง)
    - Recommendations (action items)
    - Project Health Score
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Analyze Risk")
        self.setModal(True)
        self.setFixedWidth(480)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._data = compute_risk_analysis()
        self._build_ui()

    def _build_ui(self):
        from PySide6.QtWidgets import QGraphicsDropShadowEffect, QTabWidget
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)

        card = QFrame()
        card.setObjectName("analyzeCard")
        card.setStyleSheet("QFrame#analyzeCard{background:#ffffff;border-radius:20px;border:none;}")
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40); shadow.setOffset(0, 8); shadow.setColor(QColor(0,0,0,60))
        card.setGraphicsEffect(shadow)
        outer.addWidget(card)

        root = QVBoxLayout(card)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ───────────────────────────────────────────────
        hdr = QFrame()
        hdr.setStyleSheet("background:#6366f1;border-top-left-radius:20px;border-top-right-radius:20px;")
        hdr.setFixedHeight(56)
        hl = QHBoxLayout(hdr); hl.setContentsMargins(24, 0, 16, 0)
        htitle = QLabel("🔍  Analyze Risk"); htitle.setStyleSheet("color:white;font-size:16px;font-weight:800;background:transparent;")
        hl.addWidget(htitle); hl.addStretch()
        xb = QPushButton("✕"); xb.setFixedSize(28, 28); xb.setCursor(Qt.PointingHandCursor)
        xb.setStyleSheet("QPushButton{background:#eef2ff;color:#4f46e5;border:none;border-radius:7px;font-size:13px;font-weight:bold;} QPushButton:hover{background:#e0e7ff;}")
        xb.clicked.connect(self.accept); hl.addWidget(xb)
        root.addWidget(hdr)

        # ── Tab Widget ───────────────────────────────────────────
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane{border:none;background:transparent;}
            QTabBar::tab{background:transparent;color:#94a3b8;padding:10px 20px;font-size:12px;font-weight:600;border:none;}
            QTabBar::tab:selected{color:#4f46e5;border-bottom:2px solid #4f46e5;}
            QTabBar::tab:hover{color:#334155;}
        """)

        # ── Tab 1: Overview ──────────────────────────────────────
        t1 = QWidget(); t1.setStyleSheet("background:white;")
        t1l = QVBoxLayout(t1); t1l.setContentsMargins(24,16,24,16); t1l.setSpacing(16)

        # Score row
        score_row = QHBoxLayout(); score_row.setSpacing(16)

        # Gauge
        gauge_frame = QFrame()
        gauge_frame.setStyleSheet("background:#f8fafc;border-radius:14px;border:none;")
        gfl = QVBoxLayout(gauge_frame); gfl.setContentsMargins(16,12,16,12); gfl.setSpacing(4)
        gfl.addWidget(QLabel("Overall Score"), alignment=Qt.AlignCenter)
        self._gauge = GaugeWidget(self._data["overall"])
        gfl.addWidget(self._gauge, alignment=Qt.AlignCenter)
        badge_palette = {
            "Low": ("#22c55e", "#f0fdf4"),
            "Medium": ("#d97706", "#fef3c7"),
            "High": ("#ea580c", "#ffedd5"),
            "Critical": ("#dc2626", "#fee2e2"),
        }
        lbl_col, lbl_bg = badge_palette.get(self._data["label"], ("#ea580c", "#ffedd5"))
        badge = QLabel(f"  {self._data['label']}  ")
        badge.setStyleSheet(f"background:{lbl_bg};color:{lbl_col};border-radius:8px;font-size:11px;font-weight:700;padding:2px 8px;")
        badge.setAlignment(Qt.AlignCenter)
        gfl.addWidget(badge, alignment=Qt.AlignCenter)
        score_row.addWidget(gauge_frame)

        # Health panel
        health_frame = QFrame()
        health_frame.setStyleSheet("background:#f0fdf4;border-radius:14px;border:none;")
        hfl = QVBoxLayout(health_frame); hfl.setContentsMargins(16,12,16,12); hfl.setSpacing(8)
        hl2 = QLabel("Project Health"); hl2.setStyleSheet("font-size:11px;color:#64748b;font-weight:600;background:transparent;"); hfl.addWidget(hl2, alignment=Qt.AlignCenter)
        hv = QLabel(f"{self._data['health']}"); hv.setStyleSheet("font-size:36px;font-weight:900;color:#16a34a;background:transparent;"); hv.setAlignment(Qt.AlignCenter); hfl.addWidget(hv)
        hfl.addWidget(QLabel("/ 100"), alignment=Qt.AlignCenter)
        hfl.addWidget(AnimBar(self._data["health"], "#22c55e"))

        comp_row = QHBoxLayout()
        comp_row.addWidget(self._mini_stat("Done", str(self._data["done"]), "#22c55e"))
        comp_row.addWidget(self._mini_stat("Total", str(self._data["total"]), "#4f46e5"))
        comp_row.addWidget(self._mini_stat("Rate", f"{self._data['completion_rate']}%", "#0ea5e9"))
        hfl.addLayout(comp_row)
        score_row.addWidget(health_frame)
        t1l.addLayout(score_row)

        # Dimensions
        dim_frame = QFrame(); dim_frame.setStyleSheet("background:#f8fafc;border-radius:12px;border:none;")
        dfl = QVBoxLayout(dim_frame); dfl.setContentsMargins(16,12,16,12); dfl.setSpacing(10)
        dfl.addWidget(self._section_lbl("Risk by Dimension"))
        dims = [("⏱  Timeline Risk", self._data["timeline"], "#ef4444"),
                ("⚖  Workload Risk",  self._data["workload"],  "#eab308"),
                ("🎯  Scope Risk",    self._data["scope"],     "#22c55e")]
        for dim_name, val, col in dims:
            rw = QVBoxLayout(); rw.setSpacing(4)
            rh = QHBoxLayout()
            lb = QLabel(dim_name); lb.setStyleSheet("font-size:12px;color:#475569;background:transparent;")
            pct = QLabel(f"{val}%"); pct.setStyleSheet(f"font-size:12px;font-weight:700;color:{col};background:transparent;")
            rh.addWidget(lb); rh.addStretch(); rh.addWidget(pct)
            rw.addLayout(rh); rw.addWidget(AnimBar(val, col))
            dfl.addLayout(rw)
        t1l.addWidget(dim_frame)
        tabs.addTab(t1, "📊  Overview")

        # ── Tab 2: Issues & Actions ──────────────────────────────
        t2 = QWidget(); t2.setStyleSheet("background:white;")
        t2l = QVBoxLayout(t2); t2l.setContentsMargins(24,16,24,16); t2l.setSpacing(14)

        issues = self._data["issues"]
        if issues:
            t2l.addWidget(self._section_lbl("⚠  Issues Found"))
            iss_frame = QFrame(); iss_frame.setStyleSheet("background:#fff7ed;border-radius:12px;border:none;")
            ifl = QVBoxLayout(iss_frame); ifl.setContentsMargins(14,12,14,12); ifl.setSpacing(10)
            sev_dot = {"critical":"#ef4444","high":"#f97316","medium":"#eab308","low":"#22c55e"}
            for issue in issues:
                ir = QHBoxLayout(); ir.setSpacing(10)
                dot = QLabel("●"); dot.setFixedWidth(12)
                dot.setStyleSheet(f"color:{sev_dot.get(issue['sev'],'#94a3b8')};background:transparent;")
                il = QLabel(issue["text"]); il.setStyleSheet("font-size:12px;color:#374151;background:transparent;"); il.setWordWrap(True)
                ir.addWidget(dot); ir.addWidget(il, 1)
                sep = QFrame(); sep.setFixedHeight(1); sep.setStyleSheet("background:#fed7aa;border:none;")
                ifl.addLayout(ir)
                if issue != issues[-1]: ifl.addWidget(sep)
            t2l.addWidget(iss_frame)
        else:
            ok = QLabel("✅  No critical issues found!"); ok.setAlignment(Qt.AlignCenter)
            ok.setStyleSheet("font-size:14px;font-weight:700;color:#16a34a;padding:20px;background:transparent;")
            t2l.addWidget(ok)

        t2l.addWidget(self._section_lbl("💡  Recommendations"))
        rec_frame = QFrame(); rec_frame.setStyleSheet("background:#eff6ff;border-radius:12px;border:none;")
        rfl = QVBoxLayout(rec_frame); rfl.setContentsMargins(14,12,14,12); rfl.setSpacing(8)
        for rec in self._data["recommendations"]:
            rl = QLabel(rec); rl.setStyleSheet("font-size:12px;color:#0c4a6e;background:transparent;"); rl.setWordWrap(True)
            rfl.addWidget(rl)
        t2l.addWidget(rec_frame)
        t2l.addStretch()
        tabs.addTab(t2, "🚨  Issues")

        root.addWidget(tabs)

        # ── Footer buttons ───────────────────────────────────────
        foot = QFrame(); foot.setStyleSheet("background:#f8fafc;border-bottom-left-radius:20px;border-bottom-right-radius:20px;border:none;")
        fl = QHBoxLayout(foot); fl.setContentsMargins(24,12,24,12); fl.setSpacing(12); fl.addStretch()
        close_b = QPushButton("Close"); close_b.setFixedSize(100,38); close_b.setCursor(Qt.PointingHandCursor)
        close_b.setStyleSheet("QPushButton{background:white;color:#374151;border:1.5px solid #d1d5db;border-radius:10px;font-size:13px;} QPushButton:hover{background:#f9fafb;}")
        close_b.clicked.connect(self.reject); fl.addWidget(close_b)
        ok_b = QPushButton("OK"); ok_b.setFixedSize(100,38); ok_b.setCursor(Qt.PointingHandCursor)
        ok_b.setStyleSheet("QPushButton{background:#6366f1;color:white;border:none;border-radius:10px;font-size:13px;font-weight:bold;} QPushButton:hover{background:#4f46e5;}")
        ok_b.clicked.connect(self.accept); fl.addWidget(ok_b)
        root.addWidget(foot)

    def _section_lbl(self, text):
        l = QLabel(text); l.setStyleSheet("font-size:12px;font-weight:700;color:#64748b;background:transparent;"); return l

    def _mini_stat(self, lbl, val, col):
        bg_map = {"#22c55e": "#f0fdf4", "#4f46e5": "#eef2ff", "#0ea5e9": "#f0f9ff"}
        f = QFrame(); f.setStyleSheet(f"background:{bg_map.get(col, '#f8fafc')};border-radius:8px;border:none;")
        fl = QVBoxLayout(f); fl.setContentsMargins(8,6,8,6); fl.setSpacing(2)
        vl = QLabel(val); vl.setStyleSheet(f"font-size:16px;font-weight:800;color:{col};background:transparent;"); vl.setAlignment(Qt.AlignCenter); fl.addWidget(vl)
        ll = QLabel(lbl); ll.setStyleSheet("font-size:10px;color:#94a3b8;background:transparent;"); ll.setAlignment(Qt.AlignCenter); fl.addWidget(ll)
        return f


# =====================================================================
# DraggableWidget  — wrapper ทำให้ widget ใดก็ได้ drag & drop ได้
# =====================================================================
class DraggableWidget(QFrame):
    """
    ห่อ widget ใด ๆ ให้ลาก-วางได้ใน DragDropLayout
    แสดง drag handle (⠿) ที่มุมบนซ้าย เมื่อ hover
    """
    drag_started = Signal(object)   # emits self

    def __init__(self, widget: QWidget, widget_id: str, title: str = "", parent=None):
        super().__init__(parent)
        self.widget_id   = widget_id
        self._inner      = widget
        self._dragging   = False
        self._drag_pos   = None

        self.setObjectName("draggableWidget")
        self.setStyleSheet("""
            QFrame#draggableWidget {
                background: transparent; border: 2px solid transparent;
                border-radius: 14px;
            }
            QFrame#draggableWidget:hover {
                border: 2px dashed #c7d2fe;
            }
        """)
        self.setCursor(Qt.OpenHandCursor)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # drag handle bar
        self._handle = QFrame()
        self._handle.setFixedHeight(20)
        self._handle.setStyleSheet("background:transparent;")
        hl = QHBoxLayout(self._handle)
        hl.setContentsMargins(8, 0, 8, 0)
        handle_lbl = QLabel("⠿⠿⠿")
        handle_lbl.setStyleSheet("color:#cbd5e1;font-size:11px;letter-spacing:3px;background:transparent;")
        hl.addWidget(handle_lbl)
        hl.addStretch()
        if title:
            tl = QLabel(title)
            tl.setStyleSheet("color:#94a3b8;font-size:10px;font-weight:600;background:transparent;")
            hl.addWidget(tl)
        self._handle.hide()
        outer.addWidget(self._handle)
        outer.addWidget(widget)

    def enterEvent(self, e):
        self._handle.show()
        self.setCursor(Qt.OpenHandCursor)
        super().enterEvent(e)

    def leaveEvent(self, e):
        if not self._dragging:
            self._handle.hide()
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_pos = e.globalPosition().toPoint()
            self.setCursor(Qt.ClosedHandCursor)
            self.drag_started.emit(self)
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        self._dragging = False
        self.setCursor(Qt.OpenHandCursor)
        super().mouseReleaseEvent(e)


class DragDropGrid(QWidget):
    """
    Grid layout ที่รองรับ drag & drop เปลี่ยนตำแหน่ง DraggableWidget
    ใช้ mouseMoveEvent ของ overlay สำหรับ live preview drop zone
    """
    layout_changed = Signal(list)   # emits new order of widget_ids

    def __init__(self, cols: int = 2, parent=None):
        super().__init__(parent)
        self._cols        = cols
        self._widgets: list[DraggableWidget] = []
        self._dragging_w: DraggableWidget | None = None
        self._drop_idx    = -1
        self._placeholder = None
        self.setAcceptDrops(True)
        self.setMouseTracking(True)

        self._grid = QGridLayout(self)
        self._grid.setSpacing(16)
        self._grid.setContentsMargins(0, 0, 0, 0)

    def add_widget(self, dw: DraggableWidget):
        dw.drag_started.connect(self._on_drag_started)
        self._widgets.append(dw)
        self._relayout()

    def _relayout(self):
        # clear grid
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        for i, w in enumerate(self._widgets):
            r, c = divmod(i, self._cols)
            self._grid.addWidget(w, r, c)

    def _on_drag_started(self, widget: DraggableWidget):
        self._dragging_w = widget

    def mouseMoveEvent(self, e):
        if self._dragging_w is None:
            return
        # find widget under cursor
        pos = e.position().toPoint()
        for i, w in enumerate(self._widgets):
            if w == self._dragging_w:
                continue
            if w.geometry().contains(pos):
                self._swap(self._dragging_w, w)
                break
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if self._dragging_w:
            self._dragging_w.setCursor(Qt.OpenHandCursor)
            self._dragging_w = None
            self.layout_changed.emit([w.widget_id for w in self._widgets])
        super().mouseReleaseEvent(e)

    def _swap(self, a: DraggableWidget, b: DraggableWidget):
        ia = self._widgets.index(a)
        ib = self._widgets.index(b)
        self._widgets[ia], self._widgets[ib] = self._widgets[ib], self._widgets[ia]
        self._relayout()


# =====================================================================
# TaskRow
# =====================================================================
class TaskRow(QFrame):
    double_clicked = Signal(dict)

    def __init__(self, t):
        super().__init__()
        self.task_data = dict(t)
        self.setObjectName("taskRow")
        self.setStyleSheet("#taskRow { background: white; border: none; }")
        self.setFixedHeight(70)

        layout = QGridLayout(self)
        layout.setContentsMargins(25, 8, 25, 8)
        layout.setHorizontalSpacing(20)
        layout.setColumnStretch(0, 4)
        layout.setColumnStretch(1, 3)
        layout.setColumnStretch(2, 2)
        layout.setColumnStretch(3, 1)
        layout.setColumnStretch(4, 1)

        risk_level = t.get("risk", "Medium")
        rs = RISK_STYLE_MAP.get(risk_level, RISK_STYLE_MAP["Medium"])

        # Task name + tag
        task_col_widget = QWidget()
        task_col = QVBoxLayout(task_col_widget)
        task_col.setContentsMargins(0, 0, 0, 0)
        task_col.setSpacing(4)
        task_col.setAlignment(Qt.AlignVCenter)
        title = QLabel(t["name"])
        title.setStyleSheet("font-size: 13px; font-weight: bold; color: #4b5563;")
        tag_layout = QHBoxLayout()
        tag_layout.setSpacing(5)
        dot = QLabel()
        dot.setFixedSize(8, 8)
        dot_color = t.get("risk_color") or rs["risk_color"]
        dot.setStyleSheet(f"background-color: {dot_color}; border-radius: 4px;")
        tag = QLabel(t["tag"])
        tag.setStyleSheet("font-size: 11px; color: #6b7280; font-weight: 500;")
        tag_layout.addWidget(dot)
        tag_layout.addWidget(tag)
        tag_layout.addStretch()
        task_col.addWidget(title)
        task_col.addLayout(tag_layout)

        # Progress
        prog_col_widget = QWidget()
        prog_col = QVBoxLayout(prog_col_widget)
        prog_col.setContentsMargins(0, 0, 0, 0)
        prog_col.setSpacing(4)
        prog_col.setAlignment(Qt.AlignCenter)
        pval = int(t.get("progress", 0) or 0)
        prog_color = progress_bar_color(pval)
        percent = QLabel(f"{pval}%")
        percent.setStyleSheet(f"font-size: 12px; color: {prog_color}; font-weight: 600;")
        bar = AnimBar(pval, prog_color)
        bar.setFixedWidth(100)
        prog_col.addWidget(percent)
        prog_col.addWidget(bar)
        prog_col.addStretch()

        # Status
        status_col_widget = QWidget()
        status_col = QVBoxLayout(status_col_widget)
        status_col.setContentsMargins(0, 0, 0, 0)
        status_col.setAlignment(Qt.AlignCenter)
        status = QLabel(t["status"])
        status.setAlignment(Qt.AlignCenter)
        status.setFixedSize(t.get("status_width", 85), 28)
        status.setStyleSheet(t["status_style"] + "font-size: 12px; border-radius: 8px; font-weight: 600;")
        status_col.addWidget(status)

        # Risk — ใช้ RISK_STYLE_MAP เพื่อให้สีตรงกับทุกหน้า
        risk_col_widget = QWidget()
        risk_col = QVBoxLayout(risk_col_widget)
        risk_col.setContentsMargins(0, 0, 0, 0)
        risk_col.setAlignment(Qt.AlignCenter)
        risk_lbl = QLabel(risk_level)
        risk_lbl.setAlignment(Qt.AlignCenter)
        risk_lbl.setFixedSize(72, 26)
        risk_lbl.setStyleSheet(
            f"background:{rs['risk_bg']}; color:{rs['risk_color']}; "
            f"font-size:11px; border-radius:7px; font-weight:700;"
        )
        risk_col.addWidget(risk_lbl)

        # Due date
        due_col_widget = QWidget()
        due_col = QHBoxLayout(due_col_widget)
        due_col.setContentsMargins(0, 0, 0, 0)
        due_col.setAlignment(Qt.AlignCenter)
        due_col.setSpacing(5)
        if "due_color" in t:
            due_dot = QLabel()
            due_dot.setFixedSize(7, 7)
            due_dot.setStyleSheet(f"background-color:{t['due_color']}; border-radius:3px;")
            due_col.addWidget(due_dot)
        due = QLabel(t["due"])
        due.setStyleSheet(f"font-size:13px; color:{t.get('due_text_color','#4b5563')}; font-weight:500;")
        due_col.addWidget(due)

        layout.addWidget(task_col_widget,  0, 0)
        layout.addWidget(prog_col_widget,  0, 1)
        layout.addWidget(status_col_widget, 0, 2)
        layout.addWidget(risk_col_widget,  0, 3)
        layout.addWidget(due_col_widget,   0, 4, alignment=Qt.AlignCenter)

        self._install_double_click_filter(self)

    def _install_double_click_filter(self, widget):
        widget.installEventFilter(self)
        for child in widget.findChildren(QWidget):
            child.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonDblClick and event.button() == Qt.LeftButton:
            self.double_clicked.emit(dict(self.task_data))
            return True
        return super().eventFilter(obj, event)


# =====================================================================
# NewTaskDialog
# =====================================================================
class NewTaskDialog(QDialog):
    task_created = Signal(dict)

    RISK_LEVELS = ["Low", "Medium", "High", "Critical"]
    RISK_COLORS = {
        "Low":      ("#16A34A", "#DCFCE7", "#BBF7D0"),
        "Medium":   ("#D97706", "#FEF3C7", "#FDE68A"),
        "High":     ("#EA580C", "#FFEDD5", "#FED7AA"),
        "Critical": ("#DC2626", "#FEE2E2", "#FECACA"),
    }

    def __init__(self, next_task_id: int, parent=None):
        super().__init__(parent)
        self.next_task_id  = next_task_id
        self._selected_risk = "Low"
        self._risk_btns: dict[str, QPushButton] = {}
        self.setWindowTitle("New Task")
        self.setModal(True)
        self.setFixedWidth(430)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)

        card = QFrame()
        card.setObjectName("dialogCard")
        card.setStyleSheet("QFrame#dialogCard { background:#ffffff; border-radius:18px; border:1px solid #e2e8f0; }")
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(32)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 60))
        card.setGraphicsEffect(shadow)
        outer.addWidget(card)

        root = QVBoxLayout(card)
        root.setContentsMargins(28, 22, 28, 26)
        root.setSpacing(0)

        # Header
        header_row = QHBoxLayout()
        plus_lbl = QLabel("+")
        plus_lbl.setFont(QFont("Segoe UI", 15, QFont.Bold))
        plus_lbl.setStyleSheet("color:#111827; background:transparent; border:none;")
        title_lbl = QLabel("New Task")
        title_lbl.setFont(QFont("Segoe UI", 15, QFont.Bold))
        title_lbl.setStyleSheet("color:#111827; background:transparent; border:none;")
        id_lbl = QLabel(f"#{self.next_task_id:02d}")
        id_lbl.setFont(QFont("Segoe UI", 13, QFont.Bold))
        id_lbl.setStyleSheet("color:#6366f1; background:transparent; border:none;")
        header_row.addWidget(plus_lbl)
        header_row.addSpacing(6)
        header_row.addWidget(title_lbl)
        header_row.addSpacing(8)
        header_row.addWidget(id_lbl)
        header_row.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("QPushButton{background:#f1f5f9;color:#64748b;border:none;border-radius:8px;font-size:12px;font-weight:bold;} QPushButton:hover{background:#e2e8f0;color:#1e293b;}")
        close_btn.clicked.connect(self.reject)
        header_row.addWidget(close_btn)
        root.addLayout(header_row)
        root.addSpacing(20)

        # Task Name
        root.addWidget(self._field_label("Task Name"))
        root.addSpacing(6)
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g. implement login page")
        self._name_edit.setStyleSheet(self._input_style())
        self._name_edit.setFixedHeight(42)
        root.addWidget(self._name_edit)
        root.addSpacing(14)

        # Progress
        root.addWidget(self._field_label("Progress"))
        root.addSpacing(6)
        progress_row = QHBoxLayout()
        self._progress_value_lbl = QLabel("0%")
        self._progress_value_lbl.setStyleSheet("font-size:12px;font-weight:700;color:#4f46e5;")
        progress_row.addWidget(self._progress_value_lbl)
        progress_row.addStretch()
        root.addLayout(progress_row)
        self._progress_slider = QSlider(Qt.Horizontal)
        self._progress_slider.setRange(0, 100)
        self._progress_slider.setValue(0)

        def _sync_new_task_progress(v: int) -> None:
            c = progress_bar_color(v)
            self._progress_value_lbl.setText(f"{v}%")
            self._progress_value_lbl.setStyleSheet(f"font-size:12px;font-weight:700;color:{c};")
            self._progress_slider.setStyleSheet(progress_slider_stylesheet(c))

        self._progress_slider.valueChanged.connect(_sync_new_task_progress)
        _sync_new_task_progress(self._progress_slider.value())
        root.addWidget(self._progress_slider)
        root.addSpacing(14)

        # Description
        root.addWidget(self._field_label("Description"))
        root.addSpacing(6)
        self._desc_edit = QTextEdit()
        self._desc_edit.setPlaceholderText("Describe the task details and objectives...")
        self._desc_edit.setFixedHeight(80)
        self._desc_edit.setStyleSheet(self._input_style(multiline=True))
        root.addWidget(self._desc_edit)
        root.addSpacing(14)

        # Role
        root.addWidget(self._field_label("Role"))
        root.addSpacing(6)
        self._role_edit = QLineEdit()
        self._role_edit.setPlaceholderText("Role")
        self._role_edit.setFixedHeight(42)
        self._role_edit.setStyleSheet(self._input_style())
        root.addWidget(self._role_edit)
        root.addSpacing(14)

        # Due Date
        root.addWidget(self._field_label("Due Date"))
        root.addSpacing(6)
        root.addWidget(self._build_date_row())

        # Due date error label (ซ่อนไว้ก่อน)
        self._due_error_lbl = QLabel("⚠ Please enter a due date")
        self._due_error_lbl.setStyleSheet("color:#ef4444; font-size:11px; background:transparent; border:none;")
        self._due_error_lbl.hide()
        root.addWidget(self._due_error_lbl)
        root.addSpacing(14)

        # Risk Level
        root.addWidget(self._field_label("Risk Level"))
        root.addSpacing(10)
        root.addLayout(self._build_risk_row())
        root.addSpacing(26)

        root.addLayout(self._build_bottom_buttons())

    def _build_date_row(self):
        self._date_container = QWidget()
        self._date_container.setObjectName("dateContainer")
        self._date_container.setStyleSheet(
            "QWidget#dateContainer{background:#ffffff;border:1.5px solid #d1d5db;border-radius:10px;}"
        )
        self._date_container.setFixedHeight(42)
        h = QHBoxLayout(self._date_container)
        h.setContentsMargins(12, 0, 10, 0)
        h.setSpacing(6)
        self._date_line = QLineEdit()
        self._date_line.setText(QDate.currentDate().toString("MM/dd/yyyy"))
        self._date_line.setPlaceholderText("MM/dd/yyyy")
        self._date_line.setStyleSheet("QLineEdit{background:transparent;border:none;font-size:13px;color:#374151;}")
        # ล้าง error เมื่อพิมพ์
        self._date_line.textChanged.connect(self._clear_date_error)
        h.addWidget(self._date_line, stretch=1)
        cal_btn = QPushButton("📅")
        cal_btn.setFixedSize(26, 26)
        cal_btn.setFont(QFont("Segoe UI Emoji", 11))
        cal_btn.setStyleSheet("QPushButton{background:transparent;border:none;} QPushButton:hover{background:#f1f5f9;border-radius:5px;}")
        cal_btn.setCursor(Qt.PointingHandCursor)
        cal_btn.clicked.connect(self._show_calendar)
        h.addWidget(cal_btn)
        return self._date_container

    def _clear_date_error(self):
        self._due_error_lbl.hide()
        self._date_container.setStyleSheet(
            "QWidget#dateContainer{background:#ffffff;border:1.5px solid #d1d5db;border-radius:10px;}"
        )

    def _build_risk_row(self):
        frame = QFrame()
        frame.setObjectName("riskFrame")
        frame.setFixedHeight(44)
        frame.setStyleSheet("QFrame#riskFrame{background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;}")
        row = QHBoxLayout(frame)
        row.setContentsMargins(4, 4, 4, 4)
        row.setSpacing(2)
        for level in self.RISK_LEVELS:
            btn = QPushButton(level)
            btn.setFixedHeight(34)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, lv=level: self._select_risk(lv))
            self._risk_btns[level] = btn
            row.addWidget(btn)
        self._select_risk("Low")
        outer = QHBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(frame)
        return outer

    def _select_risk(self, level: str):
        self._selected_risk = level
        for lv, btn in self._risk_btns.items():
            fg, bg, _ = self.RISK_COLORS[lv]
            if lv == level:
                btn.setStyleSheet(f"QPushButton{{background:{bg};color:{fg};border:1.5px solid {fg};border-radius:8px;font-size:11px;font-weight:bold;padding:0 8px;}}")
            else:
                btn.setStyleSheet(
                    f"QPushButton{{background:transparent;color:{fg};border:1px solid transparent;border-radius:8px;font-size:11px;padding:0 8px;}} "
                    f"QPushButton:hover{{background:{bg};color:{fg};border:1px solid {fg};}}"
                )

    def _build_bottom_buttons(self):
        row = QHBoxLayout()
        row.setSpacing(10)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(40)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet("QPushButton{background:#ffffff;color:#374151;border:1.5px solid #d1d5db;border-radius:10px;font-size:12px;font-weight:500;padding:0 20px;} QPushButton:hover{background:#f9fafb;}")
        cancel_btn.clicked.connect(self.reject)
        add_btn = QPushButton("Add Task")
        add_btn.setFixedHeight(40)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setStyleSheet("QPushButton{background:#4f46e5;color:white;border:none;border-radius:10px;font-size:12px;font-weight:bold;padding:0 24px;} QPushButton:hover{background:#4338ca;}")
        add_btn.clicked.connect(self._on_add_task)
        row.addStretch()
        row.addWidget(cancel_btn)
        row.addWidget(add_btn)
        return row

    def _show_calendar(self):
        from PySide6.QtCore import QLocale
        popup = QDialog(self)
        popup.setWindowTitle("")
        popup.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        popup.setStyleSheet("QDialog{background:#1e1e2e;border:1px solid #3d3d50;border-radius:10px;}")
        cal = QCalendarWidget(popup)
        cal.setLocale(QLocale(QLocale.English))
        cal.setGridVisible(False)
        cal.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        cal.setStyleSheet("QCalendarWidget{background:#1e1e2e;color:white;} QCalendarWidget QAbstractItemView{background:#1e1e2e;color:white;selection-background-color:#4f46e5;} QCalendarWidget QWidget#qt_calendar_navigationbar{background:#2d2d3f;} QCalendarWidget QToolButton{color:white;background:transparent;}")
        def on_date_selected(d: QDate):
            # Use Thai-friendly day/month order. This also matches build_task_row_dict parsing.
            self._date_line.setText(d.toString("dd/MM/yyyy"))
            self._clear_date_error()
            popup.close()
        cal.clicked.connect(on_date_selected)
        v = QVBoxLayout(popup)
        v.setContentsMargins(8, 8, 8, 8)
        v.addWidget(cal)
        popup.adjustSize()
        pos = self._date_line.mapToGlobal(self._date_line.rect().bottomLeft())
        popup.move(pos)
        popup.exec()

    def _field_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
        lbl.setStyleSheet("color:#374151; background:transparent; border:none;")
        return lbl

    def _input_style(self, multiline=False) -> str:
        w   = "QTextEdit" if multiline else "QLineEdit"
        pad = "10px 12px" if multiline else "0 12px"
        return (f"{w}{{background:#ffffff;border:1.5px solid #d1d5db;border-radius:10px;"
                f"padding:{pad};font-size:13px;color:#111827;}}"
                f"{w}::placeholder{{color:#9ca3af;}}"
                f"{w}:focus{{border-color:#6366f1;}}")

    def _on_add_task(self):
        # ── validate task name ──
        name = self._name_edit.text().strip()
        if not name:
            self._name_edit.setFocus()
            self._name_edit.setStyleSheet(self._input_style().replace("#d1d5db", "#ef4444"))
            return

        # ── validate due date ──
        due_text = self._date_line.text().strip()
        if not due_text:
            self._date_container.setStyleSheet(
                "QWidget#dateContainer{background:#fff5f5;border:1.5px solid #ef4444;border-radius:10px;}"
            )
            self._due_error_lbl.show()
            return

        role_text = self._role_edit.text().strip()
        # Show exactly what user typed in Role under Task name.
# If empty, keep default label as "-".
        tag = role_text if role_text else "-"

        task_dict = build_task_row_dict(
            task_id      = self.next_task_id,
            name         = name,
            tag          = tag,
            status       = status_from_progress(self._progress_slider.value()),
            risk         = self._selected_risk,
            due_date_str = due_text,
            progress     = self._progress_slider.value(),
        )
        task_dict["description"] = self._desc_edit.toPlainText().strip()
        task_dict["role"]        = role_text
        task_dict["severity"]    = self._selected_risk

        self.task_created.emit(task_dict)
        self.accept()


# =====================================================================
# DashboardPage  — with AnalyzeRisk popup + Drag & Drop widgets
# =====================================================================
class DashboardPage(QWidget):
    new_task_requested = Signal()
    task_double_clicked = Signal(dict)

    def __init__(self):
        super().__init__()
        self.setStyleSheet("background: #f8fafc;")
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(40, 30, 40, 30)
        self._main_layout.setSpacing(20)

        # ── Header ───────────────────────────────────────────────
        h = QHBoxLayout()
        title = QLabel("Dashboard")
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #334155;")


        self.btn_analyze  = QPushButton("🔍 Analyze Risk")
        self.btn_analyze.setCursor(Qt.PointingHandCursor)
        self.btn_analyze.setStyleSheet(
            "QPushButton{background:#4f46e5;color:white;border:none;border-radius:8px;"
            "padding:8px 16px;font-weight:bold;font-size:13px;}"
            "QPushButton:hover{background:#4338ca;}"
        )
        self.btn_new_task = QPushButton("+ New Task")
        self.btn_new_task.setCursor(Qt.PointingHandCursor)
        self.btn_new_task.setStyleSheet(
            "QPushButton{background:white;color:#4f46e5;border:1.5px solid #4f46e5;"
            "border-radius:8px;padding:8px 20px;font-weight:bold;font-size:13px;}"
            "QPushButton:hover{background:#eef2ff;}"
        )
        h.addWidget(title); h.addStretch()
        h.addWidget(self.btn_analyze); h.addWidget(self.btn_new_task)
        self._main_layout.addLayout(h)

        # connect Analyze Risk → popup
        self.btn_analyze.clicked.connect(self._open_analyze)

        divider = QFrame(); divider.setFixedHeight(1)
        divider.setStyleSheet("background-color:#cbd5e1;border:none;")
        self._main_layout.addWidget(divider)

        # ── Stats row (rebuilt on refresh) ───────────────────────
        self._stats_row = QHBoxLayout(); self._stats_row.setSpacing(16)
        self._main_layout.addLayout(self._stats_row)
        self._render_stats()

        # ── Drag-Drop grid for mid widgets ────────────────────────
        self._drag_grid = DragDropGrid(cols=3)
        self._drag_grid.setMouseTracking(True)

        # Build each widget
        self._gauge_widget   = self._build_gauge_card()
        self._dim_widget     = self._build_dimension_card()
        self._summary_widget = self._build_summary_card()

        # Wrap in DraggableWidget
        self._dw_gauge   = DraggableWidget(self._gauge_widget,   "gauge",   "Overall Risk Score")
        self._dw_dim     = DraggableWidget(self._dim_widget,     "dim",     "Risk by Dimension")
        self._dw_summary = DraggableWidget(self._summary_widget, "summary", "Task Summary")

        self._drag_grid.add_widget(self._dw_gauge)
        self._drag_grid.add_widget(self._dw_dim)
        self._drag_grid.add_widget(self._dw_summary)
        self._main_layout.addWidget(self._drag_grid)

        # ── Task table (full width, also draggable) ───────────────
        self._box = QFrame()
        self._box.setObjectName("tableBox")
        self._box.setStyleSheet("#tableBox{background:white;border:1px solid #cbd5e1;border-radius:16px;}")
        self._tbl_layout = QVBoxLayout(self._box)
        self._tbl_layout.setContentsMargins(0, 0, 0, 0)
        self._tbl_layout.setSpacing(0)

        head_frame = QFrame()
        head_frame.setStyleSheet("background-color:#f8fafc;border-bottom:1px solid #cbd5e1;border-top-left-radius:16px;border-top-right-radius:16px;")
        head_frame.setFixedHeight(46)
        hl = QGridLayout(head_frame); hl.setContentsMargins(25,0,25,0); hl.setHorizontalSpacing(20)
        for i, s in enumerate([4,3,2,1,1]): hl.setColumnStretch(i, s)
        for i, text in enumerate(["Task","Progress","Status","Risk","Due"]):
            lb = QLabel(text); lb.setStyleSheet("color:#64748b;font-size:13px;font-weight:bold;border:none;background:transparent;")
            hl.addWidget(lb, 0, i, alignment=Qt.AlignVCenter|(Qt.AlignLeft if text=="Task" else Qt.AlignCenter))
        self._tbl_layout.addWidget(head_frame)

        self._task_rows_widget  = QWidget()
        self._task_rows_widget.setStyleSheet("background: white; border: none;")
        self._task_rows_layout  = QVBoxLayout(self._task_rows_widget)
        self._task_rows_layout.setContentsMargins(0,0,0,0); self._task_rows_layout.setSpacing(0)
        self._tbl_layout.addWidget(self._task_rows_widget)
        eb = QFrame(); eb.setSizePolicy(QSizePolicy.Preferred,QSizePolicy.Expanding); eb.setMinimumHeight(130); eb.setStyleSheet("background:transparent;border:none;")
        self._tbl_layout.addWidget(eb)
        self._main_layout.addWidget(self._box)
        self._render_task_rows()

    # ── Widget Builders ───────────────────────────────────────────
    def _build_gauge_card(self) -> QFrame:
        gc = QFrame()
        gc.setStyleSheet("background:white;border:none;border-radius:14px;")
        gl = QVBoxLayout(gc); gl.setContentsMargins(18,16,18,16); gl.setSpacing(8)
        gh = QHBoxLayout()
        gtitle = QLabel("Overall Risk Score"); gtitle.setStyleSheet("font-size:13px;font-weight:700;color:#334155;")
        data = compute_risk_analysis()
        badge_palette = {
            "Low": ("#22c55e", "#f0fdf4"),
            "Medium": ("#d97706", "#fef3c7"),
            "High": ("#f97316", "#fff7ed"),
            "Critical": ("#ef4444", "#fef2f2"),
        }
        fg, bg = badge_palette.get(data["label"], ("#f97316", "#fff7ed"))
        gbadge = QLabel(f"  {data['label']}  ")
        gbadge.setStyleSheet(
            f"background:{bg};color:{fg};border-radius:9px;font-size:11px;font-weight:700;padding:2px 8px;"
        )
        gh.addWidget(gtitle); gh.addStretch(); gh.addWidget(gbadge)
        gl.addLayout(gh)
        gl.addWidget(GaugeWidget(data["overall"]), alignment=Qt.AlignCenter)
        # Keep legend left-aligned, but use one rich-text label for stable baseline.
        legend = QLabel(
            "<span style='color:#22c55e;'>●</span> <span style='color:#94a3b8;'>Low</span>"
            " <span style='color:#eab308;'>●</span> <span style='color:#94a3b8;'>Mediam</span>"
            " <span style='color:#f97316;'>●</span> <span style='color:#94a3b8;'>High</span>"
            " <span style='color:#ef4444;'>●</span> <span style='color:#94a3b8;'>Critical</span>"
        )
        legend.setStyleSheet("font-size:11px;")
        legend.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        gl.addWidget(legend, alignment=Qt.AlignLeft)
        return gc

    def _build_dimension_card(self) -> QFrame:
        dc = QFrame()
        dc.setStyleSheet("background:white;border:none;border-radius:14px;")
        dl = QVBoxLayout(dc); dl.setContentsMargins(18,16,18,16); dl.setSpacing(10)
        dt = QLabel("Risk by Dimension"); dt.setStyleSheet("font-size:13px;font-weight:700;color:#334155;")
        dl.addWidget(dt)
        data = compute_risk_analysis()
        for lbl, val, col in [("Timeline Risk", data["timeline"], "#ef4444"),
                               ("Workload Risk", data["workload"], "#eab308"),
                               ("Scope Risk",    data["scope"],   "#22c55e")]:
            rw = QVBoxLayout(); rw.setSpacing(5)
            rh = QHBoxLayout()
            lb = QLabel(lbl); lb.setStyleSheet("font-size:12px;color:#64748b;")
            pct = QLabel(f"{val}%"); pct.setStyleSheet(f"font-size:12px;font-weight:700;color:{col};")
            rh.addWidget(lb); rh.addStretch(); rh.addWidget(pct)
            rw.addLayout(rh); rw.addWidget(AnimBar(val, col))
            dl.addLayout(rw)
        dl.addStretch()
        return dc

    def _build_summary_card(self) -> QFrame:
        sc = QFrame()
        sc.setStyleSheet("background:white;border:none;border-radius:14px;")
        sl = QVBoxLayout(sc); sl.setContentsMargins(18,16,18,16); sl.setSpacing(4)
        sl.addWidget(self._lbl("Total Tasks","font-size:13px;font-weight:700;color:#334155;"))
        self._total_lbl = QLabel(str(len(mock_tasks)))
        self._total_lbl.setStyleSheet("font-size:42px;font-weight:900;color:#1e293b;")
        sl.addWidget(self._total_lbl)
        done_count = sum(1 for t in mock_tasks if t.get("status") == "Done" or int(t.get("progress", 0) or 0) >= 100)
        total = max(len(mock_tasks), 1)
        rate = int(done_count / total * 100)
        sl.addWidget(self._lbl(f"{done_count} completed this week","font-size:11px;color:#94a3b8;"))
        sl.addSpacing(10)
        sl.addWidget(self._lbl("Completed","font-size:12px;color:#64748b;"))
        self._comp_lbl = QLabel(str(done_count))
        self._comp_lbl.setStyleSheet("font-size:32px;font-weight:900;color:#22c55e;")
        sl.addWidget(self._comp_lbl)
        sl.addWidget(self._lbl(f"{rate}% of total","font-size:11px;color:#94a3b8;"))
        sl.addStretch()
        return sc

    # ── Analyze Risk popup ────────────────────────────────────────
    def _open_analyze(self):
        dlg = AnalyzeRiskDialog(parent=self)
        dlg.exec()
        # Refresh dashboard gauge/dimension after analysis (data may have changed)
        self.refresh_tasks()

    def _lbl(self, text, style):
        l = QLabel(text); l.setStyleSheet(style); return l

    def _render_stats(self):
        while self._stats_row.count():
            item = self._stats_row.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        total     = len(mock_tasks)
        completed = sum(1 for t in mock_tasks if t.get("status") == "Done" or int(t.get("progress", 0) or 0) >= 100)
        at_risk   = sum(1 for t in mock_tasks if t.get("risk") in ("High","Critical"))
        today = date.today(); week_end = today + timedelta(days=7)
        due_week  = sum(1 for t in mock_tasks if (d := parse_due_date(t.get("due_date",""))) and today <= d <= week_end)
        for val, lbl, fg, bg in [(str(total),"Total Tasks","#4f46e5","#eef2ff"),(str(completed),"Completed","#22c55e","#f0fdf4"),(str(at_risk),"At Risk","#f97316","#fff7ed"),(str(due_week),"Due This Week","#eab308","#fefce8")]:
            card = QFrame(); card.setStyleSheet("background:white;border:none;border-radius:14px;")
            cl = QHBoxLayout(card); cl.setContentsMargins(18,14,18,14); cl.setSpacing(14)
            ic = QLabel("●"); ic.setFixedSize(42,42); ic.setAlignment(Qt.AlignCenter)
            ic.setStyleSheet(f"background:{bg};color:{fg};border-radius:11px;font-size:16px;font-weight:900;")
            col = QVBoxLayout(); col.setSpacing(2)
            vl = QLabel(val); vl.setStyleSheet("font-size:24px;font-weight:800;color:#1e293b;")
            ll = QLabel(lbl); ll.setStyleSheet("font-size:12px;color:#64748b;")
            col.addWidget(vl); col.addWidget(ll)
            cl.addWidget(ic); cl.addLayout(col); cl.addStretch()
            self._stats_row.addWidget(card)

    def _render_task_rows(self):
        while self._task_rows_layout.count():
            item = self._task_rows_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        for t in mock_tasks:
            row = TaskRow(t)
            row.double_clicked.connect(self.task_double_clicked.emit)
            self._task_rows_layout.addWidget(row)
            line = QFrame(); line.setFixedHeight(1); line.setStyleSheet("background-color:#e2e8f0;border:none;")
            self._task_rows_layout.addWidget(line)

    def refresh_tasks(self):
        self._render_stats()
        self._refresh_analysis_cards()
        self._render_task_rows()

    def _replace_draggable_content(self, dw: DraggableWidget, new_widget: QWidget):
        old_widget = dw._inner
        if old_widget is not None:
            dw.layout().removeWidget(old_widget)
            old_widget.deleteLater()
        dw._inner = new_widget
        dw.layout().addWidget(new_widget)

    def _refresh_analysis_cards(self):
        self._replace_draggable_content(self._dw_gauge, self._build_gauge_card())
        self._replace_draggable_content(self._dw_dim, self._build_dimension_card())
        self._replace_draggable_content(self._dw_summary, self._build_summary_card())


# =====================================================================
# StablePopupComboBox
# =====================================================================
class StablePopupComboBox(QComboBox):
    """QComboBox that always shows popup directly below the field."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._popup_open = False

    def showPopup(self):
        self._popup_open = True
        self.update()
        super().showPopup()
        popup = self.view().window()
        if popup is not None:
            popup.move(self.mapToGlobal(QPoint(0, self.height())))

    def hidePopup(self):
        super().hidePopup()
        self._popup_open = False
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)

        # Arrow color follows focus state for better visual feedback.
        color = QColor("#4f46e5") if self.hasFocus() else QColor("#64748b")
        p.setBrush(color)

        cx = self.width() - 18
        cy = self.height() // 2
        size = 4
        if self._popup_open:
            pts = [QPoint(cx - size, cy + 1), QPoint(cx + size, cy + 1), QPoint(cx, cy - size)]
        else:
            pts = [QPoint(cx - size, cy - 1), QPoint(cx + size, cy - 1), QPoint(cx, cy + size)]
        p.drawPolygon(pts)


# =====================================================================
# TaskTablePage
# =====================================================================
class TaskTablePage(QWidget):
    new_task_requested = Signal()
    task_double_clicked = Signal(dict)

    def __init__(self):
        super().__init__()
        self.setStyleSheet("background: #f8fafc;")
        main = QVBoxLayout(self); main.setContentsMargins(40,30,40,30); main.setSpacing(20)

        h = QHBoxLayout()
        title = QLabel("Task Table"); title.setStyleSheet("font-size:28px;font-weight:bold;color:#334155;")
        self.btn_analyze  = QPushButton("🔍 Analyze Risk")
        self.btn_analyze.setCursor(Qt.PointingHandCursor)
        self.btn_analyze.setStyleSheet("background:#4f46e5;color:white;border:none;border-radius:8px;padding:8px 16px;font-weight:bold;font-size:13px;")
        self.btn_analyze.clicked.connect(lambda: AnalyzeRiskDialog(self).exec())
        self.btn_new_task = QPushButton("+ New Task")
        self.btn_new_task.setCursor(Qt.PointingHandCursor)
        self.btn_new_task.setStyleSheet("background:white;color:#4f46e5;border:1.5px solid #4f46e5;border-radius:8px;padding:8px 20px;font-weight:bold;font-size:13px;")
        h.addWidget(title); h.addStretch(); h.addWidget(self.btn_analyze); h.addWidget(self.btn_new_task)
        main.addLayout(h)

        divider = QFrame(); divider.setFixedHeight(1); divider.setStyleSheet("background-color:#cbd5e1;border:none;")
        main.addWidget(divider)

        # ── Dropdown Filters ──────────────────────────────────────────
        self._filter_status = ""   # "" = All
        self._filter_risk   = ""
        self._filter_due    = ""

        _dd_style = (
            "QComboBox {"
            "  background: white; color: #334155; border: 1px solid #cbd5e1;"
            "  border-radius: 8px; padding: 0 12px; font-size: 13px; font-weight: 500;"
            "  min-width: 120px; height: 34px;"
            "}"
            "QComboBox:hover { border-color: #94a3b8; }"
            "QComboBox::drop-down { border: none; width: 24px; }"
            "QComboBox::down-arrow { image: none; width: 0; height: 0; }"
            "QComboBox QAbstractItemView {"
            "  background: white; border: 1px solid #cbd5e1; border-radius: 8px;"
            "  selection-background-color: #eef2ff; selection-color: #4f46e5;"
            "  padding: 4px; outline: none; font-size: 13px;"
            "}"
            "QComboBox QAbstractItemView::item { height: 32px; padding-left: 12px; }"
        )

        f = QHBoxLayout(); f.setSpacing(10)

        self.dd_status = StablePopupComboBox()
        self.dd_status.addItem("Status")
        for s in ["To do", "In Progress", "Done"]:
            self.dd_status.addItem(s)
        self.dd_status.setStyleSheet(_dd_style)
        self.dd_status.setCursor(Qt.PointingHandCursor)

        self.dd_risk = StablePopupComboBox()
        self.dd_risk.addItem("Risk")
        for r in ["Critical", "High", "Medium", "Low"]:
            self.dd_risk.addItem(r)
        self.dd_risk.setStyleSheet(_dd_style)
        self.dd_risk.setCursor(Qt.PointingHandCursor)

        self.dd_due = StablePopupComboBox()
        self.dd_due.addItem("Due")
        for d in ["Today", "Tomorrow", "This Week", "Next Week", "This Month", "No Due Date"]:
            self.dd_due.addItem(d)
        self.dd_due.setStyleSheet(_dd_style)
        self.dd_due.setCursor(Qt.PointingHandCursor)

        f.addWidget(self.dd_status)
        f.addWidget(self.dd_risk)
        f.addWidget(self.dd_due)
        f.addStretch()
        main.addLayout(f)

        box = QFrame(); box.setObjectName("tableBox2")
        box.setStyleSheet("#tableBox2{background:white;border:1px solid #cbd5e1;border-radius:16px;}")
        self.tbl_main_layout = QVBoxLayout(box); self.tbl_main_layout.setContentsMargins(0,0,0,0); self.tbl_main_layout.setSpacing(0)

        head_frame = QFrame()
        head_frame.setStyleSheet("background-color:#f8fafc;border-bottom:1px solid #cbd5e1;border-top-left-radius:16px;border-top-right-radius:16px;")
        head_frame.setFixedHeight(46)
        hl = QGridLayout(head_frame); hl.setContentsMargins(25,0,25,0); hl.setHorizontalSpacing(20)
        for i, s in enumerate([4,3,2,1,1]): hl.setColumnStretch(i, s)
        for i, text in enumerate(["Task","Progress","Status","Risk","Due"]):
            lb = QLabel(text); lb.setStyleSheet("color:#64748b;font-size:13px;font-weight:bold;border:none;background:transparent;")
            hl.addWidget(lb, 0, i, alignment=Qt.AlignVCenter|(Qt.AlignLeft if text=="Task" else Qt.AlignCenter))
        self.tbl_main_layout.addWidget(head_frame)

        self.task_list_container = QWidget()
        self.task_list_container.setStyleSheet("background: white; border: none;")
        self.task_list_layout    = QVBoxLayout(self.task_list_container)
        self.task_list_layout.setContentsMargins(0,0,0,0); self.task_list_layout.setSpacing(0); self.task_list_layout.setAlignment(Qt.AlignTop)
        self.tbl_main_layout.addWidget(self.task_list_container)

        eb = QFrame(); eb.setSizePolicy(QSizePolicy.Preferred,QSizePolicy.Expanding); eb.setMinimumHeight(130); eb.setStyleSheet("background: transparent; border: none;")
        self.tbl_main_layout.addWidget(eb); main.addWidget(box)

        # connect dropdowns
        self.dd_status.currentIndexChanged.connect(self._on_dropdown_changed)
        self.dd_risk.currentIndexChanged.connect(self._on_dropdown_changed)
        self.dd_due.currentIndexChanged.connect(self._on_dropdown_changed)
        self._apply_dropdown_filter()

    # ── helpers to style active dropdown ─────────────────────────
    _DD_BASE = (
        "QComboBox {"
        "  background: white; color: #334155; border: 1px solid #cbd5e1;"
        "  border-radius: 8px; padding: 0 12px; font-size: 13px; font-weight: 500;"
        "  min-width: 120px; height: 34px;"
        "}"
        "QComboBox:hover { border-color: #94a3b8; }"
        "QComboBox::drop-down { border: none; width: 24px; }"
        "QComboBox::down-arrow { image: none; width: 0; height: 0; }"
        "QComboBox QAbstractItemView {"
        "  background: white; border: 1px solid #cbd5e1; border-radius: 8px;"
        "  selection-background-color: #eef2ff; selection-color: #4f46e5;"
        "  padding: 4px; outline: none; font-size: 13px;"
        "}"
        "QComboBox QAbstractItemView::item { height: 32px; padding-left: 12px; }"
    )
    _DD_ACTIVE = (
        "QComboBox {"
        "  background: #eef2ff; color: #4f46e5; border: 1.5px solid #4f46e5;"
        "  border-radius: 8px; padding: 0 12px; font-size: 13px; font-weight: 600;"
        "  min-width: 120px; height: 34px;"
        "}"
        "QComboBox:hover { border-color: #4338ca; }"
        "QComboBox::drop-down { border: none; width: 24px; }"
        "QComboBox::down-arrow { image: none; width: 0; height: 0; }"
        "QComboBox QAbstractItemView {"
        "  background: white; border: 1px solid #cbd5e1; border-radius: 8px;"
        "  selection-background-color: #eef2ff; selection-color: #4f46e5;"
        "  padding: 4px; outline: none; font-size: 13px;"
        "}"
        "QComboBox QAbstractItemView::item { height: 32px; padding-left: 12px; }"
    )

    def _on_dropdown_changed(self):
        # Status: index 0 = placeholder "Status" → no filter
        si = self.dd_status.currentIndex()
        self._filter_status = self.dd_status.currentText() if si > 0 else ""
        ri = self.dd_risk.currentIndex()
        self._filter_risk = self.dd_risk.currentText() if ri > 0 else ""
        di = self.dd_due.currentIndex()
        self._filter_due = self.dd_due.currentText() if di > 0 else ""

        # Style active dropdowns
        self.dd_status.setStyleSheet(self._DD_ACTIVE if self._filter_status else self._DD_BASE)
        self.dd_risk.setStyleSheet(self._DD_ACTIVE if self._filter_risk else self._DD_BASE)
        self.dd_due.setStyleSheet(self._DD_ACTIVE if self._filter_due else self._DD_BASE)

        self._apply_dropdown_filter()

    def _apply_dropdown_filter(self):
        while self.task_list_layout.count():
            c = self.task_list_layout.takeAt(0)
            if c.widget(): c.widget().deleteLater()

        today = date.today()
        filtered = list(mock_tasks)

        # Status filter
        if self._filter_status:
            filtered = [t for t in filtered if t.get("status","") == self._filter_status]

        # Risk filter
        if self._filter_risk:
            filtered = [t for t in filtered if t.get("risk","") == self._filter_risk]

        # Due filter
        if self._filter_due:
            tomorrow   = today + timedelta(days=1)
            week_end   = today + timedelta(days=6)
            next_w_start = today + timedelta(days=7)
            next_w_end   = today + timedelta(days=13)
            month_end  = date(today.year, today.month + 1 if today.month < 12 else 1,
                              1) - timedelta(days=1) if today.month < 12 else date(today.year, 12, 31)
            def _due_match(t):
                dd = parse_due_date(t.get("due_date",""))
                if self._filter_due == "Today":
                    return dd == today
                elif self._filter_due == "Tomorrow":
                    return dd == tomorrow
                elif self._filter_due == "This Week":
                    return dd and today <= dd <= week_end
                elif self._filter_due == "Next Week":
                    return dd and next_w_start <= dd <= next_w_end
                elif self._filter_due == "This Month":
                    return dd and dd.month == today.month and dd.year == today.year
                elif self._filter_due == "No Due Date":
                    return not dd
                return True
            filtered = [t for t in filtered if _due_match(t)]

        for t in filtered:
            row = TaskRow(t)
            row.double_clicked.connect(self.task_double_clicked.emit)
            self.task_list_layout.addWidget(row)
            line = QFrame(); line.setFixedHeight(1); line.setStyleSheet("background-color:#e2e8f0;border:none;")
            self.task_list_layout.addWidget(line)

    # keep old apply_filter for compatibility (called nowhere now but safe)
    def apply_filter(self, cat, active_btn=None):
        self._apply_dropdown_filter()

    def refresh_tasks(self):
        self._apply_dropdown_filter()


# =====================================================================
# AlertCard  — สีขอบ/badge ดึงจาก RISK_STYLE_MAP (ตรงกันทุกหน้า)
# =====================================================================
class AlertCard(QFrame):
    view_task_clicked = Signal(int)
    dismiss_clicked   = Signal(int)

    def __init__(self, alert_data: dict, parent=None):
        super().__init__(parent)
        self.alert_id = alert_data.get("id", 0)
        self._is_read = alert_data.get("read", False)
        self._severity = alert_data.get("severity", "Medium")
        self._build_ui(alert_data)

    def _build_ui(self, data: dict):
        self.setObjectName("alertCard")
        self._apply_card_style(self._severity, self._is_read)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 18)
        outer.setSpacing(14)

        icon_lbl = QLabel(data.get("icon", "🔔"))
        icon_lbl.setFont(QFont("Segoe UI Emoji", 20))
        icon_lbl.setFixedSize(36, 36)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("background:transparent;")
        outer.addWidget(icon_lbl, alignment=Qt.AlignTop)

        content = QVBoxLayout(); content.setSpacing(4)

        title_row = QHBoxLayout()
        title_lbl = QLabel(data.get("title", ""))
        title_lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
        title_lbl.setStyleSheet("color:#111827;")
        title_lbl.setWordWrap(True)
        title_row.addWidget(title_lbl); title_row.addStretch()

        # badge สีดึงจาก RISK_BADGE_COLOR → ตรงกับ TaskRow ทุกหน้า
        badge_color = RISK_BADGE_COLOR.get(self._severity, "#eab308")
        badge_dot   = QLabel(f"● {self._severity}")
        badge_dot.setFont(QFont("Segoe UI", 10, QFont.Bold))
        badge_dot.setStyleSheet(f"color:{badge_color};")
        badge_dot.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        title_row.addWidget(badge_dot)
        content.addLayout(title_row)

        desc_lbl = QLabel(data.get("description", ""))
        desc_lbl.setFont(QFont("Segoe UI", 9))
        desc_lbl.setStyleSheet("color:#374151;")
        desc_lbl.setWordWrap(True)
        content.addWidget(desc_lbl)

        meta_lbl = QLabel(data.get("meta", ""))
        meta_lbl.setFont(QFont("Segoe UI", 8))
        meta_lbl.setStyleSheet("color:#9CA3AF;")
        content.addWidget(meta_lbl)

        btn_row = QHBoxLayout(); btn_row.setSpacing(8); btn_row.setContentsMargins(0, 6, 0, 0)
        _P = "QPushButton{background-color:#4F46E5;color:white;border:none;border-radius:8px;padding:7px 18px;font-size:11px;font-weight:bold;} QPushButton:hover{background-color:#4338CA;}"
        _S = "QPushButton{background-color:white;color:#374151;border:1.5px solid #D1D5DB;border-radius:8px;padding:7px 18px;font-size:11px;} QPushButton:hover{background-color:#F9FAFB;}"
        view_btn    = QPushButton("View Task");  view_btn.setStyleSheet(_P);  view_btn.setCursor(Qt.PointingHandCursor)
        dismiss_btn = QPushButton("Dismiss");    dismiss_btn.setStyleSheet(_S); dismiss_btn.setCursor(Qt.PointingHandCursor)
        view_btn.clicked.connect(lambda: self.view_task_clicked.emit(self.alert_id))
        dismiss_btn.clicked.connect(lambda: self.dismiss_clicked.emit(self.alert_id))
        btn_row.addWidget(view_btn); btn_row.addWidget(dismiss_btn); btn_row.addStretch()
        content.addLayout(btn_row)
        outer.addLayout(content)

    def _apply_card_style(self, severity: str, is_read: bool):
        border_color = RISK_BADGE_COLOR.get(severity, "#E5E7EB")
        if is_read:
            self.setStyleSheet(f"QFrame#alertCard{{background-color:#FFFFFF;border:1px solid #E5E7EB;border-left:3px solid {border_color}60;border-radius:12px;}}")
        else:
            self.setStyleSheet(f"QFrame#alertCard{{background-color:#F1F3F5;border:1px solid #CBD5E1;border-left:4px solid {border_color};border-radius:12px;}}")

    def mark_as_read(self, severity: str = "Medium"):
        self._is_read = True
        self._apply_card_style(severity, is_read=True)


# =====================================================================
# _AutoExpandTextEdit
# =====================================================================
class _AutoExpandTextEdit(QTextEdit):
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self.setPlainText(text)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.document().contentsChanged.connect(self._adjust)

    def _adjust(self):
        doc = self.document()
        doc.setTextWidth(self.viewport().width() or 340)
        self.setFixedHeight(max(int(doc.size().height()) + 20, 44))

    def showEvent(self, e):
        super().showEvent(e); self._adjust()


# =====================================================================
# EditTaskDialog
# =====================================================================
class EditTaskDialog(QDialog):
    task_saved = Signal(dict)
    RISK_LEVELS = ["Low", "Medium", "High", "Critical"]
    RISK_COLORS = {
        "Low":      ("#16A34A","#DCFCE7","#BBF7D0"),
        "Medium":   ("#D97706","#FEF3C7","#FDE68A"),
        "High":     ("#EA580C","#FFEDD5","#FED7AA"),
        "Critical": ("#DC2626","#FEE2E2","#FECACA"),
    }

    def __init__(self, task_data: dict, parent=None):
        super().__init__(parent)
        self.task_data = dict(task_data)
        self._selected_risk = task_data.get("severity", task_data.get("risk", "Low"))
        self._risk_btns: dict[str, QPushButton] = {}
        self.setWindowTitle("Edit Task"); self.setModal(True); self.setFixedWidth(420)
        self.setStyleSheet("QDialog{background-color:#FFFFFF;border-radius:16px;}")
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(28,24,28,24); root.setSpacing(0)
        tr = QHBoxLayout()
        for t, s in [("+","color:#111827;background:transparent;border:none;font-size:16px;font-weight:bold;"),("Edit Task","color:#111827;background:transparent;border:none;font-size:15px;font-weight:bold;")]:
            l = QLabel(t); l.setFont(QFont("Segoe UI",16 if t=="+" else 15,QFont.Bold)); l.setStyleSheet(s); tr.addWidget(l)
        tr.addStretch(); root.addLayout(tr); root.addSpacing(20)

        root.addWidget(self._sl("Task Name")); root.addSpacing(6)
        self._name_edit = QLineEdit(self.task_data.get("title",""))
        self._name_edit.setStyleSheet(self._is(bold=True)); self._name_edit.setFixedHeight(40); root.addWidget(self._name_edit); root.addSpacing(16)

        root.addWidget(self._sl("Progress")); root.addSpacing(6)
        progress_row = QHBoxLayout()
        progress_value = int(self.task_data.get("progress", 0) or 0)
        self._progress_value_lbl = QLabel(f"{progress_value}%")
        self._progress_value_lbl.setStyleSheet("font-size:12px;font-weight:700;color:#4f46e5;")
        progress_row.addWidget(self._progress_value_lbl)
        progress_row.addStretch()
        root.addLayout(progress_row)
        self._progress_slider = QSlider(Qt.Horizontal)
        self._progress_slider.setRange(0, 100)
        self._progress_slider.setValue(progress_value)

        def _sync_edit_progress(v: int) -> None:
            c = progress_bar_color(v)
            self._progress_value_lbl.setText(f"{v}%")
            self._progress_value_lbl.setStyleSheet(f"font-size:12px;font-weight:700;color:{c};")
            self._progress_slider.setStyleSheet(progress_slider_stylesheet(c, groove="#e5e7eb"))

        self._progress_slider.valueChanged.connect(_sync_edit_progress)
        _sync_edit_progress(self._progress_slider.value())
        root.addWidget(self._progress_slider); root.addSpacing(16)

        root.addWidget(self._sl("Description")); root.addSpacing(6)
        self._desc_edit = _AutoExpandTextEdit(self.task_data.get("description",""))
        self._desc_edit.setStyleSheet(self._is(multiline=True)); root.addWidget(self._desc_edit); root.addSpacing(16)

        root.addWidget(self._sl("Role")); root.addSpacing(6)
        self._role_edit = QLineEdit(self.task_data.get("role",""))
        self._role_edit.setStyleSheet(self._is()); self._role_edit.setFixedHeight(40); root.addWidget(self._role_edit); root.addSpacing(16)

        root.addWidget(self._sl("Due Date")); root.addSpacing(6); root.addWidget(self._build_date_row()); root.addSpacing(16)
        root.addWidget(self._sl("Risk Level")); root.addSpacing(10); root.addLayout(self._build_risk_row()); root.addSpacing(28)
        root.addLayout(self._build_bottom_buttons())

    def _build_date_row(self):
        c = QWidget(); c.setObjectName("dateContainer")
        c.setStyleSheet("QWidget#dateContainer{background-color:#FFFFFF;border:1.5px solid #D1D5DB;border-radius:10px;}"); c.setFixedHeight(40)
        h = QHBoxLayout(c); h.setContentsMargins(12,0,10,0); h.setSpacing(6)
        due_str = self.task_data.get("due_date","")
        self._parsed_date = QDate.currentDate()
        for fmt in ["MMM dd yyyy","MMM d yyyy","dd/MM/yyyy","MM/dd/yyyy","yyyy-MM-dd"]:
            d = QDate.fromString(due_str, fmt)
            if d.isValid(): self._parsed_date = d; break
        self._date_line = QLineEdit(self._parsed_date.toString("dd/MM/yyyy"))
        self._date_line.setPlaceholderText("dd/MM/yyyy")
        self._date_line.setStyleSheet("QLineEdit{background:transparent;border:none;font-size:13px;color:#374151;}")
        h.addWidget(self._date_line, stretch=1)
        cal_btn = QPushButton("📅"); cal_btn.setFixedSize(26,26); cal_btn.setFont(QFont("Segoe UI Emoji",11))
        cal_btn.setStyleSheet("QPushButton{background:transparent;border:none;} QPushButton:hover{background:#F3F4F6;border-radius:5px;}")
        cal_btn.setCursor(Qt.PointingHandCursor); cal_btn.clicked.connect(self._show_calendar); h.addWidget(cal_btn)
        return c

    def _build_risk_row(self):
        frame = QFrame(); frame.setObjectName("riskFrame"); frame.setFixedHeight(44)
        frame.setStyleSheet("QFrame#riskFrame{background-color:#F3F4F6;border:1px solid #E5E7EB;border-radius:10px;}")
        row = QHBoxLayout(frame); row.setContentsMargins(4,4,4,4); row.setSpacing(2)
        for level in self.RISK_LEVELS:
            btn = QPushButton(level); btn.setFixedHeight(34); btn.setCursor(Qt.PointingHandCursor); btn.setCheckable(True)
            btn.clicked.connect(lambda checked, lv=level: self._select_risk(lv))
            self._risk_btns[level] = btn; row.addWidget(btn)
        self._select_risk(self._selected_risk)
        outer = QHBoxLayout(); outer.setContentsMargins(0,0,0,0); outer.addWidget(frame); return outer

    def _select_risk(self, level: str):
        self._selected_risk = level
        for lv, btn in self._risk_btns.items():
            fg, bg, _ = self.RISK_COLORS[lv]
            if lv == level:
                btn.setStyleSheet(f"QPushButton{{background-color:{bg};color:{fg};border:1.5px solid {fg};border-radius:8px;font-size:11px;font-weight:bold;padding:0 10px;}}")
            else:
                btn.setStyleSheet(f"QPushButton{{background-color:transparent;color:{fg};border:none;border-radius:8px;font-size:11px;padding:0 10px;}} QPushButton:hover{{background-color:{bg};}}")

    def _build_bottom_buttons(self):
        row = QHBoxLayout(); row.setSpacing(12); row.addStretch()
        cancel_btn = QPushButton("Cancel"); cancel_btn.setFixedSize(110,40); cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet("QPushButton{background:white;color:#374151;border:1.5px solid #D1D5DB;border-radius:10px;font-size:12px;} QPushButton:hover{background:#F9FAFB;}")
        cancel_btn.clicked.connect(self.reject); row.addWidget(cancel_btn)
        save_btn = QPushButton("Edit Task"); save_btn.setFixedSize(120,40); save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet("QPushButton{background:#4F46E5;color:white;border:none;border-radius:10px;font-size:12px;font-weight:bold;} QPushButton:hover{background:#4338CA;}")
        save_btn.clicked.connect(self._on_save); row.addWidget(save_btn); return row

    def _show_calendar(self):
        from PySide6.QtCore import QLocale
        popup = QDialog(self); popup.setWindowTitle("")
        popup.setWindowFlags(Qt.Popup|Qt.FramelessWindowHint)
        popup.setStyleSheet("QDialog{background:white;border:1px solid #D1D5DB;border-radius:10px;}")
        cal = QCalendarWidget(popup); cal.setLocale(QLocale(QLocale.English))
        cal.setGridVisible(False); cal.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader); cal.setNavigationBarVisible(True)
        d = QDate.fromString(self._date_line.text().strip(),"dd/MM/yyyy")
        if d.isValid(): cal.setSelectedDate(d)
        def on_sel(dt: QDate): self._date_line.setText(dt.toString("dd/MM/yyyy")); popup.close()
        cal.clicked.connect(on_sel)
        v = QVBoxLayout(popup); v.setContentsMargins(8,8,8,8); v.addWidget(cal)
        popup.adjustSize(); popup.move(self._date_line.mapToGlobal(self._date_line.rect().bottomLeft())); popup.exec()

    def _sl(self, text):
        l = QLabel(text); l.setFont(QFont("Segoe UI",11,QFont.Bold)); l.setStyleSheet("color:#374151;background:transparent;border:none;"); return l

    def _is(self, multiline=False, bold=False):
        w   = "QTextEdit" if multiline else "QLineEdit"
        pad = "8px 12px" if not multiline else "10px 12px"
        wt  = "bold" if bold else "normal"
        return f"{w}{{background-color:#FFFFFF;border:1.5px solid #D1D5DB;border-radius:10px;padding:{pad};font-size:13px;font-weight:{wt};color:#111827;}} {w}:focus{{border-color:#4F46E5;}}"

    def _on_save(self):
        updated = dict(self.task_data)
        updated["title"]       = self._name_edit.text().strip()
        updated["description"] = self._desc_edit.toPlainText().strip()
        updated["role"]        = self._role_edit.text().strip()
        updated["due_date"]    = self._date_line.text().strip()
        updated["progress"]    = self._progress_slider.value()
        updated["severity"]    = self._selected_risk
        updated["risk"]        = self._selected_risk   # keep in sync
        self.task_saved.emit(updated); self.accept()


# =====================================================================
# TaskDetailPage
# =====================================================================
class TaskDetailPage(QWidget):
    task_saved = Signal(dict)
    task_deleted = Signal(int)

    def __init__(self, task_data: dict, username="User"):
        super().__init__()
        self.task_data = dict(task_data)
        self.username  = username
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet("background-color:#F3F4F6;")
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        body = QHBoxLayout(); body.setContentsMargins(0,0,0,0); body.setSpacing(0)
        body.addWidget(self._build_main_area(), stretch=1); root.addLayout(body)

    def _build_main_area(self):
        c = QWidget(); c.setStyleSheet("background-color:#F3F4F6;")
        layout = QVBoxLayout(c); layout.setContentsMargins(28,8,28,24); layout.setSpacing(16)
        layout.addLayout(self._build_topbar()); layout.addWidget(self._build_task_card()); layout.addStretch()
        return c

    def _build_topbar(self):
        row = QHBoxLayout()
        row.addStretch()
        return row

    def _build_task_card(self):
        card = QFrame(); card.setObjectName("taskCard")
        card.setStyleSheet("QFrame#taskCard{background:white;border:1px solid #E5E7EB;border-radius:12px;} QFrame#taskCard QLabel{border:none;background:transparent;} QFrame#taskCard QProgressBar{border:none;}")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QVBoxLayout(card); layout.setContentsMargins(24,20,24,20); layout.setSpacing(14)

        row1 = QHBoxLayout(); row1.setSpacing(10)
        title_lbl = QLabel(self.task_data.get("title",""))
        title_lbl.setFont(QFont("Segoe UI",13,QFont.Bold)); title_lbl.setStyleSheet("color:#111827;"); title_lbl.setWordWrap(True)
        row1.addWidget(title_lbl, stretch=1)

        status_raw = self.task_data.get("status","To do")
        status_cfg = STATUS_STYLE_MAP.get(status_raw, STATUS_STYLE_MAP["To do"])
        status_lbl = QLabel(f"  {status_raw}  ")
        status_lbl.setFont(QFont("Segoe UI",9,QFont.Bold))
        status_lbl.setStyleSheet(
            status_cfg["status_style"] + "border-radius:8px;padding:2px 10px;"
        )
        status_lbl.setFixedWidth(status_cfg["status_width"] + 24)
        status_lbl.setAlignment(Qt.AlignCenter)
        status_lbl.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        row1.addWidget(status_lbl, alignment=Qt.AlignVCenter)

        # severity — ดึงจาก RISK_BADGE_COLOR ให้ตรงทุกหน้า
        severity    = self.task_data.get("severity", self.task_data.get("risk","Medium"))
        risk_color  = RISK_BADGE_COLOR.get(severity, "#eab308")
        risk_lbl    = QLabel(f"● {severity}")
        risk_lbl.setFont(QFont("Segoe UI",10,QFont.Bold))
        risk_lbl.setStyleSheet(f"color:{risk_color};padding:0 4px;")
        row1.addWidget(risk_lbl, alignment=Qt.AlignVCenter)
        layout.addLayout(row1)

        project_lbl = QLabel(f"Project: {self.task_data.get('project','')}")
        project_lbl.setFont(QFont("Segoe UI",9)); project_lbl.setStyleSheet("color:#9CA3AF;"); layout.addWidget(project_lbl)

        ph = QHBoxLayout()
        pl = QLabel("Completion Progress"); pl.setFont(QFont("Segoe UI",10,QFont.Bold)); pl.setStyleSheet("color:#111827;"); ph.addWidget(pl)
        tid_lbl = QLabel(f"#{self.task_data.get('id',self.task_data.get('task_id',1)):02d}")
        tid_lbl.setFont(QFont("Segoe UI",10,QFont.Bold)); tid_lbl.setStyleSheet("color:#4F46E5;"); ph.addWidget(tid_lbl); ph.addStretch()
        layout.addLayout(ph)

        br = QHBoxLayout(); br.setSpacing(12)
        pv = int(self.task_data.get("progress", 0) or 0)
        pc = progress_bar_color(pv)
        bar = QProgressBar(); bar.setRange(0,100); bar.setValue(pv); bar.setFixedHeight(10); bar.setTextVisible(False)
        bar.setStyleSheet(f"QProgressBar{{background-color:#E5E7EB;border-radius:5px;border:none;}} QProgressBar::chunk{{background-color:{pc};border-radius:5px;}}")
        br.addWidget(bar, stretch=1)
        pct_lbl = QLabel(str(pv)); pct_lbl.setFont(QFont("Segoe UI",11,QFont.Bold)); pct_lbl.setStyleSheet(f"color:{pc};"); pct_lbl.setFixedWidth(36); pct_lbl.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        br.addWidget(pct_lbl); layout.addLayout(br)

        dt = QLabel("Description"); dt.setFont(QFont("Segoe UI",10,QFont.Bold)); dt.setStyleSheet("color:#111827;"); layout.addWidget(dt)
        dl = QLabel(self.task_data.get("description",""))
        dl.setFont(QFont("Segoe UI",9)); dl.setStyleSheet("color:#374151;"); dl.setWordWrap(True); layout.addWidget(dl)

        dut = QLabel("Due Date"); dut.setFont(QFont("Segoe UI",10,QFont.Bold)); dut.setStyleSheet("color:#111827;"); layout.addWidget(dut)
        dur = QHBoxLayout(); dur.setSpacing(6)
        cl = QLabel("📅"); cl.setFont(QFont("Segoe UI Emoji",11)); dur.addWidget(cl)
        dv = QLabel(self.task_data.get("due_date","—")); dv.setFont(QFont("Segoe UI",9)); dv.setStyleSheet("color:#374151;"); dur.addWidget(dv); dur.addStretch()
        layout.addLayout(dur)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        del_btn = QPushButton("Delete Task")
        del_btn.setFixedHeight(34)
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setStyleSheet(
            "QPushButton{background:#FFFFFF;color:#DC2626;border:1.5px solid #FCA5A5;border-radius:8px;padding:0 18px;font-size:11px;font-weight:bold;}"
            "QPushButton:hover{background:#FEF2F2;border-color:#EF4444;}"
        )
        del_btn.clicked.connect(self._on_delete_clicked)
        btn_row.addWidget(del_btn)
        edit_btn = QPushButton("Edit Task"); edit_btn.setFixedHeight(34); edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.setStyleSheet("QPushButton{background:#4F46E5;color:white;border:none;border-radius:8px;padding:0 22px;font-size:11px;font-weight:bold;} QPushButton:hover{background:#4338CA;}")
        edit_btn.clicked.connect(self._open_edit_dialog); btn_row.addWidget(edit_btn); layout.addLayout(btn_row)
        return card

    def _open_edit_dialog(self):
        dlg = EditTaskDialog(self.task_data, parent=self)
        dlg.task_saved.connect(self._on_dialog_saved); dlg.exec()

    def _on_dialog_saved(self, updated: dict):
        self.task_saved.emit(updated)

    def _on_delete_clicked(self):
        tid = self.task_data.get("task_id", self.task_data.get("id"))
        if tid is None:
            return
        ans = QMessageBox.question(
            self,
            "Delete Task",
            "Are you sure you want to delete this task?\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if ans == QMessageBox.Yes:
            self.task_deleted.emit(int(tid))


# =====================================================================
# TaskDetailWindow
# =====================================================================
class TaskDetailWindow(QMainWindow):
    alert_task_saved = Signal(dict)
    alert_task_deleted = Signal(int)

    def __init__(self, task_data: dict, username="User"):
        super().__init__()
        self.setWindowTitle("View Task"); self.resize(900, 600)
        self._username = username; self._load_page(task_data)

    def _load_page(self, task_data: dict):
        page = TaskDetailPage(task_data, self._username)
        page.task_saved.connect(self._on_task_saved)
        page.task_deleted.connect(self._on_task_deleted)
        self.setCentralWidget(page)

    def _on_task_saved(self, updated: dict):
        self.alert_task_saved.emit(updated); self._load_page(updated)

    def _on_task_deleted(self, task_id: int):
        self.alert_task_deleted.emit(task_id)
        self.close()


# =====================================================================
# AlertPage  — ใช้ logic จากไฟล์ reference (สมบูรณ์)
# =====================================================================
class AlertPage(QWidget):
    task_updated = Signal()

    def __init__(self, username="User", parent=None):
        super().__init__(parent)
        self.username = username
        self._alerts: list[dict]          = db_load()
        self._cards:  dict[int, AlertCard] = {}
        self._open_windows: dict[int, TaskDetailWindow] = {}
        self.current_filter = "All"
        self._build_ui()
        self._rebuild_all_cards()
        self._apply_filter()

    def _build_ui(self):
        self.setStyleSheet("background-color:#F3F4F6;")
        main = QVBoxLayout(self); main.setContentsMargins(40,30,40,30); main.setSpacing(20)

        h = QHBoxLayout()
        title = QLabel("Alert"); title.setStyleSheet("font-size:28px;font-weight:bold;color:#334155;"); h.addWidget(title); h.addStretch()
        self.btn_new_task = None
        for text, style in [
            ("🔍  Analyze Risk","QPushButton{background:#4f46e5;color:white;border:none;border-radius:8px;padding:0 14px;font-size:13px;font-weight:bold;} QPushButton:hover{background:#4338ca;}"),
            ("+ New Task","QPushButton{background:white;color:#4F46E5;border:1.5px solid #4F46E5;border-radius:8px;padding:0 16px;font-size:13px;font-weight:bold;} QPushButton:hover{background:#eef2ff;}"),
        ]:
            b = QPushButton(text)
            b.setFixedHeight(34)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(style)
            if text == "+ New Task":
                self.btn_new_task = b
            elif "Analyze" in text:
                b.clicked.connect(lambda: AnalyzeRiskDialog(self).exec())
            h.addWidget(b)
        main.addLayout(h)

        divider = QFrame(); divider.setFixedHeight(1); divider.setStyleSheet("background-color:#cbd5e1;border:none;"); main.addWidget(divider)

        filter_row = QHBoxLayout(); filter_row.setSpacing(8)
        self._filter_buttons: dict[str, QPushButton] = {}
        for f in ["All","Unread","Read"]:
            btn = QPushButton(f); btn.setFixedHeight(34); btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, key=f: self._set_filter(key))
            self._filter_buttons[f] = btn; filter_row.addWidget(btn)
        filter_row.addStretch()
        dismiss_all_btn = QPushButton("Dismiss All"); dismiss_all_btn.setFixedHeight(34); dismiss_all_btn.setCursor(Qt.PointingHandCursor)
        dismiss_all_btn.setStyleSheet("QPushButton{background:#EF4444;color:white;border:none;border-radius:8px;padding:0 16px;font-size:12px;font-weight:bold;} QPushButton:hover{background:#DC2626;}")
        dismiss_all_btn.clicked.connect(self._on_dismiss_all); filter_row.addWidget(dismiss_all_btn)
        main.addLayout(filter_row)

        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background:transparent;"); scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._cards_container = QWidget(); self._cards_container.setStyleSheet("background:transparent;")
        self._cards_layout    = QVBoxLayout(self._cards_container)
        self._cards_layout.setContentsMargins(0,0,0,0); self._cards_layout.setSpacing(14); self._cards_layout.addStretch()
        scroll.setWidget(self._cards_container); main.addWidget(scroll)
        self._update_filter_styles()

    def _rebuild_all_cards(self):
        for card in self._cards.values():
            self._cards_layout.removeWidget(card); card.deleteLater()
        self._cards.clear()
        # Newest first (higher id = newer alert)
        self._alerts.sort(key=lambda a: a.get("id", 0), reverse=True)
        for alert in self._alerts:
            self._add_card(alert)

    def _add_card(self, alert: dict, prepend: bool = False):
        card = AlertCard(alert)
        card.view_task_clicked.connect(self._on_view_task)
        card.dismiss_clicked.connect(self._on_dismiss)
        if prepend:
            self._cards_layout.insertWidget(0, card)
        else:
            self._cards_layout.insertWidget(self._cards_layout.count() - 1, card)
        self._cards[alert["id"]] = card

    def _replace_card(self, alert_id: int, new_data: dict):
        if alert_id not in self._cards: return
        old_card = self._cards.pop(alert_id)
        old_idx  = self._cards_layout.indexOf(old_card)
        self._cards_layout.removeWidget(old_card); old_card.deleteLater()
        new_card = AlertCard(new_data)
        new_card.view_task_clicked.connect(self._on_view_task)
        new_card.dismiss_clicked.connect(self._on_dismiss)
        self._cards_layout.insertWidget(old_idx if old_idx >= 0 else self._cards_layout.count()-1, new_card)
        self._cards[alert_id] = new_card

    def _on_view_task(self, alert_id: int):
        alert_data = next((a for a in self._alerts if a["id"] == alert_id), None)
        if not alert_data: return
        if alert_data.get("dismissed", False):
            return
        if not alert_data.get("read", False):
            alert_data["read"] = True
            self._alerts = db_update_alert(alert_id, alert_data, self._alerts)
            if alert_id in self._cards:
                self._cards[alert_id].mark_as_read(alert_data.get("severity","Medium"))
            self._update_unread_count(); self._apply_filter()
        if alert_id in self._open_windows:
            win = self._open_windows[alert_id]
            if win.isVisible(): win.raise_(); win.activateWindow(); return
            else: del self._open_windows[alert_id]
        win = TaskDetailWindow(dict(alert_data), self.username)
        win.alert_task_saved.connect(self._on_task_saved_from_window)
        win.alert_task_deleted.connect(self._on_task_deleted_from_window)
        win.destroyed.connect(lambda _, aid=alert_id: self._open_windows.pop(aid, None))
        self._open_windows[alert_id] = win; win.show()

    def _on_task_saved_from_window(self, updated: dict):
        alert_id = updated.get("id")
        task_id = updated.get("task_id")

        # 1) Persist edit into tasks_db.json (mock_tasks),
        # so when alerts are rebuilt from tasks it doesn't revert.
        if task_id is not None:
            t = next((x for x in mock_tasks if x.get("id") == task_id), None)
            if t is not None:
                # Update core task fields used by UI & alert rebuild
                if "due_date" in updated:
                    t["due_date"] = updated.get("due_date", t.get("due_date", ""))

                    # Keep `due` display in sync for TaskTablePage.
                    due_date_str = str(t.get("due_date", "") or "").strip()
                    due_display = due_date_str
                    for fmt in ["%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d"]:
                        try:
                            d = datetime.strptime(due_date_str.strip(), fmt)
                            due_display = d.strftime("%b %-d") if sys.platform != "win32" else d.strftime("%b %#d")
                            break
                        except ValueError:
                            pass
                    t["due"] = due_display

                selected_risk = updated.get("risk") or updated.get("severity")
                if selected_risk:
                    t["risk"] = selected_risk
                    rs = RISK_STYLE_MAP.get(selected_risk, RISK_STYLE_MAP["Medium"])
                    t["risk_color"] = rs["risk_color"]
                    t["risk_bg"] = rs["risk_bg"]

                if "progress" in updated:
                    t["progress"] = int(updated.get("progress", t.get("progress", 0)) or 0)
                    auto_status = status_from_progress(t["progress"])
                    if auto_status in STATUS_STYLE_MAP:
                        t["status"] = auto_status
                        si = STATUS_STYLE_MAP[auto_status]
                        t["status_style"] = si["status_style"]
                        t["status_width"] = si["status_width"]

                # Persist editable fields (used by alert detail build_alert_from_task)
                if "description" in updated:
                    t["description"] = updated.get("description", t.get("description", ""))
                if "role" in updated:
                    t["role"] = updated.get("role", t.get("role", ""))
                    tag_txt = str(t.get("tag") or t.get("role") or "").strip()
                    if tag_txt:
                        t["tag"] = tag_txt
                        t["tag_color"] = TAG_COLOR_MAP.get(tag_txt, TAG_COLOR_MAP["Other"])

                save_tasks()

        # 2) Persist edit into alerts DB too (read/dismissed etc).
        existing = next((a for a in self._alerts if a.get("id") == alert_id), {})
        updated.setdefault("read", existing.get("read", False))
        self._alerts = db_update_alert(alert_id, updated, self._alerts)

        # 3) Rebuild from DB so UI uses the latest data.
        # This ensures the edited severity/description doesn't revert.
        self.reload_alerts()
        self.task_updated.emit()

    def _on_task_deleted_from_window(self, task_id: int):
        if task_id is None:
            return
        idx = next((i for i, t in enumerate(mock_tasks) if t.get("id") == task_id), None)
        if idx is None:
            return
        mock_tasks.pop(idx)
        save_tasks()
        self.reload_alerts()
        self.task_updated.emit()

    def _on_dismiss(self, alert_id):
        # เปลี่ยนสถานะ read
        for a in self._alerts:
            if a["id"] == alert_id:
                a["read"] = True
                a["dismissed"] = True
                break

        # เซฟลง database
        db_save(self._alerts)

        # ลบ card จาก UI
        if alert_id in self._cards:
            card = self._cards.pop(alert_id)
            self._cards_layout.removeWidget(card)
            card.deleteLater()

        # อัปเดต filter
        self._apply_filter()
        self._update_unread_count()

    def _on_dismiss_all(self):
        for a in self._alerts:
            a["read"] = True
            a["dismissed"] = True

        # เซฟ
        db_save(self._alerts)

        # ลบ UI ทั้งหมด
        for aid in list(self._cards.keys()):
            card = self._cards.pop(aid)
            self._cards_layout.removeWidget(card)
            card.deleteLater()

        self._apply_filter()
        self._update_unread_count()

    def _set_filter(self, key):
        self.current_filter = key; self._apply_filter(); self._update_filter_styles()

    def _apply_filter(self):
        for alert_id, card in self._cards.items():
            alert_data = next((a for a in self._alerts if a["id"] == alert_id), None)
            if alert_data is None: card.hide(); continue
            if alert_data.get("dismissed", False):
                card.hide()
                continue
            is_read = alert_data.get("read", False)
            show = (self.current_filter == "All" or
                    (self.current_filter == "Read"   and     is_read) or
                    (self.current_filter == "Unread" and not is_read))
            card.show() if show else card.hide()

        active_alerts = [a for a in self._alerts if not a.get("dismissed", False)]
        total   = len(active_alerts)
        unread  = sum(1 for a in active_alerts if not a.get("read", False))
        counts  = {"All": total, "Unread": unread, "Read": total - unread}
        for key, btn in self._filter_buttons.items():
            btn.setText(f"{key} ({counts[key]})")
        self._update_unread_count()

    def _update_unread_count(self): pass

    def _update_filter_styles(self):
        for key, btn in self._filter_buttons.items():
            if key == self.current_filter:
                btn.setStyleSheet("QPushButton{background:white;color:#4f46e5;border:1.5px solid #4f46e5;border-radius:17px;padding:0 20px;font-size:13px;font-weight:600;}")
            else:
                btn.setStyleSheet("QPushButton{background:white;color:#64748b;border:1px solid #cbd5e1;border-radius:17px;padding:0 20px;font-size:13px;font-weight:500;} QPushButton:hover{background:#F3F4F6;}")

    def reload_alerts(self):
        """
        Reload alerts from DB and rebuild UI.
        Called by MainWindow after user creates a new task.
        """
        self._alerts = db_load()
        self._rebuild_all_cards()
        # Keep current_filter selection, just re-apply visibility/counts.
        self._apply_filter()
        self._update_filter_styles()

    # ── เรียกจาก MainWindow เมื่อสร้าง task ใหม่ ──────────────────
    def add_alert_from_new_task(self, task_dict: dict):
        """เพิ่ม alert ทันทีสำหรับ High/Critical task ที่สร้างใหม่"""
        # Notify only when due date is within 3 days (including due-today).
        due_date = task_dict.get("due_date", "-")
        due = parse_due_date(due_date)
        if not due:
            return
        days_left = (due - datetime.now().date()).days
        if not (0 <= days_left <= 3):
            return

        severity = task_dict.get("risk", "Low")

        today_str = date.today().strftime("%b %d, %Y")
        max_id    = max((a.get("id", 0) for a in self._alerts), default=0)
        progress  = task_dict.get("progress", 0)
        icon_map = {
            "Low": "⚠️",
            "Medium": "⚠️",
            "High": "⚠️",
            "Critical": "⚠️"
        }

        icon = icon_map.get(severity, "🔔")

        due = parse_due_date(due_date)
        today = date.today()
        if due:
            days_left = (due - today).days
            if days_left < 0:
                reason = f"Overdue by {abs(days_left)} day(s), only {progress}% complete."
            elif days_left <= 3:
                reason = f"Due in {days_left} day(s) with {progress}% complete."
            else:
                reason = f"New task created. Due on {due_date}. Progress: {progress}%. Risk: {severity}."
        else:
            reason = f"New task created. Due on {due_date}. Progress: {progress}%. Risk: {severity}."

        if due and days_left is not None:
            meta_prefix = "Due today" if days_left == 0 else f"Due in {days_left} day(s)"
        else:
            meta_prefix = "Invalid due date"
        new_alert = {
            "id":          max_id + 1,
            "icon":        icon,
            "title":       f"{task_dict.get('name','')} — {severity} Risk",
            "description": reason,
            "meta":        f"{meta_prefix} · {today_str}",
            "severity":    severity,
            "project":     task_dict.get("project",""),
            "status":      task_dict.get("status","To do"),
            "progress":    progress,
            "due_date":    due_date,
            "role":        task_dict.get("role",""),
            "read":        False,
            "task_id":     task_dict.get("id", 0),
            "source":      "manual",
        }
        self._alerts.append(new_alert)
        db_save(self._alerts)
        self._add_card(new_alert, prepend=True)
        self._apply_filter()


# =====================================================================
# Edit Profile
# =====================================================================
class CustomDialog(QDialog):
    def __init__(self, parent=None, title="", message="", icon="✅"):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(360)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)

        card = QFrame()
        card.setStyleSheet("QFrame { background: white; border-radius: 20px; border: 1px solid #e2e8f0; }")
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(50)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(0, 0, 0, 60))
        card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(32, 20, 32, 28)
        layout.setSpacing(0)

        top_row = QHBoxLayout()
        top_row.addStretch()
        btn_x = QPushButton("✕")
        btn_x.setFixedSize(28, 28)
        btn_x.setCursor(Qt.PointingHandCursor)
        btn_x.setStyleSheet("QPushButton { background: #f1f5f9; color: #94a3b8; border: none; font-size: 12px; border-radius: 14px; } QPushButton:hover { background: #e2e8f0; color: #475569; }")
        btn_x.clicked.connect(self.reject)
        top_row.addWidget(btn_x)
        layout.addLayout(top_row)
        layout.addSpacing(4)

        icon_lbl = QLabel(icon)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 36px; background: transparent; border: none;")
        layout.addWidget(icon_lbl)
        layout.addSpacing(12)

        lbl_title = QLabel(title)
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setWordWrap(True)
        lbl_title.setStyleSheet("color: #1e293b; font-size: 17px; font-weight: bold; background: transparent; border: none;")
        layout.addWidget(lbl_title)
        layout.addSpacing(8)

        lbl_msg = QLabel(message)
        lbl_msg.setAlignment(Qt.AlignCenter)
        lbl_msg.setWordWrap(True)
        lbl_msg.setStyleSheet("color: #94a3b8; font-size: 13px; background: transparent; border: none;")
        layout.addWidget(lbl_msg)
        layout.addSpacing(22)

        btn_ok = QPushButton("OK")
        btn_ok.setFixedHeight(44)
        btn_ok.setFixedWidth(140)
        btn_ok.setCursor(Qt.PointingHandCursor)
        btn_ok.setStyleSheet("QPushButton { background: #4f46e5; color: white; border: none; border-radius: 10px; font-size: 14px; font-weight: bold; letter-spacing: 1px; } QPushButton:hover { background: #4338ca; } QPushButton:pressed { background: #3730a3; }")
        btn_ok.clicked.connect(self.accept)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(btn_ok)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        outer.addWidget(card)

    def exec(self):
        overlay = None
        if self.parent():
            main_win = self.parent().window()
            overlay = QWidget(main_win)
            overlay.setStyleSheet("background-color: rgba(0, 0, 0, 120);")
            overlay.resize(main_win.size())
            overlay.show()

        result = super().exec()
        if overlay:
            overlay.deleteLater()
        return result


class EditProfilePage(QWidget):
    profile_saved = Signal(dict)

    def __init__(self):
        super().__init__()
        self.default_data = {
            "first":  "Sompong",
            "last":   "Meechai",
            "nick":   "S",
            "email":  "Sompong.m@university.ac.th",
            "role":   "Risk & Task Manager",
            "status": "Active",
            "avatar_path": "",
        }
        self.saved_data = self._load_json()
        self._eye_open_icon = self._svg_icon(EYE_OPEN_SVG)
        self._eye_closed_icon = self._svg_icon(EYE_CLOSED_SVG)

        self._persist_timer = QTimer(self)
        self._persist_timer.setSingleShot(True)
        self._persist_timer.timeout.connect(self._persist_profile_auto)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")

        main_layout = QVBoxLayout(scroll_content)
        main_layout.setContentsMargins(40, 30, 40, 30)
        main_layout.setSpacing(25)

        header_container = QWidget()
        v_head = QVBoxLayout(header_container)
        v_head.setContentsMargins(0, 0, 0, 0)
        v_head.setSpacing(15)

        h_head = QHBoxLayout()
        title = QLabel("Edit Profile")
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #334155;")
        btn_analyze = QPushButton("🔍 Analyze Risk")
        btn_analyze.setCursor(Qt.PointingHandCursor)
        btn_analyze.setStyleSheet("background:#4f46e5;color:white;border:none;border-radius:8px;padding:8px 16px;font-weight:bold;font-size:13px;")
        btn_new_task = QPushButton("+ New Task")
        btn_new_task.setCursor(Qt.PointingHandCursor)
        btn_new_task.setStyleSheet("background:white;color:#4f46e5;border:1.5px solid #4f46e5;border-radius:8px;padding:8px 20px;font-weight:bold;font-size:13px;")
        h_head.addWidget(title)
        h_head.addStretch()
        h_head.addWidget(btn_analyze)
        h_head.addWidget(btn_new_task)
        v_head.addLayout(h_head)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background-color: #cbd5e1; border: none;")
        v_head.addWidget(divider)
        main_layout.addWidget(header_container)

        profile_card = QFrame()
        profile_card.setStyleSheet("background: white; border: 1px solid #cbd5e1; border-radius: 16px;")
        profile_card.setFixedHeight(140)
        card_layout = QHBoxLayout(profile_card)
        card_layout.setContentsMargins(30, 20, 30, 20)
        card_layout.setSpacing(25)

        avatar_container = QWidget()
        avatar_container.setFixedSize(80, 80)
        avatar_container.setStyleSheet("border: none;")
        avatar_container.setCursor(Qt.PointingHandCursor)

        self.card_avatar = QLabel(self.saved_data["nick"][:1].upper() if self.saved_data["nick"] else "?", avatar_container)
        self.card_avatar.setFixedSize(80, 80)
        self.card_avatar.setAlignment(Qt.AlignCenter)
        self.card_avatar.setStyleSheet("background-color: #4f46e5; color: white; border-radius: 40px; font-size: 36px; border: none;")

        self.card_avatar_overlay = QLabel("", avatar_container)
        self.card_avatar_overlay.setFixedSize(80, 80)
        self.card_avatar_overlay.setAlignment(Qt.AlignCenter)
        self.card_avatar_overlay.setStyleSheet("background-color: rgba(0,0,0,0); border-radius: 40px; font-size: 24px; border: none;")

        def _avatar_enter(e):
            self.card_avatar_overlay.setText("📷")
            self.card_avatar_overlay.setStyleSheet("background-color: rgba(0,0,0,150); color: white; border-radius: 40px; font-size: 24px; border: none;")

        def _avatar_leave(e):
            self.card_avatar_overlay.setText("")
            self.card_avatar_overlay.setStyleSheet("background-color: rgba(0,0,0,0); border-radius: 40px; font-size: 24px; border: none;")

        def _avatar_clicked(e):
            if e.button() == Qt.LeftButton:
                self._pick_avatar_image()

        avatar_container.enterEvent = _avatar_enter
        avatar_container.leaveEvent = _avatar_leave
        avatar_container.mousePressEvent = _avatar_clicked

        self.card_dot = QFrame(avatar_container)
        self.card_dot.setFixedSize(20, 20)
        self.card_dot.setStyleSheet("QFrame { background-color: #22c55e; border: 3px solid white; border-radius: 10px; }")
        self.card_dot.move(60, 60)
        self.card_dot.raise_()
        card_layout.addWidget(avatar_container)

        info_vbox = QVBoxLayout()
        info_vbox.setSpacing(6)
        info_vbox.setAlignment(Qt.AlignVCenter)

        d = self.saved_data
        hybrid_name = f"{d['first']} {d['last']} ({d['nick']})" if d["nick"] else f"{d['first']} {d['last']}"
        self.card_name = QLabel(hybrid_name.strip())
        self.card_name.setStyleSheet("font-size: 22px; font-weight: bold; color: #1e293b; border: none;")
        self.card_role = QLabel(d["role"])
        self.card_role.setStyleSheet("font-size: 13px; color: #64748b; border: none;")

        badges_hbox = QHBoxLayout()
        badges_hbox.setSpacing(10)
        self.badge_status = QLabel(d["status"])
        self.badge_status.setAlignment(Qt.AlignCenter)
        self.badge_status.setFixedHeight(24)
        _badge_style = "QLabel { background: #dcfce7; color: #16a34a; padding: 0 14px; border-radius: 12px; font-size: 11px; font-weight: bold; border: none; }" if d["status"] == "Active" else "QLabel { background: #f1f5f9; color: #94a3b8; padding: 0 14px; border-radius: 12px; font-size: 11px; font-weight: bold; border: none; }"
        self.badge_status.setStyleSheet(_badge_style)
        badges_hbox.addWidget(self.badge_status)
        badges_hbox.addStretch()

        info_vbox.addWidget(self.card_name)
        info_vbox.addWidget(self.card_role)
        info_vbox.addLayout(badges_hbox)
        card_layout.addLayout(info_vbox)
        card_layout.addStretch()
        main_layout.addWidget(profile_card)
        self._apply_card_avatar_from_data(self.saved_data)

        form_box = QFrame()
        form_box.setStyleSheet("background: white; border: 1px solid #cbd5e1; border-radius: 12px;")
        form_layout = QVBoxLayout(form_box)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(0)

        form_title_lbl = QLabel("USER SETTINGS")
        form_title_lbl.setStyleSheet("color: #64748b; font-size: 13px; font-weight: bold; padding: 15px 30px; border: none;")
        form_layout.addWidget(form_title_lbl)

        div_container = QWidget()
        div_lay = QHBoxLayout(div_container)
        div_lay.setContentsMargins(30, 0, 30, 0)
        f_divider = QFrame()
        f_divider.setFixedHeight(1)
        f_divider.setStyleSheet("background-color: #cbd5e1; border: none;")
        div_lay.addWidget(f_divider)
        form_layout.addWidget(div_container)

        grid_widget = QWidget()
        grid_widget.setStyleSheet("border: none;")
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(30, 25, 30, 20)
        grid.setHorizontalSpacing(30)
        grid.setVerticalSpacing(20)

        def create_input_field(label_text, value):
            wrapper = QWidget()
            wrapper.setStyleSheet("border: none;")
            vbox = QVBoxLayout(wrapper)
            vbox.setContentsMargins(0, 0, 0, 0)
            vbox.setSpacing(6)
            lbl = QLabel(label_text)
            lbl.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold; border: none;")
            inp = QLineEdit(value)
            inp.setFixedHeight(40)
            inp.setStyleSheet("QLineEdit { border: 1px solid #cbd5e1; border-radius: 8px; padding: 0 15px; color: #1e293b; font-size: 13px; background: white; } QLineEdit:focus { border: 1px solid #4f46e5; }")
            vbox.addWidget(lbl)
            vbox.addWidget(inp)
            return wrapper, inp

        w1, self.inp_first = create_input_field("FIRST NAME", d["first"])
        w2, self.inp_last  = create_input_field("LAST NAME", d["last"])
        w3, self.inp_nick  = create_input_field("NICKNAME (DISPLAY NAME)", d["nick"])
        w4, self.inp_email = create_input_field("EMAIL", d["email"])
        w5, self.inp_role  = create_input_field("ROLE", d["role"])

        grid.addWidget(w1, 0, 0)
        grid.addWidget(w2, 0, 1)
        grid.addWidget(w3, 1, 0, 1, 2)
        grid.addWidget(w4, 2, 0, 1, 2)
        grid.addWidget(w5, 3, 0)

        status_wrapper = QWidget()
        status_wrapper.setStyleSheet("border: none;")
        st_v = QVBoxLayout(status_wrapper)
        st_v.setContentsMargins(0, 0, 0, 0)
        st_v.setSpacing(6)
        st_l = QLabel("STATUS")
        st_l.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold; border: none;")
        self.inp_status = QComboBox()
        self.inp_status.addItems(["Active", "Inactive"])
        self.inp_status.setCurrentText(d["status"])
        self.inp_status.setFixedHeight(40)
        self.inp_status.setStyleSheet("QComboBox { border: 1px solid #cbd5e1; border-radius: 8px; padding: 0 15px; color: #1e293b; font-size: 13px; background: white; }")
        st_v.addWidget(st_l)
        st_v.addWidget(self.inp_status)
        grid.addWidget(status_wrapper, 3, 1)
        form_layout.addWidget(grid_widget)

        btn_bar_container = QWidget()
        btn_bar_layout = QHBoxLayout(btn_bar_container)
        btn_bar_layout.setContentsMargins(30, 14, 30, 18)
        btn_bar_layout.addStretch()

        self.btn_reset = QPushButton("Reset")
        self.btn_reset.setFixedSize(100, 38)
        self.btn_reset.setCursor(Qt.PointingHandCursor)
        self.btn_reset.setStyleSheet("QPushButton { background: #f1f5f9; color: #475569; border: none; border-radius: 8px; font-size: 13px; font-weight: bold; } QPushButton:hover { background: #e2e8f0; }")

        self.btn_save = QPushButton("Save")
        self.btn_save.setFixedSize(100, 38)
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.setStyleSheet("QPushButton { background: #4f46e5; color: white; border: none; border-radius: 8px; font-size: 13px; font-weight: bold; } QPushButton:hover { background: #4338ca; }")

        btn_bar_layout.addWidget(self.btn_reset)
        btn_bar_layout.addSpacing(10)
        btn_bar_layout.addWidget(self.btn_save)
        form_layout.addWidget(btn_bar_container)

        main_layout.addWidget(form_box)

        # ── 5. Security Settings Form ─────────────────────────────────
        sec_box = QFrame()
        sec_box.setStyleSheet("background: white; border: 1px solid #cbd5e1; border-radius: 12px;")
        sec_layout = QVBoxLayout(sec_box)
        sec_layout.setContentsMargins(0, 0, 0, 0)
        sec_layout.setSpacing(0)

        sec_title_lbl = QLabel("SECURITY SETTINGS")
        sec_title_lbl.setStyleSheet("color: #64748b; font-size: 13px; font-weight: bold; padding: 15px 30px; border: none;")
        sec_layout.addWidget(sec_title_lbl)

        s_div_container = QWidget()
        s_div_lay = QHBoxLayout(s_div_container)
        s_div_lay.setContentsMargins(30, 0, 30, 0)
        s_divider = QFrame()
        s_divider.setFixedHeight(1)
        s_divider.setStyleSheet("background-color: #cbd5e1; border: none;")
        s_div_lay.addWidget(s_divider)
        sec_layout.addWidget(s_div_container)

        s_grid_widget = QWidget()
        s_grid_widget.setStyleSheet("border: none;")
        s_grid = QGridLayout(s_grid_widget)
        s_grid.setContentsMargins(30, 25, 30, 20)
        s_grid.setHorizontalSpacing(30)
        s_grid.setVerticalSpacing(20)

        def create_password_field(label_text):
            wrapper = QWidget()
            wrapper.setStyleSheet("border: none;")
            vbox = QVBoxLayout(wrapper)
            vbox.setContentsMargins(0, 0, 0, 0)
            vbox.setSpacing(6)

            lbl = QLabel(label_text)
            lbl.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold; border: none;")

            input_row = QWidget()
            h_layout = QHBoxLayout(input_row)
            h_layout.setContentsMargins(0, 0, 0, 0)
            h_layout.setSpacing(8)

            inp = QLineEdit()
            inp.setEchoMode(QLineEdit.Password)
            inp.setFixedHeight(40)
            inp.setStyleSheet("QLineEdit { border: 1px solid #cbd5e1; border-radius: 8px; padding: 0 15px; color: #1e293b; font-size: 13px; background: white; } QLineEdit:focus { border: 1px solid #4f46e5; }")

            btn_eye = QPushButton()
            btn_eye.setFixedSize(28, 28)
            btn_eye.setCursor(Qt.PointingHandCursor)
            btn_eye.setToolTip("Show Password")
            btn_eye.setCheckable(True)
            btn_eye.setStyleSheet("""
                QPushButton { border:none; background:transparent; border-radius:6px; padding:3px; }
                QPushButton:hover   { background:#f1f5f9; }
                QPushButton:checked { background:#ede9fe; }
            """)

            def _svg_icon(svg_bytes: bytes) -> QIcon:
                renderer = QSvgRenderer(QByteArray(svg_bytes))
                pm = QPixmap(22, 22)
                pm.fill(Qt.transparent)
                p = QPainter(pm)
                renderer.render(p)
                p.end()
                return QIcon(pm)

            icon_open = _svg_icon(EYE_OPEN_SVG)
            icon_closed = _svg_icon(EYE_CLOSED_SVG)
            btn_eye.setIcon(icon_open)
            btn_eye.setIconSize(QSize(18, 18))

            def toggle_password_visibility():
                checked = btn_eye.isChecked()
                inp.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)
                btn_eye.setIcon(icon_closed if checked else icon_open)
                btn_eye.setToolTip("Hide Password" if checked else "Show Password")

            btn_eye.clicked.connect(toggle_password_visibility)

            h_layout.addWidget(inp)
            h_layout.addWidget(btn_eye)

            vbox.addWidget(lbl)
            vbox.addWidget(input_row)

            return wrapper, inp

        self.pw1_wrapper, self.inp_old_pw = create_password_field("CURRENT PASSWORD")
        self.pw2_wrapper, self.inp_new_pw = create_password_field("NEW PASSWORD")
        self.pw3_wrapper, self.inp_confirm_pw = create_password_field("CONFIRM NEW PASSWORD")

        s_grid.addWidget(self.pw1_wrapper, 0, 0, 1, 2)
        s_grid.addWidget(self.pw2_wrapper, 1, 0)
        s_grid.addWidget(self.pw3_wrapper, 1, 1)

        self.pw2_wrapper.hide()
        self.pw3_wrapper.hide()

        sec_layout.addWidget(s_grid_widget)

        s_btn_bar_container = QWidget()
        s_btn_bar_layout = QHBoxLayout(s_btn_bar_container)
        s_btn_bar_layout.setContentsMargins(30, 14, 30, 18)

        self.lbl_pw_error = QLabel("")
        self.lbl_pw_error.setStyleSheet("color: #ef4444; font-size: 12px; font-weight: bold; border: none;")

        self.btn_update_pw = QPushButton("Update Password")
        self.btn_update_pw.setFixedSize(140, 38)
        self.btn_update_pw.setCursor(Qt.ForbiddenCursor)
        self.btn_update_pw.setEnabled(False)
        self.btn_update_pw.setStyleSheet("QPushButton { background: #94a3b8; color: white; border: none; border-radius: 8px; font-size: 13px; font-weight: bold; }")

        self.btn_update_pw.show()

        s_btn_bar_layout.addWidget(self.lbl_pw_error)
        s_btn_bar_layout.addStretch()
        s_btn_bar_layout.addWidget(self.btn_update_pw)
        sec_layout.addWidget(s_btn_bar_container)
        main_layout.addWidget(sec_box)

        main_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        outer_layout.addWidget(scroll_area)

        self.btn_save.clicked.connect(self.save_data)
        self.btn_reset.clicked.connect(self.reset_data)
        self.inp_first.textChanged.connect(self.validate_form)
        self.inp_last.textChanged.connect(self.validate_form)
        self.inp_nick.textChanged.connect(self.validate_form)
        self.inp_email.textChanged.connect(self.validate_form)
        self.inp_role.textChanged.connect(self.validate_form)
        self.inp_status.currentIndexChanged.connect(self.validate_form)
        self.validate_form()

        self.btn_update_pw.clicked.connect(self.update_password)
        self.inp_old_pw.textChanged.connect(self.check_current_password)
        self.inp_new_pw.textChanged.connect(self.validate_new_password)
        self.inp_confirm_pw.textChanged.connect(self.validate_new_password)
        self._hide_new_password_fields()

    # ══ Helpers & Logic ══════════════════════════════════════════
    def _load_json(self):
        # 1) Prefer per-user persisted profile (scoped by email).
        key = _current_user_key()
        if key != "__default__":
            data = _load_scoped_object(PROFILE_DB_FILE, key=key)
            if data:
                for k, v in self.default_data.items():
                    data.setdefault(k, v)
                return data

        # 2) Fallback to legacy single-file profile.json (used to bootstrap current user key).
        if os.path.exists(PROFILE_JSON):
            try:
                with open(PROFILE_JSON, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for k, v in self.default_data.items():
                    data.setdefault(k, v)
                return data
            except (json.JSONDecodeError, IOError):
                pass

        return dict(self.default_data)

    def _svg_icon(self, svg_bytes: bytes) -> QIcon:
        pix = QPixmap()
        pix.loadFromData(svg_bytes, "SVG")
        return QIcon(pix)

    def _get_form_data(self):
        return {
            "first":  self.inp_first.text().strip(),
            "last":   self.inp_last.text().strip(),
            "nick":   self.inp_nick.text().strip(),
            "email":  self.inp_email.text().strip(),
            "role":   self.inp_role.text().strip(),
            "status": self.inp_status.currentText(),
            "avatar_path": self.saved_data.get("avatar_path", ""),
        }

    def _form_fields_valid(self) -> bool:
        if not self.inp_first.text().strip():
            return False
        if not self.inp_last.text().strip():
            return False
        email_text = self.inp_email.text().strip()
        return bool(re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email_text))

    def _schedule_auto_persist(self) -> None:
        self._persist_timer.start(400)

    def _persist_profile_auto(self) -> None:
        if not self._form_fields_valid():
            return
        data = self._get_form_data()
        try:
            # Persist per-user profile.
            key = _current_user_key()
            if key != "__default__":
                _save_scoped_object(PROFILE_DB_FILE, key=key, obj=data)

            # Keep current-session profile.json in sync (used for key + UI bootstrapping).
            with open(PROFILE_JSON, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except OSError:
            return
        self.saved_data = dict(data)
        self._update_profile_card(data)
        self.profile_saved.emit(data)

    def _persist_avatar_merge(self) -> None:
        """Keep other profile keys if form invalid; always persist new avatar path."""
        base = self._load_json()
        base["avatar_path"] = str(self.saved_data.get("avatar_path", "") or "")
        try:
            key = _current_user_key()
            if key != "__default__":
                _save_scoped_object(PROFILE_DB_FILE, key=key, obj=base)
            with open(PROFILE_JSON, "w", encoding="utf-8") as f:
                json.dump(base, f, ensure_ascii=False, indent=4)
        except OSError:
            return
        self.saved_data = base
        card = dict(base)
        card.update(self._get_form_data())
        self._update_profile_card(card)
        self.profile_saved.emit(card)

    def _apply_data(self, data):
        self.inp_first.setText(data["first"])
        self.inp_last.setText(data["last"])
        self.inp_nick.setText(data["nick"])
        self.inp_email.setText(data["email"])
        self.inp_role.setText(data["role"])
        self.inp_status.setCurrentText(data["status"])

    def _update_profile_card(self, data):
        hybrid_name = f"{data['first']} {data['last']} ({data['nick']})" if data["nick"] else f"{data['first']} {data['last']}"
        self.card_name.setText(hybrid_name.strip())
        self.card_role.setText(data["role"])
        self._apply_card_avatar_from_data(data)

        self.badge_status.setText(data["status"])
        if data["status"] == "Active":
            self.badge_status.setStyleSheet("QLabel { background: #dcfce7; color: #16a34a; padding: 0 14px; border-radius: 12px; font-size: 11px; font-weight: bold; border: none; }")
            self.card_dot.setStyleSheet("QFrame { background-color: #22c55e; border: 3px solid white; border-radius: 10px; }")
        else:
            self.badge_status.setStyleSheet("QLabel { background: #f1f5f9; color: #94a3b8; padding: 0 14px; border-radius: 12px; font-size: 11px; font-weight: bold; border: none; }")
            self.card_dot.setStyleSheet("QFrame { background-color: #94a3b8; border: 3px solid white; border-radius: 10px; }")
        self.badge_status.adjustSize()
        self.card_dot.raise_()

    def _pick_avatar_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "เลือกรูปโปรไฟล์", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp)")
        if not path:
            return
        rounded = self._build_rounded_avatar(path, 80)
        if rounded is None:
            return
        self.saved_data["avatar_path"] = path
        self.card_avatar.setPixmap(rounded)
        self.card_avatar.setText("")
        self._persist_timer.stop()
        if self._form_fields_valid():
            self._persist_profile_auto()
        else:
            self._persist_avatar_merge()

    def _build_rounded_avatar(self, path: str, size: int) -> QPixmap | None:
        pixmap = QPixmap(path)
        if pixmap.isNull():
            return None
        rounded = QPixmap(size, size)
        rounded.fill(Qt.transparent)
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(pixmap.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, size, size)
        painter.end()
        return rounded

    def _apply_card_avatar_from_data(self, data: dict):
        path = str(data.get("avatar_path", "") or "").strip()
        if path and os.path.exists(path):
            rounded = self._build_rounded_avatar(path, 80)
            if rounded is not None:
                self.card_avatar.setPixmap(rounded)
                self.card_avatar.setText("")
                return
        self.card_avatar.setPixmap(QPixmap())
        self.card_avatar.setText(data["nick"][:1].upper() if data.get("nick") else "?")

    def _set_input_error(self, widget, has_error):
        if has_error:
            widget.setStyleSheet("QLineEdit { border: 1px solid #ef4444; border-radius: 8px; padding: 0 15px; color: #1e293b; font-size: 13px; background: #fef2f2; } QLineEdit:focus { border: 1px solid #dc2626; }")
        else:
            widget.setStyleSheet("QLineEdit { border: 1px solid #cbd5e1; border-radius: 8px; padding: 0 15px; color: #1e293b; font-size: 13px; background: white; } QLineEdit:focus { border: 1px solid #4f46e5; }")

    def validate_form(self):
        is_valid = True
        if not self.inp_first.text().strip():
            self._set_input_error(self.inp_first, True); is_valid = False
        else:
            self._set_input_error(self.inp_first, False)

        if not self.inp_last.text().strip():
            self._set_input_error(self.inp_last, True); is_valid = False
        else:
            self._set_input_error(self.inp_last, False)

        email_text = self.inp_email.text().strip()
        email_pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(email_pattern, email_text):
            self._set_input_error(self.inp_email, True); is_valid = False
        else:
            self._set_input_error(self.inp_email, False)

        self.btn_save.setEnabled(is_valid)
        if is_valid:
            self.btn_save.setStyleSheet("QPushButton { background: #4f46e5; color: white; border: none; border-radius: 8px; font-size: 13px; font-weight: bold; } QPushButton:hover { background: #4338ca; }")
            self.btn_save.setCursor(Qt.PointingHandCursor)
            self._schedule_auto_persist()
        else:
            self.btn_save.setStyleSheet("QPushButton { background: #94a3b8; color: white; border: none; border-radius: 8px; font-size: 13px; font-weight: bold; }")
            self.btn_save.setCursor(Qt.ForbiddenCursor)

    def check_current_password(self):
        from database import User
        old_pw = self.inp_old_pw.text()
        current_email = self.inp_email.text().strip().lower()
        user = User.find_by_email(current_email) if current_email else None

        if not old_pw:
            self._set_input_error(self.inp_old_pw, False)
            self.lbl_pw_error.setText("")
            self._hide_new_password_fields()
            return

        if user and user.check_password(old_pw):
            self._set_input_error(self.inp_old_pw, False)
            self.lbl_pw_error.setText("Current password correct! Enter new password.")
            self.lbl_pw_error.setStyleSheet("color: #16a34a; font-size: 12px; font-weight: bold; border: none;")
            self._show_new_password_fields()
        else:
            self._set_input_error(self.inp_old_pw, True)
            self.lbl_pw_error.setText("Incorrect current password.")
            self.lbl_pw_error.setStyleSheet("color: #ef4444; font-size: 12px; font-weight: bold; border: none;")
            self._hide_new_password_fields()

    def _hide_new_password_fields(self):
        self.pw2_wrapper.hide()
        self.pw3_wrapper.hide()
        self.btn_update_pw.hide()
        self.inp_new_pw.clear()
        self.inp_confirm_pw.clear()
        self.btn_update_pw.setEnabled(False)
        self.btn_update_pw.setStyleSheet("QPushButton { background: #94a3b8; color: white; border: none; border-radius: 8px; font-size: 13px; font-weight: bold; }")
        self.btn_update_pw.setCursor(Qt.ForbiddenCursor)

    def _show_new_password_fields(self):
        self.pw2_wrapper.show()
        self.pw3_wrapper.show()
        self.btn_update_pw.show()
        self.validate_new_password()

    def validate_new_password(self):
        new_pw = self.inp_new_pw.text()
        confirm_pw = self.inp_confirm_pw.text()
        is_valid = False

        self.lbl_pw_error.setStyleSheet("color: #ef4444; font-size: 12px; font-weight: bold; border: none;")

        if new_pw or confirm_pw:
            if len(new_pw) < 6:
                self.lbl_pw_error.setText("New password must be at least 6 characters.")
                self._set_input_error(self.inp_new_pw, True)
                self._set_input_error(self.inp_confirm_pw, False)
            elif new_pw != confirm_pw:
                self.lbl_pw_error.setText("New passwords do not match.")
                self._set_input_error(self.inp_new_pw, False)
                self._set_input_error(self.inp_confirm_pw, True)
            else:
                self.lbl_pw_error.setText("Passwords match. Ready to update.")
                self.lbl_pw_error.setStyleSheet("color: #16a34a; font-size: 12px; font-weight: bold; border: none;")
                self._set_input_error(self.inp_new_pw, False)
                self._set_input_error(self.inp_confirm_pw, False)
                is_valid = True
        else:
            self.lbl_pw_error.setText("Current password correct! Enter new password.")
            self.lbl_pw_error.setStyleSheet("color: #16a34a; font-size: 12px; font-weight: bold; border: none;")
            self._set_input_error(self.inp_new_pw, False)
            self._set_input_error(self.inp_confirm_pw, False)

        self.btn_update_pw.setEnabled(is_valid)
        if is_valid:
            self.btn_update_pw.setStyleSheet("QPushButton { background: #0f172a; color: white; border: none; border-radius: 8px; font-size: 13px; font-weight: bold; } QPushButton:hover { background: #334155; }")
            self.btn_update_pw.setCursor(Qt.PointingHandCursor)
        else:
            self.btn_update_pw.setStyleSheet("QPushButton { background: #94a3b8; color: white; border: none; border-radius: 8px; font-size: 13px; font-weight: bold; }")
            self.btn_update_pw.setCursor(Qt.ForbiddenCursor)

    def save_data(self):
        self.validate_form()
        if not self._form_fields_valid():
            return
        self._persist_timer.stop()
        data = self._get_form_data()
        try:
            with open(PROFILE_JSON, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            self.saved_data = dict(data)
            dlg = CustomDialog(self, title="Saved Successfully!", message="The profile has been updated in the system.", icon="✅")
            if dlg.exec() == QDialog.Accepted:
                self._update_profile_card(data)
                self.profile_saved.emit(data)
        except IOError as e:
            dlg = CustomDialog(self, title="Save Failed", message=str(e), icon="❌")
            dlg.exec()

    def reset_data(self):
        self._persist_timer.stop()
        self._apply_data(self.saved_data)
        self.validate_form()

    def update_password(self):
        from database import User

        current_email = self.inp_email.text().strip().lower()
        new_pw = self.inp_new_pw.text()
        if not current_email or len(new_pw) < 6:
            return

        ok = User.update_password(current_email, new_pw)
        if ok:
            dlg = CustomDialog(self, title="Success!", message="Password updated securely!", icon="🔒")
            dlg.exec()
            self.inp_old_pw.clear()
            self.lbl_pw_error.setText("")
            self._hide_new_password_fields()
            if self._form_fields_valid():
                self._persist_timer.stop()
                self._persist_profile_auto()
        else:
            dlg = CustomDialog(self, title="Update Failed", message="Could not update password. Please try again.", icon="❌")
            dlg.exec()


# =====================================================================
# MainWindow
# =====================================================================
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        # Ensure tasks/alerts are loaded for the currently logged-in user.
        load_all_data()
        self.resize(1280, 820)
        self.setWindowTitle("RiskTrack")
        self.setObjectName("riskTrackMainRoot")
        self.setStyleSheet(
            "* { font-family: 'Segoe UI', Arial, sans-serif; } "
            "#riskTrackMainRoot { background-color: #f8fafc; }"
        )

        root = QHBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)

        side = QVBoxLayout(); side.setContentsMargins(15,20,15,20); side.setSpacing(8)
        logo_row = QHBoxLayout(); logo_row.setSpacing(8)
        logo_ic  = QLabel("R"); logo_ic.setFixedSize(34,34); logo_ic.setAlignment(Qt.AlignCenter)
        logo_ic.setStyleSheet("background:#4f46e5;border-radius:9px;color:white;font-size:16px;font-weight:900;")
        logo_txt = QLabel("RiskTrack"); logo_txt.setStyleSheet("font-size:17px;font-weight:800;color:#1e293b;")
        logo_row.addWidget(logo_ic); logo_row.addWidget(logo_txt); logo_row.addStretch()
        side.addLayout(logo_row); side.addSpacing(16)

        self.profile_box = QFrame(); self.profile_box.setStyleSheet("background-color:#f1f5f9;border-radius:16px;")
        self.profile_box.setCursor(Qt.PointingHandCursor)
        pl = QVBoxLayout(self.profile_box); pl.setContentsMargins(10,20,10,20); pl.setSpacing(5)
        self.side_avatar = QLabel("S"); self.side_avatar.setFixedSize(52,52); self.side_avatar.setAlignment(Qt.AlignCenter)
        self.side_avatar.setStyleSheet("background-color:#4f46e5;color:white;border-radius:26px;font-size:20px;font-weight:700;")
        self.side_name = QLabel("Sompong Meechai"); self.side_name.setStyleSheet("font-size:13px;font-weight:bold;color:#1e293b;background:transparent;"); self.side_name.setAlignment(Qt.AlignCenter)
        self.role_l = QLabel("Edit profile"); self.role_l.setStyleSheet("color:#94a3b8;font-size:12px;background:transparent;"); self.role_l.setAlignment(Qt.AlignCenter)
        self.role_l.setCursor(Qt.PointingHandCursor)
        pl.addWidget(self.side_avatar,0,Qt.AlignCenter); pl.addWidget(self.side_name,0,Qt.AlignCenter); pl.addWidget(self.role_l,0,Qt.AlignCenter)
        side.addWidget(self.profile_box); side.addSpacing(16)

        def make_nav(text, active=False):
            btn = QPushButton(f"  {text}"); btn.setFixedHeight(42); btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(("background:#4f46e5;color:white;" if active else "background:transparent;color:#64748b;") + "border-radius:10px;text-align:left;padding-left:16px;font-weight:bold;font-size:14px;")
            return btn

        self.btn_dashboard  = make_nav("Dashboard", True)
        self.btn_task_table = make_nav("Task Table")
        self.btn_alert      = make_nav("Alert")
        self.btn_logout     = make_nav("Logout")
        self.nav_buttons    = [self.btn_dashboard, self.btn_task_table, self.btn_alert]
        side.addWidget(self.btn_dashboard); side.addWidget(self.btn_task_table); side.addWidget(self.btn_alert)
        side.addStretch(); side.addWidget(self.btn_logout)

        side_widget = QWidget(); side_widget.setLayout(side); side_widget.setFixedWidth(240)
        side_widget.setStyleSheet("background:#ffffff;border-right:1px solid #e2e8f0;")
        root.addWidget(side_widget)

        self.stack          = QStackedWidget()
        self.page_dashboard  = DashboardPage()
        self.page_task_table = TaskTablePage()
        self.page_alert      = AlertPage(username="Sompong Meechai")
        self.page_edit_profile = EditProfilePage()
        self.stack.addWidget(self.page_dashboard)
        self.stack.addWidget(self.page_task_table)
        self.stack.addWidget(self.page_alert)
        self.stack.addWidget(self.page_edit_profile)

        self.page_dashboard.btn_new_task.clicked.connect(self.open_new_task_dialog)
        self.page_task_table.btn_new_task.clicked.connect(self.open_new_task_dialog)
        self.page_dashboard.task_double_clicked.connect(self._open_task_detail_from_row)
        self.page_task_table.task_double_clicked.connect(self._open_task_detail_from_row)
        self.page_alert.task_updated.connect(self._refresh_task_pages)
        self._open_task_windows: dict[int, TaskDetailWindow] = {}
        # + New Task in Alert top bar
        if getattr(self.page_alert, "btn_new_task", None) is not None:
            self.page_alert.btn_new_task.clicked.connect(self.open_new_task_dialog)
        self.page_edit_profile.profile_saved.connect(self._on_profile_saved)

        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background:#f8fafc;border:none;"); scroll.setWidget(self.stack)
        root.addWidget(scroll, 1)

        self.btn_dashboard.clicked.connect(lambda: self.switch_page(0, self.btn_dashboard))
        self.btn_task_table.clicked.connect(lambda: self.switch_page(1, self.btn_task_table))
        self.btn_alert.clicked.connect(lambda: self.switch_page(2, self.btn_alert))
        self.profile_box.mousePressEvent = self._open_edit_profile_from_sidebar
        self.side_avatar.mousePressEvent = self._open_edit_profile_from_sidebar
        self.side_name.mousePressEvent = self._open_edit_profile_from_sidebar
        self.role_l.mousePressEvent = self._open_edit_profile_from_sidebar
        # Logout behavior is handled by the parent AppWindow (Main.py).
        self._on_profile_saved(self.page_edit_profile.saved_data)

    def switch_page(self, idx, active_btn):
        self.stack.setCurrentIndex(idx)
        for btn in self.nav_buttons:
            if btn == active_btn:
                btn.setStyleSheet("background:#4f46e5;color:white;border-radius:10px;text-align:left;padding-left:16px;font-weight:bold;font-size:14px;")
            else:
                btn.setStyleSheet("background:transparent;color:#64748b;border-radius:10px;text-align:left;padding-left:16px;font-weight:bold;font-size:14px;")

    def open_new_task_dialog(self):
        next_id = (max(t.get("id",0) for t in mock_tasks) + 1) if mock_tasks else 1
        dlg = NewTaskDialog(next_task_id=next_id, parent=self)
        dlg.task_created.connect(self._on_task_created)
        dlg.exec()

    def _on_task_created(self, task_dict: dict):
        mock_tasks.append(task_dict)
        save_tasks()

        self._refresh_task_pages()

        self.page_alert.reload_alerts()   # ⭐ ให้ alert อัพเดททันที

    def _refresh_task_pages(self):
        self.page_dashboard.refresh_tasks()
        self.page_task_table.refresh_tasks()

    def _open_task_detail_from_row(self, task: dict):
        task_id = task.get("id")
        if task_id is None:
            return

        if task_id in self._open_task_windows:
            win = self._open_task_windows[task_id]
            if win.isVisible():
                win.raise_()
                win.activateWindow()
                return
            del self._open_task_windows[task_id]

        detail_data = {
            "id": task_id,
            "task_id": task_id,
            "title": task.get("name", ""),
            "description": task.get("description", ""),
            "role": task.get("tag", ""),
            "project": task.get("tag", ""),
            "status": task.get("status", "To do"),
            "progress": task.get("progress", 0),
            "severity": task.get("risk", "Medium"),
            "risk": task.get("risk", "Medium"),
            "due_date": task.get("due_date", task.get("due", "")),
        }
        win = TaskDetailWindow(detail_data, username="Sompong Meechai")
        win.alert_task_saved.connect(self._on_task_saved_from_task_window)
        win.alert_task_deleted.connect(self._on_task_deleted_from_task_window)
        win.destroyed.connect(lambda _, tid=task_id: self._open_task_windows.pop(tid, None))
        self._open_task_windows[task_id] = win
        win.show()

    def _on_task_saved_from_task_window(self, updated: dict):
        task_id = updated.get("task_id") or updated.get("id")
        if task_id is None:
            return

        task = next((t for t in mock_tasks if t.get("id") == task_id), None)
        if task is None:
            return

        if "title" in updated:
            task["name"] = updated.get("title", task.get("name", ""))
        if "description" in updated:
            task["description"] = updated.get("description", task.get("description", ""))
        if "role" in updated:
            task["tag"] = updated.get("role", task.get("tag", ""))
            task["project"] = updated.get("role", task.get("project", ""))
            task["tag_color"] = TAG_COLOR_MAP.get(task["tag"], TAG_COLOR_MAP["Other"])
        if "due_date" in updated:
            task["due_date"] = updated.get("due_date", task.get("due_date", ""))
            due_date_str = str(task.get("due_date", "") or "").strip()
            due_display = due_date_str
            for fmt in ["%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d"]:
                try:
                    d = datetime.strptime(due_date_str, fmt)
                    due_display = d.strftime("%b %-d") if sys.platform != "win32" else d.strftime("%b %#d")
                    break
                except ValueError:
                    pass
            task["due"] = due_display

        if "progress" in updated:
            task["progress"] = int(updated.get("progress", task.get("progress", 0)) or 0)
            auto_status = status_from_progress(task["progress"])
            if auto_status in STATUS_STYLE_MAP:
                task["status"] = auto_status
                si = STATUS_STYLE_MAP[auto_status]
                task["status_style"] = si["status_style"]
                task["status_width"] = si["status_width"]

        selected_risk = updated.get("risk") or updated.get("severity")
        if selected_risk:
            task["risk"] = selected_risk
            rs = RISK_STYLE_MAP.get(selected_risk, RISK_STYLE_MAP["Medium"])
            task["risk_color"] = rs["risk_color"]
            task["risk_bg"] = rs["risk_bg"]

        task["bar"] = progress_bar_color(int(task.get("progress", 0) or 0))
        save_tasks()
        self._refresh_task_pages()
        self.page_alert.reload_alerts()

    def _on_task_deleted_from_task_window(self, task_id: int):
        if task_id is None:
            return
        idx = next((i for i, t in enumerate(mock_tasks) if t.get("id") == task_id), None)
        if idx is None:
            return
        mock_tasks.pop(idx)
        save_tasks()
        self._refresh_task_pages()
        self.page_alert.reload_alerts()

    def _on_profile_saved(self, data: dict):
        display_name = data.get("nick", "").strip() if data.get("nick") else f"{data.get('first', '')} {data.get('last', '')}".strip()
        nick_char = data.get("nick", "")[:1].upper() if data.get("nick") else "?"
        self.side_name.setText(display_name or "Unknown")
        avatar_path = str(data.get("avatar_path", "") or "").strip()
        if avatar_path and os.path.exists(avatar_path):
            rounded = self.page_edit_profile._build_rounded_avatar(avatar_path, 52)
            if rounded is not None:
                self.side_avatar.setPixmap(rounded)
                self.side_avatar.setText("")
                self.side_avatar.setStyleSheet("background: transparent; border-radius:26px;")
                return
        self.side_avatar.setPixmap(QPixmap())
        self.side_avatar.setText(nick_char)
        self.side_avatar.setStyleSheet("background-color:#4f46e5;color:white;border-radius:26px;font-size:20px;font-weight:700;")

    def _open_edit_profile_from_sidebar(self, event):
        if event.button() == Qt.LeftButton:
            self.switch_page(3, None)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = MainWindow()
    w.show()
    sys.exit(app.exec())