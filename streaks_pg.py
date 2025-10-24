import os
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except Exception:  # allow import without psycopg installed at dev time
    psycopg2 = None
    RealDictCursor = None


class StreakServicePG:
    """
    PostgreSQL-backed service for streaks: daily activity, soft penalties, and summary state.
    Schema (public schema by default):
      - streak_days(user_id, date, activity_count, source, created_at)
      - streak_state(user_id, current_streak, longest_streak, last_active_date, missed_days, last_reset_date, updated_at)
      - streak_goals(user_id, goal_days, effective_from, updated_at)
      - streak_events(id, user_id, event_date, event_type, meta, created_at)
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
            raise RuntimeError("PostgreSQL not configured. Set PG_DSN or PG* env variables and install psycopg2.")
        return psycopg2.connect(self.dsn)

    def init_schema(self):
        ddl = """
        CREATE TABLE IF NOT EXISTS streak_days (
          id SERIAL PRIMARY KEY,
          user_id INTEGER NOT NULL,
          date DATE NOT NULL,
          activity_count INTEGER NOT NULL DEFAULT 1,
          source TEXT,
          created_at TIMESTAMP NOT NULL DEFAULT NOW(),
          UNIQUE(user_id, date)
        );

        CREATE TABLE IF NOT EXISTS streak_state (
          user_id INTEGER PRIMARY KEY,
          current_streak INTEGER NOT NULL DEFAULT 0,
          longest_streak INTEGER NOT NULL DEFAULT 0,
          last_active_date DATE,
          missed_days INTEGER NOT NULL DEFAULT 0,
          last_reset_date DATE,
          updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS streak_goals (
          user_id INTEGER PRIMARY KEY,
          goal_days INTEGER NOT NULL DEFAULT 7,
          effective_from DATE NOT NULL DEFAULT CURRENT_DATE,
          updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS streak_events (
          id SERIAL PRIMARY KEY,
          user_id INTEGER NOT NULL,
          event_date DATE NOT NULL,
          event_type TEXT NOT NULL,
          meta JSONB,
          created_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
        """
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(ddl)
            conn.commit()

    # --- Core Reads ---
    def get_streak_state(self, user_id: int) -> Dict[str, Any]:
        sql = """
        SELECT current_streak, longest_streak, last_active_date, missed_days, last_reset_date
        FROM streak_state WHERE user_id = %s
        """
        with self._conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (user_id,))
                row = cur.fetchone() or {}
        return {
            'current_streak': row.get('current_streak', 0) if row else 0,
            'longest_streak': row.get('longest_streak', 0) if row else 0,
            'last_active_date': (row.get('last_active_date').isoformat() if row and row.get('last_active_date') else None),
            'missed_days': row.get('missed_days', 0) if row else 0,
            'last_reset_date': (row.get('last_reset_date').isoformat() if row and row.get('last_reset_date') else None),
        }

    def get_month_streak_days(self, user_id: int, month_start: date, month_end: date) -> List[str]:
        sql = """
        SELECT date FROM streak_days WHERE user_id = %s AND date BETWEEN %s AND %s ORDER BY date ASC
        """
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (user_id, month_start, month_end))
                rows = cur.fetchall()
        return [r[0].isoformat() for r in rows]

    def get_streak_goal(self, user_id: int) -> Dict[str, Any]:
        sql = "SELECT goal_days, effective_from FROM streak_goals WHERE user_id = %s"
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (user_id,))
                row = cur.fetchone()
        if not row:
            return { 'goal_days': 7, 'effective_from': date.today().isoformat() }
        goal_days, eff = row
        return { 'goal_days': int(goal_days), 'effective_from': eff.isoformat() if eff else None }

    # --- Core Writes ---
    def ensure_state_row(self, conn, user_id: int):
        with conn.cursor() as cur:
            cur.execute("INSERT INTO streak_state(user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING", (user_id,))

    def mark_daily_activity(self, user_id: int, activity_date: Optional[date] = None, source: Optional[str] = None, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Apply soft-penalty logic and upsert streak state. Returns updated state."""
        d = activity_date or date.today()
        with self._conn() as conn:
            self.ensure_state_row(conn, user_id)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Insert day if not present
                cur.execute(
                    "INSERT INTO streak_days(user_id, date, activity_count, source) VALUES(%s,%s,1,%s) ON CONFLICT(user_id,date) DO UPDATE SET activity_count = streak_days.activity_count + 1"
                    , (user_id, d, source)
                )
                # Log event
                cur.execute(
                    "INSERT INTO streak_events(user_id, event_date, event_type, meta) VALUES (%s,%s,%s,%s)",
                    (user_id, d, source or 'activity', (meta or None))
                )
                # Fetch current state
                cur.execute("SELECT current_streak, longest_streak, last_active_date, missed_days FROM streak_state WHERE user_id = %s", (user_id,))
                row = cur.fetchone()
                current = row['current_streak'] or 0
                longest = row['longest_streak'] or 0
                last_active = row['last_active_date']
                missed = row['missed_days'] or 0

                # Compute gap
                gap = 0
                if last_active:
                    gap = (d - last_active).days

                if last_active is None:
                    current = 1
                elif gap == 0:
                    # same day: don't change current (already counted); ensure >=1
                    current = max(1, current)
                elif gap == 1:
                    current = current + 1
                elif 1 < gap < 8:
                    # soft penalty: subtract one then count today
                    current = max(0, current - 1) + 1
                    missed += (gap - 1)
                else:  # gap >= 8
                    current = 1
                    missed += (gap - 1)
                    cur.execute("UPDATE streak_state SET last_reset_date = %s WHERE user_id = %s", (d, user_id))

                longest = max(longest, current)
                # Update state
                cur.execute(
                    "UPDATE streak_state SET current_streak=%s, longest_streak=%s, last_active_date=%s, missed_days=%s, updated_at=NOW() WHERE user_id=%s",
                    (current, longest, d, missed, user_id)
                )
            conn.commit()
        return self.get_streak_state(user_id)

    def set_streak_goal(self, user_id: int, goal_days: int, effective_from: Optional[date] = None):
        eff = effective_from or (date.today() + timedelta(days=1))
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO streak_goals(user_id, goal_days, effective_from) VALUES(%s,%s,%s) ON CONFLICT (user_id) DO UPDATE SET goal_days=EXCLUDED.goal_days, effective_from=EXCLUDED.effective_from, updated_at=NOW()",
                    (user_id, goal_days, eff)
                )
            conn.commit()

    # Utilities for month boundaries
    @staticmethod
    def month_bounds(y: int, m: int) -> (date, date):
        start = date(y, m, 1)
        if m == 12:
            end = date(y + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(y, m + 1, 1) - timedelta(days=1)
        return start, end
