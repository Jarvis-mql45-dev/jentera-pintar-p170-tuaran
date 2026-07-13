-- =============================================================================
-- JENTERA PINTAR P170 TUARAN — PostgreSQL Full Schema Recovery
-- Source: backend/database.py (init_db), backend/migrate_schema.sql
-- Idempotent: CREATE TABLE IF NOT EXISTS — safe to run on existing DB
-- =============================================================================

-- 1. PARLIMEN (Hierarki tertinggi — P170 Tuaran)
CREATE TABLE IF NOT EXISTS parlimen (
    id SERIAL PRIMARY KEY,
    kod VARCHAR(10) UNIQUE NOT NULL,
    nama TEXT NOT NULL,
    keterangan TEXT,
    dicipta_pada TEXT
);

-- 2. DUN (FK → parlimen — N12, N13, N14, N15)
CREATE TABLE IF NOT EXISTS dun (
    id SERIAL PRIMARY KEY,
    parlimen_id INTEGER NOT NULL REFERENCES parlimen(id),
    kod VARCHAR(10) UNIQUE NOT NULL,
    nama TEXT NOT NULL,
    keterangan TEXT,
    dicipta_pada TEXT
);

-- 3. PDM (FK → dun)
CREATE TABLE IF NOT EXISTS pdm (
    id SERIAL PRIMARY KEY,
    dun_id INTEGER NOT NULL REFERENCES dun(id),
    kod VARCHAR(20),
    nama TEXT NOT NULL,
    keterangan TEXT,
    dicipta_pada TEXT
);

-- 4. KAMPUNG (FK → pdm)
CREATE TABLE IF NOT EXISTS kampung (
    id SERIAL PRIMARY KEY,
    pdm_id INTEGER NOT NULL REFERENCES pdm(id),
    nama TEXT NOT NULL,
    keterangan TEXT,
    dicipta_pada TEXT
);

-- 5. USERS (RBAC — login/auth)
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

-- 6. PENGUNDI (Main data — all dashboard queries)
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
    dicipta_pada TEXT,
    ketua_keluarga_id INTEGER REFERENCES pengundi(id),
    pegawai_penyelaras_id INTEGER REFERENCES pengundi(id)
);

-- 7. AUDIT_LOGS (PDPA compliance)
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

-- 8. SURVEY (Soal Selidik)
CREATE TABLE IF NOT EXISTS Survey (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    questions TEXT NOT NULL,
    created_by INTEGER REFERENCES users(id),
    created_at TEXT
);

-- 9. SURVEY RESPONSE
CREATE TABLE IF NOT EXISTS SurveyResponse (
    id SERIAL PRIMARY KEY,
    survey_id INTEGER NOT NULL REFERENCES Survey(id),
    answers TEXT NOT NULL,
    respondent_info TEXT DEFAULT '',
    submitted_at TEXT
);

-- =============================================================================
-- INDEXES
-- =============================================================================
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
CREATE INDEX IF NOT EXISTS idx_pengundi_ketua_keluarga ON pengundi(ketua_keluarga_id);
CREATE INDEX IF NOT EXISTS idx_pengundi_pegawai_penyelaras ON pengundi(pegawai_penyelaras_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_username ON audit_logs(username);
CREATE INDEX IF NOT EXISTS idx_audit_logs_tindakan ON audit_logs(tindakan);
CREATE INDEX IF NOT EXISTS idx_audit_logs_dicipta ON audit_logs(dicipta_pada);

-- =============================================================================
-- SEED DATA (parlimen P170 + 4 DUN)
-- =============================================================================
INSERT INTO parlimen (kod, nama, keterangan, dicipta_pada)
SELECT 'P170', 'Tuaran', 'Parlimen P170 Tuaran, Sabah', NOW()::TEXT
WHERE NOT EXISTS (SELECT 1 FROM parlimen WHERE kod = 'P170');

INSERT INTO dun (parlimen_id, kod, nama, keterangan, dicipta_pada)
SELECT p.id, 'N12', 'Sulaman', 'DUN N12 Sulaman', NOW()::TEXT
FROM parlimen p WHERE p.kod = 'P170'
AND NOT EXISTS (SELECT 1 FROM dun WHERE kod = 'N12');

INSERT INTO dun (parlimen_id, kod, nama, keterangan, dicipta_pada)
SELECT p.id, 'N13', 'Pantai Dalit', 'DUN N13 Pantai Dalit', NOW()::TEXT
FROM parlimen p WHERE p.kod = 'P170'
AND NOT EXISTS (SELECT 1 FROM dun WHERE kod = 'N13');

INSERT INTO dun (parlimen_id, kod, nama, keterangan, dicipta_pada)
SELECT p.id, 'N14', 'Tamparuli', 'DUN N14 Tamparuli', NOW()::TEXT
FROM parlimen p WHERE p.kod = 'P170'
AND NOT EXISTS (SELECT 1 FROM dun WHERE kod = 'N14');

INSERT INTO dun (parlimen_id, kod, nama, keterangan, dicipta_pada)
SELECT p.id, 'N15', 'Kiulu', 'DUN N15 Kiulu', NOW()::TEXT
FROM parlimen p WHERE p.kod = 'P170'
AND NOT EXISTS (SELECT 1 FROM dun WHERE kod = 'N15');