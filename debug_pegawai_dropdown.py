"""
Diagnostic script to verify Pegawai Penyelaras dropdown data.
"""
from backend.database import get_db

db = get_db()
cursor = db.cursor()

print("=== LATEST 5 PEGAWAI PENYELARAS RECORDS ===")
cursor.execute("SELECT id, nama_penuh, no_kp, no_telefon, aktif FROM pegawai_penyelaras ORDER BY id DESC LIMIT 5")
for r in cursor.fetchall():
    d = dict(r)
    print(f"  ID={d['id']}, Nama={d['nama_penuh']}, KP={d['no_kp']}, Tel={d['no_telefon']}, Aktif={d['aktif']}")

print("\n=== SEARCH for 'KRIST' (aktif=1) ===")
cursor.execute("SELECT id, id AS no_kp, nama_penuh FROM pegawai_penyelaras WHERE aktif = 1 AND UPPER(nama_penuh) LIKE UPPER(?) ORDER BY nama_penuh", ('%KRIST%',))
for r in cursor.fetchall():
    d = dict(r)
    print(f"  ID={d['id']}, KP={d['no_kp']}, Nama={d['nama_penuh']}")

print("\n=== SEARCH for 'MAZMIEL' (aktif=1) ===")
cursor.execute("SELECT id, id AS no_kp, nama_penuh FROM pegawai_penyelaras WHERE aktif = 1 AND UPPER(nama_penuh) LIKE UPPER(?) ORDER BY nama_penuh", ('%MAZMIEL%',))
for r in cursor.fetchall():
    d = dict(r)
    print(f"  ID={d['id']}, KP={d['no_kp']}, Nama={d['nama_penuh']}")

print("\n=== ALL PEGAWAI (aktif=1) ===")
cursor.execute("SELECT id, nama_penuh, no_kp FROM pegawai_penyelaras WHERE aktif = 1 ORDER BY id")
all_rows = cursor.fetchall()
print(f"  Total active = {len(all_rows)}")
for r in all_rows:
    d = dict(r)
    print(f"  ID={d['id']}, Nama={d['nama_penuh']}, KP={d['no_kp'] or 'MISSING'}")

cursor.execute("SELECT COUNT(*) FROM pegawai_penyelaras WHERE aktif = 1")
total_aktif = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM pegawai_penyelaras")
total_all = cursor.fetchone()[0]
print(f"\nTotal: {total_all} records ({total_aktif} active)")

db.close()