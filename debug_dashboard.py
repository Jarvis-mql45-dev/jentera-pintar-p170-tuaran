"""
Debug script: test the consolidated dashboard endpoint JSON structure.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from backend.database import get_db

db = get_db()
cursor = db.cursor()

THN_SEMASA = 2026
where = "WHERE status_fizikal = 'Hidup' AND status_rekod = 'Sah'"
params = []

cursor.execute(f"""
    SELECT
        d.kod AS dun_kod,
        p.dm,
        COUNT(p.id) AS jumlah,
        SUM(CASE WHEN p.status_sokongan = 'Putih' THEN 1 ELSE 0 END) AS putih,
        SUM(CASE WHEN p.status_sokongan = 'Atas Pagar' THEN 1 ELSE 0 END) AS atas_pagar,
        SUM(CASE WHEN p.status_sokongan = 'Hitam' THEN 1 ELSE 0 END) AS hitam,
        SUM(CASE WHEN p.status_sokongan IS NULL OR p.status_sokongan NOT IN ('Putih', 'Atas Pagar', 'Hitam') THEN 1 ELSE 0 END) AS tidak_dikenali,
        SUM(CASE WHEN p.status_fizikal = 'Meninggal Dunia' THEN 1 ELSE 0 END) AS meninggal,
        SUM(CASE WHEN p.tahun_lahir IS NOT NULL AND (? - p.tahun_lahir) BETWEEN 18 AND 30 THEN 1 ELSE 0 END) AS usia_18_30,
        SUM(CASE WHEN p.tahun_lahir IS NOT NULL AND (? - p.tahun_lahir) BETWEEN 31 AND 59 THEN 1 ELSE 0 END) AS usia_31_59,
        SUM(CASE WHEN p.tahun_lahir IS NOT NULL AND (? - p.tahun_lahir) >= 60 THEN 1 ELSE 0 END) AS usia_60plus
    FROM pengundi p
    JOIN dun d ON d.id = p.dun_id
    {where}
      AND p.dm IS NOT NULL AND p.dm != ''
    GROUP BY d.kod, p.dm
    ORDER BY d.kod, p.dm
""", params + [THN_SEMASA, THN_SEMASA, THN_SEMASA])

dun_pdm_raw = {}
for row in cursor.fetchall():
    dk = row["dun_kod"]
    if dk not in dun_pdm_raw:
        dun_pdm_raw[dk] = []
    dun_pdm_raw[dk].append({
        "dm": row["dm"],
        "jumlah": row["jumlah"],
        "putih": row["putih"],
    })

print("=== DUN KEYS FOUND ===")
print(list(dun_pdm_raw.keys()))
print()
for k in ['N12', 'N13', 'N14', 'N15']:
    data = dun_pdm_raw.get(k, [])
    print(f"{k}: {len(data)} PDM records")
    if data:
        print(f"  First 3 DMs: {[d['dm'] for d in data[:3]]}")
    else:
        print(f"  ⚠️ EMPTY - will trigger fallback message!")

print()
print("=== FRONTEND SIMULATION ===")
DUN_PDM_CODES = ['N12', 'N13', 'N14', 'N15']
for kod in DUN_PDM_CODES:
    pdmData = dun_pdm_raw.get(kod, [])
    print(f"dunPdmData['{kod}'] -> {len(pdmData)} records")
    if len(pdmData) == 0:
        print(f"  ❌ PROBLEM: renderPdmTable will show fallback for {kod}")
    else:
        print(f"  ✅ OK")

db.close()