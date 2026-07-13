"""
Final verification: compare Supabase counts vs Excel.
"""
import os, sys
env_path = '.env'
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                os.environ[key.strip()] = val.strip()

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("Missing DATABASE_URL")
    sys.exit(1)

import psycopg2
c = psycopg2.connect(DATABASE_URL)
cur = c.cursor()

print("=" * 60)
print("FINAL VERIFICATION")
print("=" * 60)

# 1. Raw total
cur.execute("SELECT COUNT(*) FROM pengundi")
raw = cur.fetchone()[0]
print(f"\nRaw total: {raw}")

# 2. Dashboard filter (Hidup + Sah)
cur.execute("SELECT COUNT(*) FROM pengundi WHERE status_fizikal = 'Hidup' AND status_rekod = 'Sah'")
dash = cur.fetchone()[0]
print(f"Dashboard filter (Hidup+Sah): {dash}")

# 3. By DUN (Hidup+Sah)
cur.execute("""
    SELECT d.kod, d.nama, COUNT(p.id)
    FROM pengundi p
    JOIN dun d ON p.dun_id = d.id
    WHERE p.status_fizikal = 'Hidup' AND p.status_rekod = 'Sah'
    GROUP BY d.kod, d.nama
    ORDER BY d.kod
""")
print(f"\nBy DUN (Hidup+Sah):")
for r in cur.fetchall():
    print(f"  {r[0]} {r[1]}: {r[2]}")

# 4. Expected from Excel
expected = {"N12": 18244, "N13": 26151, "N14": 26648, "N15": 17166}
print(f"\nExpected vs Actual (raw):")
cur.execute("""
    SELECT d.kod, d.nama, COUNT(p.id)
    FROM pengundi p
    JOIN dun d ON p.dun_id = d.id
    GROUP BY d.kod, d.nama
    ORDER BY d.kod
""")
total_diff = 0
for r in cur.fetchall():
    exp = expected[r[0]]
    act = r[2]
    diff = act - exp
    total_diff += diff
    status = "OK" if diff == 0 else f"+{diff}"
    print(f"  {r[0]} {r[1]}: exp={exp}, actual={act} ({status})")

print(f"\n  TOTAL diff: {total_diff}")

# 5. Unique no_kp by DUN (raw)
cur.execute("""
    SELECT d.kod, d.nama, COUNT(DISTINCT p.no_kp)
    FROM pengundi p
    JOIN dun d ON p.dun_id = d.id
    GROUP BY d.kod, d.nama
    ORDER BY d.kod
""")
print(f"\nUnique no_kp by DUN:")
for r in cur.fetchall():
    exp = expected[r[0]]
    diff = r[2] - exp
    print(f"  {r[0]} {r[1]}: {r[2]} (exp={exp}, diff={diff})")

# 6. Check if extra N12 records have duplicate no_kp across DUNs
cur.execute("""
    SELECT p.no_kp, COUNT(DISTINCT p.dun_id) as duns
    FROM pengundi p
    WHERE p.no_kp IN (
        SELECT no_kp FROM pengundi WHERE dun_id = (SELECT id FROM dun WHERE kod = 'N12')
    )
    GROUP BY p.no_kp
    HAVING COUNT(DISTINCT p.dun_id) > 1
    ORDER BY COUNT(p.id) DESC
    LIMIT 10
""")
cross_dun = cur.fetchall()
if cross_dun:
    print(f"\nN12 no_kp that also appear in OTHER DUNs:")
    for r in cross_dun:
        print(f"  no_kp={r[0]}, appears in {r[1]} different DUNs")
else:
    print(f"\nNo cross-DUN duplicates found.")

# 7. Sumber PDM breakdown
cur.execute("SELECT sumber_pdm, COUNT(*) FROM pengundi GROUP BY sumber_pdm ORDER BY COUNT(*) DESC")
print(f"\nBy sumber_pdm:")
for r in cur.fetchall():
    print(f"  {r[0] or 'NULL'}: {r[1]}")

# 8. Seed data
cur.execute("SELECT COUNT(*) FROM pengundi WHERE sumber_pdm = 'Seed Data'")
print(f"\nSeed Data records: {cur.fetchone()[0]}")

cur.close()
c.close()
print(f"\n{'='*60}")
print(f"TOTAL: {dash} voters (dashboard filter)")
print(f"FINAL: {raw} records (raw total)")