"""
Verify the KK double-counting fix in /api/dashboard/pdm/{dun_kod}
"""
import os, sys
sys.path.insert(0, '.')
from backend.database import get_db

db = get_db()
cursor = db.cursor()

THN_SEMASA = 2026

print("=" * 60)
print("VERIFY FIX: KK Allocation per-PDM (no double-counting)")
print("=" * 60)

for dun in ['N12', 'N13', 'N14', 'N15']:
    cursor.execute("""
        SELECT
            p.dm,
            COUNT(p.id) AS jumlah,
            (SELECT COUNT(*) FROM (
                SELECT sub.kk_id FROM (
                    SELECT p2.ketua_keluarga_id AS kk_id,
                           p2.dm,
                           ROW_NUMBER() OVER (PARTITION BY p2.ketua_keluarga_id ORDER BY COUNT(*) DESC) AS rn
                    FROM pengundi p2
                    WHERE p2.ketua_keluarga_id IS NOT NULL
                      AND p2.status_fizikal = 'Hidup'
                      AND p2.status_rekod = 'Sah'
                      AND p2.dun_id = (SELECT id FROM dun WHERE kod = %s)
                    GROUP BY p2.ketua_keluarga_id, p2.dm
                ) sub
                WHERE sub.rn = 1 AND sub.dm = p.dm
            ) sq) AS jumlah_ketua_keluarga_fixed
        FROM pengundi p
        WHERE p.dun_id = (SELECT id FROM dun WHERE kod = %s)
          AND p.status_fizikal = 'Hidup'
          AND p.status_rekod = 'Sah'
          AND p.dm IS NOT NULL AND p.dm != ''
        GROUP BY p.dm
        ORDER BY p.dm
    """, (dun, dun))
    
    rows = cursor.fetchall()
    total_kk_new = sum(r[2] for r in rows)
    
    cursor.execute("""
        SELECT COUNT(DISTINCT ketua_keluarga_id)
        FROM pengundi
        WHERE dun_id = (SELECT id FROM dun WHERE kod = %s)
          AND status_fizikal = 'Hidup' AND status_rekod = 'Sah'
          AND ketua_keluarga_id IS NOT NULL
    """, (dun,))
    expected = cursor.fetchone()[0]
    
    status = "PASS" if total_kk_new == expected else "FAIL"
    print(f"\n{dun}:")
    for r in rows:
        print(f"  PDM={r[0]:20s} | Pengundi={r[1]:6d} | KK(fixed)={r[2]}")
    print(f"  SUM={total_kk_new} | Expected(DISTINCT)={expected} | [{status}]")

# Overall
cursor.execute("""
    SELECT COUNT(DISTINCT ketua_keluarga_id)
    FROM pengundi
    WHERE status_fizikal = 'Hidup' AND status_rekod = 'Sah'
      AND ketua_keluarga_id IS NOT NULL
""")
total = cursor.fetchone()[0]
print(f"\nTotal distinct KK (Parlimen): {total}")
db.close()
print("\nDone.")