"""
database.py — RiskTrack Data Layer  (JSON backend)
════════════════════════════════════════════════════
รวม: database + user model (risktrack.json)

"""

import os
import json
import uuid
import hashlib
import threading
from datetime import datetime
from typing import Optional, List, Any

# ── Config (graceful fallback) ──────────────────────────────────────
try:
    from config import DB_FILENAME
except ImportError:
    DB_FILENAME = "risktrack.json"

# ── ถ้า DB_FILENAME ยังเป็น .db ให้เปลี่ยนนามสกุลเป็น .json ─────────
if DB_FILENAME.endswith(".db"):
    DB_FILENAME = DB_FILENAME[:-3] + ".json"

_HERE    = os.path.dirname(os.path.abspath(__file__))
_DB_PATH = os.path.join(_HERE, DB_FILENAME)

STATUS_OPTIONS = ("To do", "In Progress", "Review", "Done")
RISK_OPTIONS   = ("Low", "Medium", "High", "Critical")


# ══════════════════════════════════════════════════════════════════════
#  DatabaseManager  — JSON file backend
# ══════════════════════════════════════════════════════════════════════

class DatabaseManager:
    """
    Singleton ที่จัดการ JSON file แทน SQLite
    ข้อมูลทั้งหมดเก็บใน dict ใน memory และ flush ลง .json ทุกครั้งที่แก้ไข

    Schema:
        {
          "users":        { "<id>": {...} },
          "projects":     { "<id>": {...} },
          "tasks":        { "<id>": {...} },
          "alerts":       { "<id>": {...} },
          "reset_tokens": [ {...}, ... ]
        }
    """

    _instance: Optional["DatabaseManager"] = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "DatabaseManager":
        if cls._instance is None:
            cls._instance = cls(_DB_PATH)
        return cls._instance

    def __init__(self, db_path: str = _DB_PATH) -> None:
        self.db_path = db_path
        self._lock   = threading.Lock()
        self._data: dict = self._load()

    # ── I/O ───────────────────────────────────────────────────────
    def _load(self) -> dict:
        """โหลด JSON file; ถ้าไม่มีให้สร้าง schema เปล่า"""
        empty = {
            "users":        {},
            "projects":     {},
            "tasks":        {},
            "alerts":       {},
            "reset_tokens": [],
        }
        if not os.path.exists(self.db_path):
            return empty
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # ตรวจว่ามีทุก key
            for k in empty:
                data.setdefault(k, empty[k])
            return data
        except (json.JSONDecodeError, OSError):
            return empty

    def _save(self) -> None:
        """เขียน JSON ลง disk (เรียกหลัง mutation ทุกครั้ง)"""
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    # ── Generic table helpers ─────────────────────────────────────
    def insert(self, table: str, record: dict) -> None:
        with self._lock:
            self._data[table][record["id"]] = record
            self._save()

    def update(self, table: str, record_id: str, fields: dict) -> bool:
        with self._lock:
            if record_id not in self._data[table]:
                return False
            self._data[table][record_id].update(fields)
            self._save()
            return True

    def delete(self, table: str, record_id: str) -> bool:
        with self._lock:
            if record_id not in self._data[table]:
                return False
            del self._data[table][record_id]
            self._save()
            return True

    def get(self, table: str, record_id: str) -> Optional[dict]:
        return self._data[table].get(record_id)

    def all_records(self, table: str) -> List[dict]:
        return list(self._data[table].values())

    def find(self, table: str, **kwargs) -> List[dict]:
        """คืน records ที่ตรงกับทุก key=value ที่ระบุ"""
        results = []
        for rec in self._data[table].values():
            if all(rec.get(k) == v for k, v in kwargs.items()):
                results.append(rec)
        return results

    # ── Reset Token helpers ───────────────────────────────────────
    def save_reset_token(self, email: str, token: str, expires_at: str) -> None:
        with self._lock:
            # ลบ token เก่าของ email นี้ก่อน
            self._data["reset_tokens"] = [
                t for t in self._data["reset_tokens"]
                if t.get("email") != email.strip().lower()
            ]
            self._data["reset_tokens"].append({
                "email":      email.strip().lower(),
                "token":      token,
                "expires_at": expires_at,
                "used":       False,
            })
            self._save()

    def get_reset_token(self, email: str) -> Optional[dict]:
        key = email.strip().lower()
        valid = [
            t for t in self._data["reset_tokens"]
            if t.get("email") == key and not t.get("used", False)
        ]
        if not valid:
            return None
        return sorted(valid, key=lambda t: t["expires_at"], reverse=True)[0]

    def mark_token_used(self, email: str) -> None:
        with self._lock:
            key = email.strip().lower()
            for t in self._data["reset_tokens"]:
                if t.get("email") == key:
                    t["used"] = True
            self._save()

    # ── Utility ───────────────────────────────────────────────────
    def get_db_path(self) -> str:
        return self.db_path


# User Model

class User:
    """
    Attributes: id, name, email, password_hash, role, created_at
    """

    def __init__(self, id: str, name: str, email: str,
                 password_hash: str, role: str = "member",
                 created_at: str = "") -> None:
        self.id            = id
        self.name          = name
        self.email         = email.lower()
        self.password_hash = password_hash
        self.role          = role
        self.created_at    = created_at or datetime.now().isoformat()

    @staticmethod
    def _hash(password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    @staticmethod
    def _db() -> DatabaseManager:
        return DatabaseManager.get_instance()

    @classmethod
    def create(cls, name: str, email: str, password: str,
               role: str = "member") -> Optional["User"]:
        key = email.strip().lower()
        if cls.find_by_email(key):
            return None
        user = cls(
            id=str(uuid.uuid4()), name=name.strip(), email=key,
            password_hash=cls._hash(password), role=role,
            created_at=datetime.now().isoformat(),
        )
        try:
            cls._db().insert("users", user._to_raw())
            return user
        except Exception:
            return None

    @classmethod
    def find_by_email(cls, email: str) -> Optional["User"]:
        results = cls._db().find("users", email=email.strip().lower())
        return cls._from_raw(results[0]) if results else None

    @classmethod
    def find_by_id(cls, user_id: str) -> Optional["User"]:
        raw = cls._db().get("users", user_id)
        return cls._from_raw(raw) if raw else None

    @classmethod
    def all(cls) -> List["User"]:
        rows = cls._db().all_records("users")
        return sorted(
            [cls._from_raw(r) for r in rows],
            key=lambda u: u.created_at, reverse=True
        )

    @classmethod
    def update_password(cls, email: str, new_password: str) -> bool:
        key = email.strip().lower()
        results = cls._db().find("users", email=key)
        if not results:
            return False
        return cls._db().update("users", results[0]["id"],
                                {"password_hash": cls._hash(new_password)})

    def check_password(self, password: str) -> bool:
        return self.password_hash == self._hash(password)

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "email": self.email,
                "role": self.role, "created_at": self.created_at}

    def _to_raw(self) -> dict:
        return {"id": self.id, "name": self.name, "email": self.email,
                "password_hash": self.password_hash, "role": self.role,
                "created_at": self.created_at}

    def __repr__(self) -> str:
        return f"<User id={self.id[:8]}… name={self.name!r}>"

    @classmethod
    def _from_raw(cls, r: dict) -> "User":
        return cls(id=r["id"], name=r["name"], email=r["email"],
                   password_hash=r["password_hash"], role=r.get("role", "member"),
                   created_at=r["created_at"])
