-- ============================================================
-- JENTERA PINTAR P170 TUARAN - ENABLE ROW LEVEL SECURITY
-- ============================================================
-- SAFETY: Connecting via direct DB user (postgres.hgweacgibbnynjviocje)
-- which BYPASSES RLS automatically (PostgreSQL owner rule).
-- So enabling RLS will NOT break the backend API.
-- It WILL block unauthenticated Supabase REST API queries (anon key).
-- ============================================================

-- 1. Enable RLS on ALL tables
ALTER TABLE IF EXISTS parlimen ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS dun ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS pdm ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS kampung ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS pengundi ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS users ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS "Survey" ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS "SurveyResponse" ENABLE ROW LEVEL SECURITY;

-- 2. Drop any default public access policies if they exist (clean slate)
DROP POLICY IF EXISTS "Enable read access for all users" ON parlimen;
DROP POLICY IF EXISTS "Enable read access for all users" ON dun;
DROP POLICY IF EXISTS "Enable read access for all users" ON pdm;
DROP POLICY IF EXISTS "Enable read access for all users" ON kampung;
DROP POLICY IF EXISTS "Enable read access for all users" ON pengundi;
DROP POLICY IF EXISTS "Enable read access for all users" ON users;
DROP POLICY IF EXISTS "Enable read access for all users" ON audit_logs;
DROP POLICY IF EXISTS "Enable read access for all users" ON "Survey";
DROP POLICY IF EXISTS "Enable read access for all users" ON "SurveyResponse";

-- 3. IMPORTANT: Do NOT create any public policies here.
--    The backend connects as the database owner (postgres.hgweacgibbnynjviocje),
--    which automatically bypasses RLS. No policies needed for owner access.
--    Supabase anon key will be blocked from direct table access.

-- 4. (Optional) Create authenticated-read policies for Supabase service_role access.
--    Only needed if you want Supabase Dashboard queries to work for these tables.
--    Uncomment if desired:
--
-- CREATE POLICY "auth_read_parlimen" ON parlimen FOR SELECT USING (auth.role() = 'authenticated');
-- CREATE POLICY "auth_read_dun" ON dun FOR SELECT USING (auth.role() = 'authenticated');
-- CREATE POLICY "auth_read_pdm" ON pdm FOR SELECT USING (auth.role() = 'authenticated');
-- CREATE POLICY "auth_read_kampung" ON kampung FOR SELECT USING (auth.role() = 'authenticated');
-- CREATE POLICY "auth_read_pengundi" ON pengundi FOR SELECT USING (auth.role() = 'authenticated');
-- CREATE POLICY "auth_read_users" ON users FOR SELECT USING (auth.role() = 'authenticated');
-- CREATE POLICY "auth_read_audit_logs" ON audit_logs FOR SELECT USING (auth.role() = 'authenticated');
-- CREATE POLICY "auth_read_Survey" ON "Survey" FOR SELECT USING (auth.role() = 'authenticated');
-- CREATE POLICY "auth_read_SurveyResponse" ON "SurveyResponse" FOR SELECT USING (auth.role() = 'authenticated');

-- Verification query:
-- SELECT schemaname, tablename, rowsecurity FROM pg_tables WHERE tablename IN ('parlimen','dun','pdm','kampung','pengundi','users','audit_logs','Survey','SurveyResponse');