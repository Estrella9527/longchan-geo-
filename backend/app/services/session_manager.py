"""
Browser Session Manager — manages persistent browser sessions for Playwright providers.

Each session corresponds to a pre-authenticated browser profile (user_data_dir)
that can be used by DoubaoProvider or DeepSeekProvider.

Uses raw psycopg2 for sync DB access (called from both Celery workers and API layer).
"""
import os
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4
from typing import Optional

import psycopg2
from app.core.config import settings

logger = logging.getLogger(__name__)


@contextmanager
def _sync_db():
    """Raw psycopg2 connection for session manager operations."""
    # Convert asyncpg URL to psycopg2
    db_url = settings.DATABASE_URL.replace("+asyncpg", "").replace("postgresql://", "postgresql://")
    conn = psycopg2.connect(db_url)
    try:
        yield conn
    finally:
        conn.close()


class SessionManager:
    """Manages browser sessions for Playwright-based LLM providers."""

    def __init__(self):
        self.base_dir = getattr(settings, "BROWSER_SESSION_DIR", "/app/browser_data")

    def _ensure_dir(self, path: str):
        os.makedirs(path, exist_ok=True)

    def get_user_data_dir(self, session_id: str) -> str:
        path = os.path.join(self.base_dir, session_id)
        self._ensure_dir(path)
        return path

    def create_session(self, provider_name: str, display_name: str = "", phone_number: str = "") -> dict:
        session_id = str(uuid4())
        user_data_dir = self.get_user_data_dir(session_id)
        now = datetime.now(timezone.utc)

        with _sync_db() as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO browser_sessions
                   (id, provider_name, user_data_dir, display_name, status, phone_number,
                    created_at, updated_at)
                   VALUES (%s, %s, %s, %s, 'created', %s, %s, %s)""",
                (session_id, provider_name, user_data_dir,
                 display_name or f"{provider_name}会话", phone_number, now, now),
            )
            conn.commit()

        return {
            "id": session_id,
            "provider_name": provider_name,
            "user_data_dir": user_data_dir,
            "display_name": display_name or f"{provider_name}会话",
            "status": "created",
            "phone_number": phone_number,
            "created_at": now.isoformat(),
        }

    def list_sessions(self, provider_name: Optional[str] = None) -> list[dict]:
        with _sync_db() as conn:
            cur = conn.cursor()
            if provider_name:
                cur.execute(
                    """SELECT id, provider_name, user_data_dir, display_name, status,
                              phone_number, last_used_at, last_health_check, health_check_message, created_at, updated_at
                       FROM browser_sessions WHERE provider_name = %s
                       ORDER BY created_at DESC""",
                    (provider_name,),
                )
            else:
                cur.execute(
                    """SELECT id, provider_name, user_data_dir, display_name, status,
                              phone_number, last_used_at, last_health_check, health_check_message, created_at, updated_at
                       FROM browser_sessions ORDER BY created_at DESC"""
                )
            cols = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            return [dict(zip(cols, row)) for row in rows]

    def get_session(self, session_id: str) -> Optional[dict]:
        with _sync_db() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT id, provider_name, user_data_dir, display_name, status,
                          phone_number, last_used_at, last_health_check, health_check_message, created_at, updated_at
                   FROM browser_sessions WHERE id = %s""",
                (session_id,),
            )
            cols = [desc[0] for desc in cur.description]
            row = cur.fetchone()
            return dict(zip(cols, row)) if row else None

    def acquire(self, provider_name: str) -> Optional[dict]:
        with _sync_db() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT id, provider_name, user_data_dir, display_name, status
                   FROM browser_sessions
                   WHERE provider_name = %s AND status = 'active'
                   ORDER BY last_used_at DESC NULLS LAST
                   LIMIT 1""",
                (provider_name,),
            )
            cols = [desc[0] for desc in cur.description]
            row = cur.fetchone()
            if not row:
                return None

            session = dict(zip(cols, row))
            now = datetime.now(timezone.utc)
            cur.execute(
                "UPDATE browser_sessions SET last_used_at = %s, updated_at = %s WHERE id = %s",
                (now, now, session["id"]),
            )
            conn.commit()
            return session

    def update_status(self, session_id: str, status: str):
        now = datetime.now(timezone.utc)
        with _sync_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE browser_sessions SET status = %s, updated_at = %s WHERE id = %s",
                (status, now, session_id),
            )
            conn.commit()

    def update_phone(self, session_id: str, phone_number: str):
        now = datetime.now(timezone.utc)
        with _sync_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE browser_sessions SET phone_number = %s, updated_at = %s WHERE id = %s",
                (phone_number, now, session_id),
            )
            conn.commit()

    def update_health_check(self, session_id: str, is_healthy: bool, message: str = ""):
        now = datetime.now(timezone.utc)
        new_status = "active" if is_healthy else "expired"
        if not message:
            message = "会话正常，登录状态有效" if is_healthy else "会话已过期，需要重新登录"
        with _sync_db() as conn:
            cur = conn.cursor()
            cur.execute(
                """UPDATE browser_sessions
                   SET last_health_check = %s, status = %s, health_check_message = %s, updated_at = %s
                   WHERE id = %s""",
                (now, new_status, message, now, session_id),
            )
            conn.commit()

    def delete_session(self, session_id: str) -> bool:
        with _sync_db() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM browser_sessions WHERE id = %s", (session_id,))
            conn.commit()
            return cur.rowcount > 0


# Singleton
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
