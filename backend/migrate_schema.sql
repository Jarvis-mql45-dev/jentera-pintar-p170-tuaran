-- ============================================================
-- JENTERA PINTAR N05 MATUNGGONG - PostgreSQL Schema Migration
-- ============================================================
-- Guna skrip ini untuk membina jadual di Neon (PostgreSQL).
--
-- Cara guna (psql):
--   psql "postgresql://user:pass@ep-xxx.aws.neon.tech/dbname" -f migrate_schema.sql
--
-- Atau guna pgAdmin / SQL Editor di Neon Dashboard:
--   Salin dan tampal kandungan fail ini.

-- ============================================================
-- 1. JADUAL: users (RBAC – Role Based Access Control)
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    nama_penuh TEXT,
    kata_laluan TEXT NOT NULL,
    peranan VARCHAR(100) NOT NULL DEFAULT 'Pemerhati',
    dm TEXT,
    aktif INTEGER DEFAULT 1,
    dicipta_pada TEXT
);

-- ============================================================
-- 2. JADUAL: pengundi (Data utama pengundi)
-- ============================================================
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
);

-- ============================================================
-- 3. JADUAL: audit_logs (Pematuhan PDPA)
-- ============================================================
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
);

-- ============================================================
-- 4. JADUAL: Survey (Soal Selidik)
-- ============================================================
CREATE TABLE IF NOT EXISTS Survey (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    questions TEXT NOT NULL,
    created_by INTEGER,
    created_at TEXT,
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- ============================================================
-- 5. JADUAL: SurveyResponse (Respons Soal Selidik)
-- ============================================================
CREATE TABLE IF NOT EXISTS SurveyResponse (
    id SERIAL PRIMARY KEY,
    survey_id INTEGER NOT NULL,
    answers TEXT NOT NULL,
    respondent_info TEXT DEFAULT '',
    submitted_at TEXT,
    FOREIGN KEY (survey_id) REFERENCES Survey(id)
);

-- ============================================================
-- 6. INDEKS (Pengoptimuman Carian)
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_pengundi_no_kp ON pengundi(no_kp);
CREATE INDEX IF NOT EXISTS idx_pengundi_nama ON pengundi(nama_penuh);
CREATE INDEX IF NOT EXISTS idx_pengundi_dm ON pengundi(dm);
CREATE INDEX IF NOT EXISTS idx_pengundi_status_rekod ON pengundi(status_rekod);
CREATE INDEX IF NOT EXISTS idx_pengundi_status_sokongan ON pengundi(status_sokongan);
CREATE INDEX IF NOT EXISTS idx_audit_logs_username ON audit_logs(username);
CREATE INDEX IF NOT EXISTS idx_audit_logs_tindakan ON audit_logs(tindakan);
CREATE INDEX IF NOT EXISTS idx_audit_logs_dicipta ON audit_logs(dicipta_pada);

-- ============================================================
-- SELESAI – Semua jadual dan indeks telah dibina.
-- ============================================================