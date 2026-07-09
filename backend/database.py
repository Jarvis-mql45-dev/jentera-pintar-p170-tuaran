"""
Database abstraction layer for JenteraPintar P170 Tuaran.
Menyokong DUA mod:

1. SQLite (default – tempatan) – jika DATABASE_URL tidak diset
2. PostgreSQL – jika environment variable DATABASE_URL diset

Semua kod aplikasi TIDAK perlu diubah — antara muka cursor dikekalkan.
"""
import os
from datetime import datetime
from backend.config import settings
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
        # 0. Guard clause: jangan teruskan jika DSN kosong
        if not dsn or not dsn.strip():
            raise ValueError("DATABASE_URL tidak diset atau kosong — sambungan PostgreSQL tidak dapat dibuat")
        # 1. Dialect fix: psycopg2 hanya terima postgresql://, bukan postgres://
        if dsn.startswith("postgres://"):
            dsn = "postgresql://" + dsn[len("postgres://"):]
        # 2. Dalam production (Supabase/Vercel), pastikan SSL diwajibkan
        if settings.is_production and 'sslmode' not in dsn:
            separator = '&' if '?' in dsn else '?'
            dsn = f"{dsn}{separator}sslmode=require"
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
    Dibungkus dalam try/except supaya app tidak crash
    jika database gagal disambung (contoh: di Vercel Serverless).
    """
    try:
        try:
            db = get_db()
        except Exception as e:
            print(f"⚠️ Gagal dapatkan sambungan database: {e}", file=__import__('sys').stderr)
            print("   App akan terus berjalan — route database akan return error 500 jika diakses.", file=__import__('sys').stderr)
            return

        cursor = db.cursor()

        # =============================================================================
        # URUTAN PENTING: Cipta jadual HIERARKI DAHULU sebelum pengundi (FK reference)
        # =============================================================================

        # 1. parlimen (hierarki tertinggi)
        if USE_POSTGRES:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS parlimen (
                    id SERIAL PRIMARY KEY,
                    kod VARCHAR(10) UNIQUE NOT NULL,
                    nama TEXT NOT NULL,
                    keterangan TEXT,
                    dicipta_pada TEXT
                )
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS parlimen (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kod TEXT UNIQUE NOT NULL,
                    nama TEXT NOT NULL,
                    keterangan TEXT,
                    dicipta_pada TEXT
                )
            """)

        # 2. dun (FK → parlimen)
        if USE_POSTGRES:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dun (
                    id SERIAL PRIMARY KEY,
                    parlimen_id INTEGER NOT NULL REFERENCES parlimen(id),
                    kod VARCHAR(10) UNIQUE NOT NULL,
                    nama TEXT NOT NULL,
                    keterangan TEXT,
                    dicipta_pada TEXT
                )
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dun (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    parlimen_id INTEGER NOT NULL REFERENCES parlimen(id),
                    kod TEXT UNIQUE NOT NULL,
                    nama TEXT NOT NULL,
                    keterangan TEXT,
                    dicipta_pada TEXT
                )
            """)

        # 3. pdm (FK → dun)
        if USE_POSTGRES:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pdm (
                    id SERIAL PRIMARY KEY,
                    dun_id INTEGER NOT NULL REFERENCES dun(id),
                    kod VARCHAR(20),
                    nama TEXT NOT NULL,
                    keterangan TEXT,
                    dicipta_pada TEXT
                )
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pdm (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dun_id INTEGER NOT NULL REFERENCES dun(id),
                    kod TEXT,
                    nama TEXT NOT NULL,
                    keterangan TEXT,
                    dicipta_pada TEXT
                )
            """)

        # 4. kampung (FK → pdm)
        if USE_POSTGRES:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS kampung (
                    id SERIAL PRIMARY KEY,
                    pdm_id INTEGER NOT NULL REFERENCES pdm(id),
                    nama TEXT NOT NULL,
                    keterangan TEXT,
                    dicipta_pada TEXT
                )
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS kampung (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pdm_id INTEGER NOT NULL REFERENCES pdm(id),
                    nama TEXT NOT NULL,
                    keterangan TEXT,
                    dicipta_pada TEXT
                )
            """)

        # Seed data awal untuk parlimen P170 Tuaran dan 4 DUN (selepas jadual wujud)
        now_str = datetime.now().isoformat()
        cursor.execute("SELECT COUNT(*) FROM parlimen")
        if cursor.fetchone()[0] == 0:
            if USE_POSTGRES:
                cursor.execute(
                    "INSERT INTO parlimen (kod, nama, keterangan, dicipta_pada) VALUES (%s, %s, %s, %s)",
                    ("P170", "Tuaran", "Parlimen P170 Tuaran, Sabah", now_str)
                )
                parlimen_id = cursor.lastrowid
                cursor.execute(
                    "INSERT INTO dun (parlimen_id, kod, nama, keterangan, dicipta_pada) VALUES (%s, %s, %s, %s, %s)",
                    (parlimen_id, "N12", "Sulaman", "DUN N12 Sulaman", now_str)
                )
                cursor.execute(
                    "INSERT INTO dun (parlimen_id, kod, nama, keterangan, dicipta_pada) VALUES (%s, %s, %s, %s, %s)",
                    (parlimen_id, "N13", "Pantai Dalit", "DUN N13 Pantai Dalit", now_str)
                )
                cursor.execute(
                    "INSERT INTO dun (parlimen_id, kod, nama, keterangan, dicipta_pada) VALUES (%s, %s, %s, %s, %s)",
                    (parlimen_id, "N14", "Tamparuli", "DUN N14 Tamparuli", now_str)
                )
                cursor.execute(
                    "INSERT INTO dun (parlimen_id, kod, nama, keterangan, dicipta_pada) VALUES (%s, %s, %s, %s, %s)",
                    (parlimen_id, "N15", "Kiulu", "DUN N15 Kiulu", now_str)
                )
            else:
                cursor.execute(
                    "INSERT INTO parlimen (kod, nama, keterangan, dicipta_pada) VALUES (?, ?, ?, ?)",
                    ("P170", "Tuaran", "Parlimen P170 Tuaran, Sabah", now_str)
                )
                parlimen_id = cursor.lastrowid
                cursor.execute(
                    "INSERT INTO dun (parlimen_id, kod, nama, keterangan, dicipta_pada) VALUES (?, ?, ?, ?, ?)",
                    (parlimen_id, "N12", "Sulaman", "DUN N12 Sulaman", now_str)
                )
                cursor.execute(
                    "INSERT INTO dun (parlimen_id, kod, nama, keterangan, dicipta_pada) VALUES (?, ?, ?, ?, ?)",
                    (parlimen_id, "N13", "Pantai Dalit", "DUN N13 Pantai Dalit", now_str)
                )
                cursor.execute(
                    "INSERT INTO dun (parlimen_id, kod, nama, keterangan, dicipta_pada) VALUES (?, ?, ?, ?, ?)",
                    (parlimen_id, "N14", "Tamparuli", "DUN N14 Tamparuli", now_str)
                )
                cursor.execute(
                    "INSERT INTO dun (parlimen_id, kod, nama, keterangan, dicipta_pada) VALUES (?, ?, ?, ?, ?)",
                    (parlimen_id, "N15", "Kiulu", "DUN N15 Kiulu", now_str)
                )
            print("✅ Seed data parlimen & DUN untuk P170 Tuaran telah dimasukkan")

        # 5. users (RBAC)
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

        # 6. pengundi (FK ke parlimen, dun, pdm, kampung - semua dah wujud)
        if USE_POSTGRES:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pengundi (
                    id SERIAL PRIMARY KEY,
                    no_kp VARCHAR(20),
                    nama_penuh TEXT,
                    jantina VARCHAR(1),
                    tahun_lahir INTEGER,
                    parlimen_id INTEGER REFERENCES parlimen(id),
                    dun_id INTEGER REFERENCES dun(id),
                    pdm_id INTEGER REFERENCES pdm(id),
                    kampung_id INTEGER REFERENCES kampung(id),
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
                    parlimen_id INTEGER REFERENCES parlimen(id),
                    dun_id INTEGER REFERENCES dun(id),
                    pdm_id INTEGER REFERENCES pdm(id),
                    kampung_id INTEGER REFERENCES kampung(id),
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

        # 7. audit_logs
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

        # 8. Survey
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
            CREATE INDEX IF NOT EXISTS idx_parlimen_kod ON parlimen(kod)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_dun_kod ON dun(kod)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_dun_parlimen_id ON dun(parlimen_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_pdm_dun_id ON pdm(dun_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_kampung_pdm_id ON kampung(pdm_id)
        """)
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
    except Exception as e:
        print(f"⚠️ Gagal init database: {e}", file=__import__('sys').stderr)
        import traceback
        traceback.print_exc()
