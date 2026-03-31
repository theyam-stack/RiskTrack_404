"""
config.py — RiskTrack Application Configuration
⚠️  กรุณาแก้ไข SMTP settings ก่อนใช้งาน Forgot Password

วิธีสร้าง Gmail App Password:
  1. เข้า myaccount.google.com → Security
  2. เปิด 2-Step Verification (ถ้ายังไม่ได้เปิด)
  3. ค้นหา "App passwords" → สร้าง App password
  4. นำรหัส 16 หลักมาใส่ใน SMTP_PASS
"""

# ── SMTP Email Settings ─────────────────────────────────────────────
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587          # 587 = STARTTLS  |  465 = SSL
SMTP_USER = "thitiya.m@kkumail.com"
SMTP_PASS = "elfz fgoy usms xbnw"

# ── App Settings ────────────────────────────────────────────────────
APP_NAME          = "RiskTrack"
RESET_CODE_EXPIRE = 10   # นาที ก่อน OTP หมดอายุ
DB_FILENAME       = "risktrack.json"  
SESSION_FILENAME  = "session.json"