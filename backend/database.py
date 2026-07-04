"""
Database abstraction layer for JenteraPintar N05 Matunggong.
Menyokong DUA mod:

1. SQLite (default – tempatan) – jika DATABASE_URL tidak diset
2. PostgreSQL – jika environment variable DATABASE_URL diset

Semua kod aplikasi TIDAK perlu diubah — antara muka cursor dikekalkan.
"""
import os
from config import settings
from typing import Optional

# Tentukan mod pangkalan data
USE_POSTGRES = bool(settings.DATABASE_URL and settings.DATABASE_URL.strip())


# =============================================================================
# MODUL BANTU: Padankan ? placeholder kepada %s untuk PostgreSQL
# =============================================================================
def _convert_placeholders(sql: str) -> str:
    """Tukar placeholder ? (SQLite) kepada %s (PostgreSQL)."""
    return sql.replace('?', '%s')


def _add_returning_id(sql: str) -> str:
    """Tambah RETURNING id pada INSERT jika belum ada."""
    trimmed = sql.strip().upper()
    if trimmed.startswith('INSERT') and 'RETURNING' not in trimmed:
        # Pastikan tiada ; di hujung
        sql = sql.rstrip().rstrip(';') + ' RETURNING id'
    return sql


# =============================================================================
# PEMBALUT CURSOR UNTUK PostgreSQL
# =============================================================================
class _PostgresCursor:
    """
    Pembalut cursor psycopg2 yang menyamai antara muka `sqlite3.Cursor`
    untuk membolehkan kod sedia ada berfungsi tanpa perubahan.

    Ciri-ciri yang disamakan:
      - execute(sql, params) – placeholder ? → %s
      - lastrowid – diambil dari RETURNING id
      - rowcount – terus dari psycopg2
      - fetchone(), fetchall() – DictRow (sokong akses nombor & string)
    """

    def __init__(self, pg_conn):
        import psycopg2.extras
        self._inner = pg_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        self._lastrowid_value: Optional[int] = None

    def execute(self, sql: str, params=None):
        pg_sql = _convert_placeholders(sql)

        # Jika INSERT, tambah RETURNING id untuk dapatkan lastrowid
        is_insert = pg_sql.strip().upper().startswith('INSERT')
        if is_insert:
            pg_sql = _add_returning_id(pg_sql)

        if params is not None:
            # Pastikan params adalah list/tuple
            if isinstance(params, (list, tuple)):
                self._inner.execute(pg_sql, params)
            else:
                self._inner.execute(pg_sql, [params])
        else:
            self._inner.execute(pg_sql)

        # Ambil lastrowid daripada RETURNING
        if is_insert:
            try:
                self._lastrowid_value = self._inner.fetchone()[0]
            except Exception:
                self._lastrowid_value = None

    def executemany(self, sql: str, seq_of_params):
        pg_sql = _convert_placeholders(sql)
        self._inner.executemany(pg_sql, seq_of_params)

    @property
    def lastrowid(self) -> Optional[int]:
        return self._lastrowid_value

    @property
    def rowcount(self) -> int:
        return self._inner.rowcount

    @property
    def description(self):
        return self._inner.description

    def fetchone(self):
        return self._inner.fetchone()

    def fetchall(self):
        return self._inner.fetchall()

    def fetchmany(self, size=None):
        if size is not None:
            return self._inner.fetchmany(size)
        return self._inner.fetchmany()

    def close(self):
        self._inner.close()

    def __iter__(self):
        return iter(self._inner)


# =============================================================================
# PEMBALUT SAMBUNGAN UNTUK PostgreSQL
# =============================================================================
class _PostgresConnection:
    """
    Pembalut sambungan psycopg2 yang menyamai antara muka `sqlite3.Connection`.
    Fungsi .cursor() memulangkan _PostgresCursor.
    """

    def __init__(self, dsn: str):
        import psycopg2
        self._inner = psycopg2.connect(dsn)
        self._inner.autocommit = False

    def cursor(self):
        return _PostgresCursor(self._inner)

    def commit(self):
        self._inner.commit()

    def rollback(self):
        self._inner.rollback()

    def close(self):
        self._inner.close()


