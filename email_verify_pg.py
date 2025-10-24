import os
import secrets
import hashlib
from datetime import datetime, timedelta, date
from typing import Optional, Tuple, Dict, Any

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except Exception:
    psycopg2 = None
    RealDictCursor = None


class EmailVerifyServicePG:
    """
    PostgreSQL-backed service for issuing and verifying email tokens/codes.
    Table: email_verifications
    Columns: id, user_id, email, token_hash, code_hash, sent_at, expires_at, consumed_at,
             resend_count, attempt_count
    """

    def __init__(self, dsn: Optional[str] = None):
        self.dsn = dsn or os.getenv("PG_DSN") or self._build_dsn_from_env()

    def _build_dsn_from_env(self) -> Optional[str]:
        host = os.getenv("PGHOST")
        db = os.getenv("PGDATABASE")
        user = os.getenv("PGUSER")
        pwd = os.getenv("PGPASSWORD")
        port = os.getenv("PGPORT", "5432")
        if host and db and user and pwd:
            return f"dbname={db} user={user} password={pwd} host={host} port={port}"
        return None

    def _conn(self):
        if not psycopg2 or not self.dsn:
            raise RuntimeError("PostgreSQL not configured for email verification.")
        return psycopg2.connect(self.dsn)

    def init_schema(self):
        ddl = """
        CREATE TABLE IF NOT EXISTS email_verifications (
          id SERIAL PRIMARY KEY,
          user_id INTEGER NOT NULL,
          email TEXT NOT NULL,
          token_hash TEXT NOT NULL,
          code_hash TEXT,
          sent_at TIMESTAMP NOT NULL DEFAULT NOW(),
          expires_at TIMESTAMP NOT NULL,
          consumed_at TIMESTAMP NULL,
          resend_count INTEGER NOT NULL DEFAULT 0,
          attempt_count INTEGER NOT NULL DEFAULT 0,
          inbound_recipient TEXT NULL,
          inbound_provider TEXT NULL,
          inbound_received_at TIMESTAMP NULL
        );
        CREATE INDEX IF NOT EXISTS idx_email_verif_user ON email_verifications(user_id);
        CREATE INDEX IF NOT EXISTS idx_email_verif_token ON email_verifications(token_hash);
        CREATE INDEX IF NOT EXISTS idx_email_verif_expires ON email_verifications(expires_at);
        """
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(ddl)
                # Backfill columns for existing tables if needed
                cur.execute("ALTER TABLE email_verifications ADD COLUMN IF NOT EXISTS inbound_recipient TEXT")
                cur.execute("ALTER TABLE email_verifications ADD COLUMN IF NOT EXISTS inbound_provider TEXT")
                cur.execute("ALTER TABLE email_verifications ADD COLUMN IF NOT EXISTS inbound_received_at TIMESTAMP NULL")
            conn.commit()

    @staticmethod
    def _sha256(s: str) -> str:
        return hashlib.sha256(s.encode('utf-8')).hexdigest()

    @staticmethod
    def make_token_and_code() -> Tuple[str, str]:
        token = secrets.token_urlsafe(32)
        code = f"{secrets.randbelow(1_000_000):06d}"
        return token, code

    def invalidate_previous(self, conn, user_id: int):
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE email_verifications SET consumed_at = NOW() WHERE user_id = %s AND consumed_at IS NULL",
                (user_id,)
            )

    def issue(self, user_id: int, email: str, ttl_minutes: int = 15) -> Tuple[str, str, datetime, Optional[str]]:
        token, code = self.make_token_and_code()
        token_hash = self._sha256(token)
        code_hash = self._sha256(code)
        expires_at = datetime.utcnow() + timedelta(minutes=ttl_minutes)
        provider = os.getenv('INBOUND_PROVIDER') or ''
        vdomain = os.getenv('VERIFY_DOMAIN') or ''
        inbound_recipient = None
        if vdomain:
            local = secrets.token_urlsafe(8).lower()
            inbound_recipient = f"{local}@{vdomain}"
        with self._conn() as conn:
            self.invalidate_previous(conn, user_id)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO email_verifications(user_id, email, token_hash, code_hash, expires_at, inbound_recipient, inbound_provider)
                    VALUES(%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (user_id, email, token_hash, code_hash, expires_at, inbound_recipient, provider)
                )
            conn.commit()
        return token, code, expires_at, inbound_recipient

    def can_resend(self, user_id: int) -> bool:
        # Enforce 2 minutes cooldown and max 5 per day
        sql = """
        SELECT COUNT(*) FILTER (WHERE sent_at > NOW() - INTERVAL '24 hours') AS sent_last_day,
               MAX(sent_at) AS last_sent
        FROM email_verifications WHERE user_id = %s AND consumed_at IS NULL
        """
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (user_id,))
                row = cur.fetchone()
        sent_last_day, last_sent = row if row else (0, None)
        if sent_last_day is not None and sent_last_day >= 5:
            return False
        if last_sent and (datetime.utcnow() - last_sent).total_seconds() < 120:
            return False
        return True

    def resend(self, user_id: int, email: str, ttl_minutes: int = 15) -> Tuple[str, str, datetime, Optional[str]]:
        if not self.can_resend(user_id):
            raise RuntimeError("Resend limit reached. Please wait before trying again.")
        token, code = self.make_token_and_code()
        token_hash = self._sha256(token)
        code_hash = self._sha256(code)
        expires_at = datetime.utcnow() + timedelta(minutes=ttl_minutes)
        provider = os.getenv('INBOUND_PROVIDER') or ''
        vdomain = os.getenv('VERIFY_DOMAIN') or ''
        inbound_recipient = None
        if vdomain:
            local = secrets.token_urlsafe(8).lower()
            inbound_recipient = f"{local}@{vdomain}"
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO email_verifications(user_id, email, token_hash, code_hash, expires_at, resend_count, inbound_recipient, inbound_provider)
                    VALUES (%s,%s,%s,%s,%s,
                        COALESCE((SELECT MAX(resend_count) FROM email_verifications WHERE user_id=%s),0)+1,
                        %s, %s)
                    """,
                    (user_id, email, token_hash, code_hash, expires_at, user_id, inbound_recipient, provider)
                )
            conn.commit()
        return token, code, expires_at, inbound_recipient

    def _consume(self, conn, ev_id: int):
        with conn.cursor() as cur:
            cur.execute("UPDATE email_verifications SET consumed_at = NOW() WHERE id = %s AND consumed_at IS NULL", (ev_id,))

    def verify_by_token(self, raw_token: str) -> Optional[Dict[str, Any]]:
        token_hash = self._sha256(raw_token)
        with self._conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM email_verifications WHERE token_hash = %s ORDER BY sent_at DESC LIMIT 1",
                    (token_hash,)
                )
                row = cur.fetchone()
                if not row:
                    return None
                if row['consumed_at'] is not None:
                    return None
                if row['expires_at'] and row['expires_at'] < datetime.utcnow():
                    return None
                self._consume(conn, row['id'])
            conn.commit()
            return row

    def verify_by_code(self, user_id: int, raw_code: str) -> bool:
        code_hash = self._sha256(raw_code)
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, expires_at, consumed_at FROM email_verifications
                    WHERE user_id = %s AND code_hash = %s
                    ORDER BY sent_at DESC LIMIT 1
                    """,
                    (user_id, code_hash)
                )
                row = cur.fetchone()
                if not row:
                    return False
                ev_id, expires_at, consumed_at = row
                if consumed_at is not None:
                    return False
                if expires_at and expires_at < datetime.utcnow():
                    return False
                self._consume(conn, ev_id)
            conn.commit()
            return True

    # Inbound matching by recipient/sender/content
    def verify_from_inbound(self, recipient: str, sender_email: str, content: str) -> Optional[int]:
        """Return user_id if verified; None otherwise."""
        if not recipient or not sender_email:
            return None
        code_candidates = []
        # Extract possible 6-digit codes from content
        import re
        code_candidates.extend(re.findall(r"\b(\d{6})\b", content or ""))
        with self._conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, user_id, email, code_hash, expires_at, consumed_at
                    FROM email_verifications
                    WHERE inbound_recipient = %s
                    ORDER BY sent_at DESC LIMIT 1
                    """,
                    (recipient,)
                )
                row = cur.fetchone()
                if not row:
                    return None
                if row['consumed_at'] is not None:
                    return None
                if row['expires_at'] and row['expires_at'] < datetime.utcnow():
                    return None
                # Sender must match registered email
                if (row['email'] or '').strip().lower() != sender_email.strip().lower():
                    return None
                # Match any 6-digit code in body/subject
                ok = False
                for c in code_candidates:
                    if self._sha256(c) == row['code_hash']:
                        ok = True
                        break
                if not ok:
                    return None
                # Consume and mark inbound received
                with conn.cursor() as c2:
                    c2.execute("UPDATE email_verifications SET consumed_at = NOW(), inbound_received_at = NOW() WHERE id = %s AND consumed_at IS NULL", (row['id'],))
                conn.commit()
                return row['user_id']

    def get_pending_for_user(self, user_id: int) -> Dict[str, Any]:
        with self._conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, email, inbound_recipient, expires_at, consumed_at
                    FROM email_verifications
                    WHERE user_id = %s
                    ORDER BY sent_at DESC LIMIT 1
                    """,
                    (user_id,)
                )
                return cur.fetchone() or {}

    def latest_status(self, user_id: int) -> Dict[str, Any]:
        with self._conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT id, sent_at, expires_at, consumed_at, resend_count FROM email_verifications WHERE user_id = %s ORDER BY sent_at DESC LIMIT 1",
                    (user_id,)
                )
                row = cur.fetchone()
                return row or {}
