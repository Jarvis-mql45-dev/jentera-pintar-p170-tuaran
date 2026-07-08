-- ============================================================
-- JENTERA PINTAR P170 TUARAN - PostgreSQL Schema Migration
-- ============================================================
-- Skema diperluas untuk menyokong hierarki:
--   parlimen (P170) → dun (N12,N13,N14,N15) → pdm → kampung
--
-- Cara guna (psql):
--   psql "postgresql://user:pass@ep-xxx.aws.neon.tech/dbname" -f migrate_schema.sql
--
-- Atau guna pgAdmin / SQL Editor di Neon Dashboard:
--   Salin dan tampal kandungan fail ini.

-- ============================================================
-- 1. JADUAL: parlimen (Hierarki tertinggi - contoh: P170 Tuaran)
-- ============================================================
CREATE TABLE IF NOT EXISTS parlimen (
    id SERIAL PRIMARY KEY,
    kod VARCHAR(10) UNIQUE NOT NULL,        -- Contoh: "P170"
    nama TEXT NOT NULL,                      -- Contoh: "Tuaran"
    keterangan TEXT,
    dicipta_pada TEXT
);

-- Data awal untuk P170 Tuaran
INSERT INTO parlimen (kod, nama, keterangan, dicipta_pada)
SELECT 'P170', 'Tuaran', 'Parlimen P170 Tuaran, Sabah', datetime('now')
WHERE NOT EXISTS (SELECT 1 FROM parlimen WHERE kod = 'P170');

-- ============================================================
-- 2. JADUAL: dun (Dewan Undangan Negeri - FK ke parlimen)
-- ============================================================
CREATE TABLE IF NOT EXISTS dun (
    id SERIAL PRIMARY KEY,
    parlimen_id INTEGER NOT NULL REFERENCES parlimen(id),
    kod VARCHAR(10) UNIQUE NOT NULL,        -- Contoh: "N12", "N13", "N14", "N15"
    nama TEXT NOT NULL,                      -- Contoh: "Sulaman", "Pantai Dalit", dll.
    keterangan TEXT,
    dicipta_pada TEXT
);

-- Data awal untuk 4 DUN dalam P170 Tuaran
INSERT INTO dun (parlimen_id, kod, nama, keterangan, dicipta_pada)
SELECT p.id, 'N12', 'Sulaman', 'DUN N12 Sulaman', datetime('now')
FROM parlimen p WHERE p.kod = 'P170'
AND NOT EXISTS (SELECT 1 FROM dun WHERE kod = 'N12');

INSERT INTO dun (parlimen_id, kod, nama, keterangan, dicipta_pada)
SELECT p.id, 'N13', 'Pantai Dalit', 'DUN N13 Pantai Dalit', datetime('now')
FROM parlimen p WHERE p.kod = 'P170'
AND NOT EXISTS (SELECT 1 FROM dun WHERE kod = 'N13');

INSERT INTO dun (parlimen_id, kod, nama, keterangan, dicipta_pada)
SELECT p.id, 'N14', 'Tamparuli', 'DUN N14 Tamparuli', datetime('now')
FROM parlimen p WHERE p.kod = 'P170'
AND NOT EXISTS (SELECT 1 FROM dun WHERE kod = 'N14');

INSERT INTO dun (parlimen_id, kod, nama, keterangan, dicipta_pada)
SELECT p.id, 'N15', 'Kiulu', 'DUN N15 Kiulu', datetime('now')
FROM parlimen p WHERE p.kod = 'P170'
AND NOT EXISTS (SELECT 1 FROM dun WHERE kod = 'N15');

-- ============================================================
-- 3. JADUAL: pdm (Pusat Daerah Mengundi - FK ke dun)
-- ============================================================
CREATE TABLE IF NOT EXISTS pdm (
    id SERIAL PRIMARY KEY,
    dun_id INTEGER NOT NULL REFERENCES dun(id),
    kod VARCHAR(20),
    nama TEXT NOT NULL,                      -- Contoh: "PDM BINGOLON", "PDM DUALOG", dll.
    keterangan TEXT,
    dicipta_pada TEXT
);

-- ============================================================
-- 4. JADUAL: kampung (Lokaliti - FK ke pdm)
-- ============================================================
CREATE TABLE IF NOT EXISTS kampung (
    id SERIAL PRIMARY KEY,
    pdm_id INTEGER NOT NULL REFERENCES pdm(id),
    nama TEXT NOT NULL,                      -- Contoh: "Kampung Bingolon", dll.
    keterangan TEXT,
    dicipta_pada TEXT
);

-- ============================================================
-- 5. JADUAL: users (RBAC – Role Based Access Control)
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
-- 6. JADUAL: pengundi (Data utama pengundi - dengan FK ke hierarki)
-- ============================================================
CREATE TABLE IF NOT EXISTS pengundi (
    id SERIAL PRIMARY KEY,
    no_kp VARCHAR(20),
    nama_penuh TEXT,
    jantina VARCHAR(1),
    tahun_lahir INTEGER,
    -- Kolum FK baru untuk hierarki (guna JOIN dengan jadual rujukan)
    parlimen_id INTEGER REFERENCES parlimen(id),
    dun_id INTEGER REFERENCES dun(id),
    pdm_id INTEGER REFERENCES pdm(id),
    kampung_id INTEGER REFERENCES kampung(id),
    -- Kolum text asal dikekalkan untuk backward compatibility
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
-- 7. JADUAL: audit_logs (Pematuhan PDPA)
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
-- 8. JADUAL: Survey (Soal Selidik)
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
-- 9. JADUAL: SurveyResponse (Respons Soal Selidik)
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
-- 10. INDEKS (Pengoptimuman Carian)
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_parlimen_kod ON parlimen(kod);
CREATE INDEX IF NOT EXISTS idx_dun_kod ON dun(kod);
CREATE INDEX IF NOT EXISTS idx_dun_parlimen_id ON dun(parlimen_id);
CREATE INDEX IF NOT EXISTS idx_pdm_dun_id ON pdm(dun_id);
CREATE INDEX IF NOT EXISTS idx_kampung_pdm_id ON kampung(pdm_id);
CREATE INDEX IF NOT EXISTS idx_pengundi_no_kp ON pengundi(no_kp);
CREATE INDEX IF NOT EXISTS idx_pengundi_nama ON pengundi(nama_penuh);
CREATE INDEX IF NOT EXISTS idx_pengundi_dm ON pengundi(dm);
CREATE INDEX IF NOT EXISTS idx_pengundi_status_rekod ON pengundi(status_rekod);
CREATE INDEX IF NOT EXISTS idx_pengundi_status_sokongan ON pengundi(status_sokongan);
CREATE INDEX IF NOT EXISTS idx_pengundi_parlimen_id ON pengundi(parlimen_id);
CREATE INDEX IF NOT EXISTS idx_pengundi_dun_id ON pengundi(dun_id);
CREATE INDEX IF NOT EXISTS idx_pengundi_pdm_id ON pengundi(pdm_id);
CREATE INDEX IF NOT EXISTS idx_pengundi_kampung_id ON pengundi(kampung_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_username ON audit_logs(username);
CREATE INDEX IF NOT EXISTS idx_audit_logs_tindakan ON audit_logs(tindakan);
CREATE INDEX IF NOT EXISTS idx_audit_logs_dicipta ON audit_logs(dicipta_pada);

-- ============================================================
-- SELESAI – Semua jadual dan indeks telah dibina.
-- ============================================================