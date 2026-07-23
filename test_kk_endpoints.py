"""
Test KK endpoints locally after fixing dun_id -> dun
"""
import os, sys
sys.path.insert(0, '.')
from backend.database import get_db

db = get_db()
cursor = db.cursor()

print("=" * 60)
print("TEST: /api/ketua-keluarga/stats (simulated)")
print("=" * 60)

# Total Ketua Keluarga aktif
cursor.execute("SELECT COUNT(*) FROM ketua_keluarga WHERE is_active = 1")
total_ketua = cursor.fetchone()[0]
print(f"  total_ketua: {total_ketua}")

# Total Ahli Keluarga (pengundi yang terikat dengan mana-mana KK)
cursor.execute("""
    SELECT COUNT(DISTINCT p.id) 
    FROM pengundi p
    JOIN ketua_keluarga kk ON kk.id = p.ketua_keluarga_id
    WHERE kk.is_active = 1 AND p.status_fizikal = 'Hidup' AND p.status_rekod = 'Sah'
""")
ahli_terikat = cursor.fetchone()[0]
print(f"  ahli_terikat: {ahli_terikat}")

# DUN coverage - FIXED: use kk.dun (text) instead of kk.dun_id (FK)
cursor.execute("""
    SELECT COUNT(DISTINCT d.kod) 
    FROM ketua_keluarga kk
    JOIN dun d ON d.kod = UPPER(kk.dun)
    WHERE kk.is_active = 1 AND kk.dun IS NOT NULL AND kk.dun != ''
""")
dun_covered = cursor.fetchone()[0]
print(f"  dun_covered: {dun_covered}")

cursor.execute("SELECT COUNT(*) FROM dun")
total_dun = cursor.fetchone()[0]
print(f"  total_dun: {total_dun}")

# PDM coverage
cursor.execute("""
    SELECT COUNT(DISTINCT kk.dm) 
    FROM ketua_keluarga kk
    WHERE kk.is_active = 1 AND kk.dm IS NOT NULL AND kk.dm != ''
""")
pdm_covered = cursor.fetchone()[0]
print(f"  pdm_covered: {pdm_covered}")

cursor.execute("SELECT COUNT(*) FROM pdm")
total_pdm = cursor.fetchone()[0]
print(f"  total_pdm: {total_pdm}")

print()
print("=" * 60)
print("TEST: /api/ketua-keluarga/list (simulated)")
print("=" * 60)

cursor.execute("""
    SELECT kk.id, kk.nama_penuh,
           COALESCE(kk.no_kp, '') AS no_kp,
           COALESCE(kk.no_telefon, '') AS no_telefon,
           kk.dm, kk.dicipta_pada,
           COALESCE((SELECT COUNT(*) FROM pengundi p 
                     WHERE p.ketua_keluarga_id = kk.id 
                     AND p.status_fizikal = 'Hidup' 
                     AND p.status_rekod = 'Sah'), 0) AS jumlah_pengundi,
           d.kod AS dun_kod,
           d.nama AS dun_nama
    FROM ketua_keluarga kk
    LEFT JOIN dun d ON d.kod = UPPER(kk.dun)
    WHERE kk.is_active = 1
    ORDER BY kk.nama_penuh
""")

rows = cursor.fetchall()
print(f"  Total records returned: {len(rows)}")
print()
for r in rows:
    print(f"  ID={r[0]:3d} | {r[1]:35s} | KP={r[2]:15s} | DM={str(r[4]):15s} | DUN={str(r[7]):6s} | Ahli={r[6]}")

print()
print("✅ DONE - No SQL errors!")
db.close()