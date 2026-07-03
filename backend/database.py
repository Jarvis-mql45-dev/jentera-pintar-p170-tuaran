import sqlite3
from config import settings


def get_db():
    conn = sqlite3.connect(settings.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Table users for RBAC
    cursor.execute('''
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
    ''')

    # Table pengundi (already created by migrasi.py, but ensure it exists)
    cursor.execute('''
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
    ''')

    # Table audit_logs for PDPA compliance
    cursor.execute('''
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
    ''')

    # Create indexes if not exist
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_pengundi_no_kp ON pengundi(no_kp)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_pengundi_nama ON pengundi(nama_penuh)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_pengundi_dm ON pengundi(dm)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_pengundi_status_rekod ON pengundi(status_rekod)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_pengundi_status_sokongan ON pengundi(status_sokongan)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_audit_logs_username ON audit_logs(username)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_audit_logs_tindakan ON audit_logs(tindakan)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_audit_logs_dicipta ON audit_logs(dicipta_pada)
    ''')

    # Table Survey for survey/quiz system
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Survey (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            questions TEXT NOT NULL,
            created_by INTEGER,
            created_at TEXT,
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    ''')

    # Table SurveyResponse for survey answers
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS SurveyResponse (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            survey_id INTEGER NOT NULL,
            answers TEXT NOT NULL,
            respondent_info TEXT DEFAULT '',
            submitted_at TEXT,
            FOREIGN KEY (survey_id) REFERENCES Survey(id)
        )
    ''')

    conn.commit()
    conn.close()
