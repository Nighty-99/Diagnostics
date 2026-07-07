from __future__ import annotations

from datetime import datetime, timezone
from email.message import EmailMessage
import json
import os
from pathlib import Path
import smtplib
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("DIAGNOSTIC_DB_PATH", BASE_DIR / "diagnostic_results.sqlite3"))
HOST = os.getenv("DIAGNOSTIC_BACKEND_HOST", "127.0.0.1")
PORT = int(os.getenv("DIAGNOSTIC_BACKEND_PORT", "8788"))
ALLOWED_ORIGIN = os.getenv("DIAGNOSTIC_ALLOWED_ORIGIN", "*")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS diagnostic_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                personal_data_consent INTEGER NOT NULL,
                marketing_consent INTEGER NOT NULL,
                diagnostic_id TEXT NOT NULL,
                diagnostic_title TEXT NOT NULL,
                total_score REAL NOT NULL,
                total_max REAL NOT NULL,
                overall_percent REAL NOT NULL,
                overall_level TEXT NOT NULL,
                primary_score_range TEXT,
                secondary_score_range TEXT,
                payload_json TEXT NOT NULL
            )
            """
        )
        conn.commit()


def as_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def require_text(data: dict, key: str) -> str:
    value = str(data.get(key, "")).strip()
    if not value:
        raise ValueError(f"Missing required field: {key}")
    return value


def validate_payload(payload: dict) -> None:
    student = payload.get("student") or {}
    diagnostic = payload.get("diagnostic") or {}
    result = payload.get("result") or {}

    require_text(student, "name")
    require_text(student, "email")
    require_text(student, "phone")
    require_text(diagnostic, "id")
    require_text(diagnostic, "title")

    if not bool(student.get("personal_data_consent")):
        raise ValueError("Personal data consent is required")

    for key in ("total_score", "total_max", "overall_percent"):
        if key not in result:
            raise ValueError(f"Missing result field: {key}")


def save_result(payload: dict) -> int:
    student = payload["student"]
    diagnostic = payload["diagnostic"]
    result = payload["result"]
    forecast = result.get("score_forecast") or {}
    created_at = payload.get("submitted_at") or utc_now()

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            INSERT INTO diagnostic_results (
                created_at,
                name,
                email,
                phone,
                personal_data_consent,
                marketing_consent,
                diagnostic_id,
                diagnostic_title,
                total_score,
                total_max,
                overall_percent,
                overall_level,
                primary_score_range,
                secondary_score_range,
                payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                created_at,
                student.get("name", ""),
                student.get("email", ""),
                student.get("phone", ""),
                1 if student.get("personal_data_consent") else 0,
                1 if student.get("marketing_consent") else 0,
                diagnostic.get("id", ""),
                diagnostic.get("title", ""),
                as_float(result.get("total_score")),
                as_float(result.get("total_max")),
                as_float(result.get("overall_percent")),
                str(result.get("overall_level", "")),
                str(forecast.get("primary_score_range", "")),
                str(forecast.get("secondary_score_range", "")),
                json.dumps(payload, ensure_ascii=False),
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)


def result_email_text(payload: dict, result_id: int) -> str:
    student = payload["student"]
    diagnostic = payload["diagnostic"]
    result = payload["result"]
    forecast = result.get("score_forecast") or {}

    lines = [
        f"Здравствуйте, {student.get('name', '')}!",
        "",
        "Ваш результат диагностики:",
        f"Диагностика: {diagnostic.get('title', '')}",
        f"Балл: {result.get('total_score')} / {result.get('total_max')}",
        f"Процент: {result.get('overall_percent')}%",
        f"Уровень: {result.get('overall_level')}",
    ]

    if forecast:
        lines += [
            "",
            "Ориентир по ЕГЭ:",
            f"Первичный балл: {forecast.get('primary_score_range', '')}",
            f"Вторичный балл: {forecast.get('secondary_score_range', '')}",
            f"Комментарий: {forecast.get('comment', '')}",
            f"Ближайшая цель: {forecast.get('next_goal', '')}",
        ]

    findings = result.get("main_findings") or []
    if findings:
        lines += ["", "Главные выводы:"]
        lines += [f"- {item}" for item in findings]

    lines += [
        "",
        f"Номер записи в базе: {result_id}",
        "",
        "С уважением,",
        "онлайн-школа Infinita",
    ]
    return "\n".join(lines)


def send_email(payload: dict, result_id: int) -> bool:
    smtp_host = os.getenv("SMTP_HOST")
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM") or smtp_user
    admin_email = os.getenv("ADMIN_EMAIL")

    if not smtp_host or not smtp_from:
        return False

    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    use_tls = os.getenv("SMTP_USE_TLS", "1") != "0"
    student = payload["student"]

    recipients = [student["email"]]
    if admin_email:
        recipients.append(admin_email)

    message = EmailMessage()
    message["Subject"] = "Результат диагностики Infinita"
    message["From"] = smtp_from
    message["To"] = ", ".join(recipients)
    message.set_content(result_email_text(payload, result_id))

    with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as smtp:
        if use_tls:
            smtp.starttls()
        if smtp_user and smtp_password:
            smtp.login(smtp_user, smtp_password)
        smtp.send_message(message)

    return True


class DiagnosticHandler(BaseHTTPRequestHandler):
    server_version = "DiagnosticBackend/1.0"

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", ALLOWED_ORIGIN)
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS, GET")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def write_json(self, status: int, data: dict) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.write_json(200, {"ok": True})

    def do_GET(self) -> None:  # noqa: N802
        if urlparse(self.path).path == "/health":
            self.write_json(200, {"ok": True, "db_path": str(DB_PATH)})
            return
        self.write_json(404, {"ok": False, "error": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/api/diagnostic-results":
            self.write_json(404, {"ok": False, "error": "Not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(length)
            payload = json.loads(raw_body.decode("utf-8"))
            validate_payload(payload)
            result_id = save_result(payload)
            email_sent = send_email(payload, result_id)
            self.write_json(200, {"ok": True, "id": result_id, "email_sent": email_sent})
        except Exception as exc:  # intentionally returned as client-readable API error
            self.write_json(400, {"ok": False, "error": str(exc)})


def main() -> None:
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), DiagnosticHandler)
    print(f"Diagnostic backend started at http://{HOST}:{PORT}")
    print(f"SQLite database: {DB_PATH}")
    server.serve_forever()


if __name__ == "__main__":
    main()