# =============================================================================
# FUNGSI UTAMA get_db() – kembali sambungan SQLite ATAU PostgreSQL
# =============================================================================
def get_db():
    """
    Kembalikan sambungan pangkalan data.

    - Jika DATABASE_URL diset → PostgreSQL (psycopg2)
    - Jika tidak → SQLite tempatan (sqlite3)
    """
    if USE_POSTGRES:
        return _PostgresConnection(settings.DATABASE_URL)

    import sqlite3
    conn = sqlite3.connect(settings.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# =============================================================================
# FUNGSI init_db() – Bina jadual
# =============================================================================
def init_db():
    """
    Bina semua jadual yang diperlukan jika belum wujud.
    Berfungsi untuk SQLite dan PostgreSQL.
    """
    db = get_db()
    cursor = db.cursor()

    # Jadual users (RBAC)
    if USE_POSTGRES:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                nama_penuh TEXT,
                kata_laluan TEXT NOT NULL,
                peranan VARCHAR(100) NOT NULL DEFAULT 'Pemerhati',
                dm TEXT,
                aktif INTEGER DEFAULT 1,
                dicipta_pada TEXT
            )
        """)
    else:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                nama_penuh TEXT,
                kata_laluan TEXT NOT NULL,
                peranan TEXT NOT NULL DEFAULT 'Pemerhati',
                dm TEXT,
                aktif INTEGER DEFAULT 1,
                dicipta_pada TEXT
            )
        """)

    # Jadual pengundi
    if USE_POSTGRES:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pengundi (
                id SERIAL PRIMARY KEY,
                no_kp VARCHAR(20),
                nama_penuh TEXT,
                jantina VARCHAR(1),
                tahun_lahir INTEGER,
                dm TEXT,
                lokaliti TEXT,
                no_telefon TEXT,
                status_sokongan TEXT,
                status_fizikal TEXT,
                adalah_pemilik_apps INTEGER DEFAULT 0,
                status_rekod TEXT DEFAULT 'Sah',
                sumber_pdm TEXT,
                dicipta_pada TEXT
            )
        """)
    else:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pengundi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                no_kp TEXT,
                nama_penuh TEXT,
                jantina TEXT,
                tahun_lahir INTEGER,
                dm TEXT,
                lokaliti TEXT,
                no_telefon TEXT,
                status_sokongan TEXT,
                status_fizikal TEXT,
                adalah_pemilik_apps INTEGER DEFAULT 0,
                status_rekod TEXT DEFAULT 'Sah',
                sumber_pdm TEXT,
                dicipta_pada TEXT
            )
        """)

    # Jadual audit_logs
    if USE_POSTGRES:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                username VARCHAR(255) NOT NULL,
                peranan VARCHAR(100) NOT NULL,
                tindakan VARCHAR(255) NOT NULL,
                penerangan TEXT,
                no_kp_terlibat VARCHAR(20),
                endpoint TEXT,
                ip_address TEXT,
                user_agent TEXT,
                dicipta_pada TEXT NOT NULL
            )
        """)
    else:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT NOT NULL,
                peranan TEXT NOT NULL,
                tindakan TEXT NOT NULL,
                penerangan TEXT,
                no_kp_terlibat TEXT,
                endpoint TEXT,
                ip_address TEXT,
                user_agent TEXT,
                dicipta_pada TEXT NOT NULL
            )
        """)

    # Jadual Survey
    if USE_POSTGRES:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Survey (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                questions TEXT NOT NULL,
                created_by INTEGER,
                created_at TEXT,
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS SurveyResponse (
                id SERIAL PRIMARY KEY,
                survey_id INTEGER NOT NULL,
                answers TEXT NOT NULL,
                respondent_info TEXT DEFAULT '',
                submitted_at TEXT,
                FOREIGN KEY (survey_id) REFERENCES Survey(id)
            )
        """)
    else:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Survey (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                questions TEXT NOT NULL,
                created_by INTEGER,
                created_at TEXT,
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS SurveyResponse (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                survey_id INTEGER NOT NULL,
                answers TEXT NOT NULL,
                respondent_info TEXT DEFAULT '',
                submitted_at TEXT,
                FOREIGN KEY (survey_id) REFERENCES users(id)
            )
        """)

    # Indeks – sintaks sama untuk kedua-dua pangkalan data
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_pengundi_no_kp ON pengundi(no_kp)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_pengundi_nama ON pengundi(nama_penuh)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_pengundi_dm ON pengundi(dm)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_pengundi_status_rekod ON pengundi(status_rekod)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_pengundi_status_sokongan ON pengundi(status_sokongan)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_logs_username ON audit_logs(username)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_logs_tindakan ON audit_logs(tindakan)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_logs_dicipta ON audit_logs(dicipta_pada)
    """)

    db.commit()
    db.close()