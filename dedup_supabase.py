"""
Delete duplicate pengundi records from Supabase, keeping only the earliest (lowest ID) for each no_kp.
"""
import os
import sys

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
conn.autocommit = False
cur = conn.cursor()

print("=" * 60)
print("SUPABASE DEDUP - Delete duplicate pengundi records")
print("=" * 60)

# 1. Before counts
cur.execute("SELECT COUNT(*) FROM pengundi")
before = cur.fetchone()[0]
print(f"\nBefore: {before} records")

cur.execute("SELECT COUNT(DISTINCT no_kp) FROM pengundi")
unique_before = cur.fetchone()[0]
print(f"Unique no_kp: {unique_before}")
print(f"Excess rows: {before - unique_before}")

# 2. Count duplicates to delete by DUN
cur.execute("""
    SELECT d.kod, d.nama,
           COUNT(p.id) as total,
           COUNT(p.id) - COUNT(DISTINCT p.no_kp) as excess
    FROM pengundi p
    JOIN dun d ON p.dun_id = d.id
    GROUP BY d.kod, d.nama
    ORDER BY d.kod
""")
print(f"\nRecords by DUN (before dedup):")
for r in cur.fetchall():
    print(f"  {r[0]} {r[1]}: {r[2]} records, {r[3]} excess")

# 3. Delete duplicates using ctid (PostgreSQL physical row ID)
# Strategy: For each no_kp, keep only the row with the lowest id
print(f"\nDeleting duplicates...")

cur.execute("""
    DELETE FROM pengundi
    WHERE id NOT IN (
        SELECT MIN(id)
        FROM pengundi
        GROUP BY no_kp
    )
""")
deleted = cur.rowcount
print(f"Deleted: {deleted} duplicate rows")

conn.commit()

# 4. After counts
cur.execute("SELECT COUNT(*) FROM pengundi")
after = cur.fetchone()[0]
print(f"\nAfter: {after} records")

cur.execute("SELECT COUNT(DISTINCT no_kp) FROM pengundi")
unique_after = cur.fetchone()[0]
print(f"Unique no_kp: {unique_after}")
print(f"Still excess: {after - unique_after}")

if after == unique_after:
    print("✅ No duplicates remain!")
else:
    print("⚠️ Some duplicates remain — checking...")

# 5. Per-DUN after
cur.execute("""
    SELECT d.kod, d.nama, COUNT(p.id) as records
    FROM pengundi p
    JOIN dun d ON p.dun_id = d.id
    GROUP BY d.kod, d.nama
    ORDER BY d.kod
""")
print(f"\nRecords by DUN (after dedup):")
expected = {"N12": 18244, "N13": 26151, "N14": 26648, "N15": 17166}
total_after = 0
for r in cur.fetchall():
    total_after += r[2]
    exp = expected.get(r[0], 0)
    diff = r[2] - exp
    status = "✅" if diff == 0 else f"⚠️ +{diff}" if diff > 0 else f"🔴 {diff}"
    print(f"  {r[0]} {r[1]}: {r[2]} ({status})")
print(f"\n  TOTAL: {total_after}")
print(f"  EXPECTED: {sum(expected.values())}")
print(f"  DIFF: {total_after - sum(expected.values())}")

# 6. Verify no duplicates remain
cur.execute("""
    SELECT COUNT(*) FROM (
        SELECT no_kp FROM pengundi GROUP BY no_kp HAVING COUNT(*) > 1
    ) dups
""")
remaining_dups = cur.fetchone()[0]
if remaining_dups > 0:
    print(f"\n⚠️ {remaining_dups} duplicate no_kp groups remain!")
else:
    print(f"\n✅ All duplicates removed!")

cur.close()
conn.close()
print("\n✅ Dedup complete")