"""
N12 Final Fix: The dedup used EXACT string matching on no_kp.
But some no_kp were stored as 9-digit (no leading zeros) in one migration
and 12-digit (with leading zeros) in another migration.

The dedup treated '102120143' and '000102120143' as DIFFERENT voters,
so both were kept. This script:
1. Normalises ALL no_kp to 12 digits (left pad with zeros)
2. Re-runs dedup to remove the true duplicates
3. Verifies count matches Excel exactly
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

import psycopg2
conn = psycopg2.connect(os.environ['DATABASE_URL'])
conn.autocommit = False
cur = conn.cursor()

print("=" * 60)
print("N12 FINAL FIX - Normalise + Dedup")
print("=" * 60)

# Before counts
cur.execute("SELECT COUNT(*) FROM pengundi")
print(f"\nTotal DB records: {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(DISTINCT no_kp) FROM pengundi")
print(f"Unique no_kp: {cur.fetchone()[0]}")

# 1. Find all no_kp shorter than 12 digits (they lost leading zeros)
cur.execute("""
    SELECT id, no_kp, LENGTH(no_kp)
    FROM pengundi
    WHERE LENGTH(no_kp) < 12 AND no_kp ~ '^\d+$'
    ORDER BY id
""")
short_rows = cur.fetchall()
print(f"\nRecords with <12 digit no_kp: {len(short_rows)}")
if short_rows:
    print("Sample:")
    for r in short_rows[:5]:
        print(f"  id={r[0]}, no_kp='{r[1]}' ({r[2]} digits)")

# 2. Normalise: Pad all short no_kp to 12 digits
print(f"\nNormalising {len(short_rows)} records to 12 digits...")
cur.execute("""
    UPDATE pengundi
    SET no_kp = LPAD(no_kp, 12, '0')
    WHERE LENGTH(no_kp) < 12 AND no_kp ~ '^\d+$'
""")
updated = cur.rowcount
print(f"Updated: {updated} records")
conn.commit()

# Verify: Now find any <12 digit no_kp remaining
cur.execute("SELECT COUNT(*) FROM pengundi WHERE LENGTH(no_kp) < 12 AND no_kp ~ '^\d+$'")
remaining_short = cur.fetchone()[0]
print(f"Still <12 digits after fix: {remaining_short}")
if remaining_short > 0:
    cur.execute("SELECT no_kp FROM pengundi WHERE LENGTH(no_kp) < 12 AND no_kp ~ '^\d+$' LIMIT 10")
    for r in cur.fetchall():
        print(f"  Remaining: '{r[0]}'")

# 3. Now re-run dedup — this time the groups will collapse correctly
print(f"\nRunning dedup on normalised data...")
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
after_total = cur.fetchone()[0]
print(f"\nAfter fix - total records: {after_total}")

cur.execute("SELECT COUNT(DISTINCT no_kp) FROM pengundi")
after_unique = cur.fetchone()[0]
print(f"After fix - unique no_kp: {after_unique}")
print(f"Excess: {after_total - after_unique}")

# 5. Per-DUN
expected = {"N12": 18244, "N13": 26151, "N14": 26648, "N15": 17166}
cur.execute("""
    SELECT d.kod, d.nama, COUNT(p.id) as records, COUNT(DISTINCT p.no_kp) as unique_nok
    FROM pengundi p
    JOIN dun d ON p.dun_id = d.id
    GROUP BY d.kod, d.nama
    ORDER BY d.kod
""")
print(f"\nFinal per-DUN:")
for r in cur.fetchall():
    exp = expected.get(r[0], 0)
    diff = r[2] - exp
    status = "✅" if diff == 0 else f"⚠️ +{diff}" if diff > 0 else f"🔴 {diff}"
    print(f"  {r[0]} {r[1]}: {r[2]} records, {r[3]} unique (expected {exp}) {status}")

cur.close()
conn.close()
print(f"\n✅ Fix complete")