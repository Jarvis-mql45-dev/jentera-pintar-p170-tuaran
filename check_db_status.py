"""
Check Supabase database status after schema apply and migration.
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

checks = [
    ("Total pengundi", "SELECT COUNT(*) FROM pengundi"),
    ("Parlimen", "SELECT COUNT(*) FROM parlimen"),
    ("DUN", "SELECT COUNT(*) FROM dun"),
    ("PDM", "SELECT COUNT(*) FROM pdm"),
    ("Kampung", "SELECT COUNT(*) FROM kampung"),
    ("Users", "SELECT COUNT(*) FROM users"),
    ("Parlimen records", "SELECT kod, nama FROM parlimen"),
    ("DUN records", "SELECT kod, nama FROM dun ORDER BY kod"),
    ("Voters by DUN", "SELECT d.kod, d.nama, COUNT(p.id) as jumlah FROM pengundi p JOIN dun d ON p.dun_id = d.id GROUP BY d.kod, d.nama ORDER BY d.kod"),
    ("Voters by status", "SELECT status_sokongan, COUNT(*) as jumlah FROM pengundi GROUP BY status_sokongan ORDER BY jumlah DESC"),
]

for label, sql in checks:
    try:
        cur.execute(sql)
        rows = cur.fetchall()
        if len(rows) == 1 and len(rows[0]) <= 2:
            print(f"✅ {label}: {rows[0][0]}")
        elif len(rows) > 0 and len(rows[0]) > 2:
            print(f"\n✅ {label}:")
            for r in rows:
                vals = ' · '.join([str(v) for v in r])
                print(f"   {vals}")
        else:
            print(f"\n✅ {label}:")
            for r in rows:
                print(f"   {r[0]} | {r[1]}")
    except Exception as e:
        print(f"⚠️  {label}: {str(e)[:80]}")

cur.close()
conn.close()
print("\n✅ Check complete")