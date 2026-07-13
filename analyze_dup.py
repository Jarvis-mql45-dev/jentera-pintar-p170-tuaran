"""
Analyze duplicate records in Supabase pengundi table.
"""
import os
import sys

# Load .env
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                os.environ[key.strip()] = val.strip()

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("❌ DATABASE_URL not found")
    sys.exit(1)

import psycopg2
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

print("=" * 60)
print("DUPLICATE ANALYSIS - SUPABASE PENGUNDI")
print("=" * 60)

# 1. Total records
cur.execute("SELECT COUNT(*) FROM pengundi")
total = cur.fetchone()[0]
print(f"\nTotal records: {total}")

# 2. Unique no_kp
cur.execute("SELECT COUNT(DISTINCT no_kp) FROM pengundi")
unique = cur.fetchone()[0]
print(f"Unique no_kp:  {unique}")
print(f"Duplicates:    {total - unique}")

# 3. Duplicate count distribution
cur.execute("""
    SELECT dup_count, COUNT(*) as groups
    FROM (
        SELECT COUNT(*) as dup_count
        FROM pengundi
        GROUP BY no_kp
    ) sub
    GROUP BY dup_count
    ORDER BY dup_count
""")
print(f"\nDuplicate distribution:")
for r in cur.fetchall():
    print(f"  {r[0]}x copies: {r[1]} no_kp groups")

# 4. Exact duplicate count per DUN
cur.execute("""
    SELECT d.kod, d.nama,
           COUNT(p.id) as total_records,
           (SELECT COUNT(*) FROM pengundi p2 WHERE p2.dun_id = d.id GROUP BY p2.no_kp HAVING COUNT(*) > 1) as dup_groups
    FROM pengundi p
    JOIN dun d ON p.dun_id = d.id
    GROUP BY d.kod, d.nama
    ORDER BY d.kod
""")
print(f"\nRecords by DUN:")
for r in cur.fetchall():
    print(f"  {r[0]} {r[1]}: {r[2]} total records")

# 5. Expected count vs actual
expected = {
    "N12": 18244,  # from individual Excel
    "N13": 26151,
    "N14": 26648,
    "N15": 17166,
}
print(f"\nExpected vs Actual:")
total_expected = 0
total_actual = 0
cur.execute("SELECT d.kod, d.nama, COUNT(p.id) FROM pengundi p JOIN dun d ON p.dun_id = d.id GROUP BY d.kod, d.nama ORDER BY d.kod")
for r in cur.fetchall():
    exp = expected.get(r[0], 0)
    act = r[2]
    diff = act - exp
    total_expected += exp
    total_actual += act
    status = "✅" if diff == 0 else f"⚠️ +{diff}" if diff > 0 else f"🔴 {diff}"
    print(f"  {r[0]} {r[1]}: exp={exp}, actual={act} ({status})")
print(f"\n  TOTAL: exp={total_expected}, actual={total_actual}, diff={total_actual - total_expected}")

# 6. Check for seed_data sample records
cur.execute("SELECT COUNT(*) FROM pengundi WHERE sumber_pdm = 'Seed Data'")
seed_count = cur.fetchone()[0]
print(f"\nSeed Data (sample) records: {seed_count}")

# 7. Records by sumber_pdm
cur.execute("SELECT sumber_pdm, COUNT(*) FROM pengundi GROUP BY sumber_pdm ORDER BY COUNT(*) DESC")
print(f"Records by sumber_pdm:")
for r in cur.fetchall():
    print(f"  {r[0] or 'NULL'}: {r[1]}")

# 8. Show samples of duplicate no_kp
cur.execute("""
    SELECT no_kp, nama_penuh, dun_id, sumber_pdm, status_fizikal, status_rekod
    FROM pengundi
    WHERE no_kp IN (
        SELECT no_kp FROM pengundi GROUP BY no_kp HAVING COUNT(*) > 1
    )
    ORDER BY no_kp, id
    LIMIT 20
""")
dups = cur.fetchall()
if dups:
    print(f"\nSample duplicates (first 20 rows):")
    for r in dups:
        print(f"  no_kp={r[0]}, nama={r[1][:20]}, dun_id={r[2]}, sumber={r[3]}, fizikal={r[4]}, rekod={r[5]}")

cur.close()
conn.close()
print("\n✅ Analysis complete")