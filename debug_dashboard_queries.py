"""Debug setiap query dalam endpoint dashboard untuk kenal pasti yang mana fail."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from database import get_db

db = get_db()
cursor = db.cursor()

THN_SEMASA = 2026
where = "WHERE status_fizikal = 'Hidup' AND status_rekod = 'Sah'"
params = []

queries = [
    ("COUNT", f"SELECT COUNT(*) FROM pengundi {where}"),
    ("SOKONGAN", f"SELECT status_sokongan, COUNT(*) as jumlah FROM pengundi {where} GROUP BY status_sokongan ORDER BY jumlah DESC"),
    ("JANTINA", f"SELECT jantina, COUNT(*) as jumlah FROM pengundi {where} GROUP BY jantina"),
    ("FIZIKAL", f"SELECT status_fizikal, COUNT(*) as jumlah FROM pengundi {where} GROUP BY status_fizikal"),
    ("LOKALITI", f"SELECT lokaliti, COUNT(*) as jumlah FROM pengundi {where} GROUP BY lokaliti ORDER BY jumlah DESC LIMIT 10"),
    ("UMUR", f"SELECT CASE WHEN (tahun_lahir IS NULL) THEN 'Tidak Diketahui' WHEN ({THN_SEMASA} - tahun_lahir) BETWEEN 18 AND 30 THEN 'Belia' WHEN ({THN_SEMASA} - tahun_lahir) BETWEEN 31 AND 59 THEN 'Dewasa' WHEN ({THN_SEMASA} - tahun_lahir) >= 60 THEN 'Warga Emas' ELSE 'Lain-lain' END as klasifikasi, COUNT(*) as jumlah, SUM(CASE WHEN jantina = 'L' THEN 1 ELSE 0 END) as lelaki, SUM(CASE WHEN jantina = 'P' THEN 1 ELSE 0 END) as perempuan FROM pengundi {where} GROUP BY klasifikasi"),
    ("PURATA", f"SELECT AVG({THN_SEMASA} - tahun_lahir) as purata_umur FROM pengundi {where} AND tahun_lahir IS NOT NULL"),
    ("SOKONGAN_UMUR", f"SELECT CASE WHEN (tahun_lahir IS NULL) THEN 'Tidak Diketahui' WHEN ({THN_SEMASA} - tahun_lahir) BETWEEN 18 AND 30 THEN 'Belia' WHEN ({THN_SEMASA} - tahun_lahir) BETWEEN 31 AND 59 THEN 'Dewasa' WHEN ({THN_SEMASA} - tahun_lahir) >= 60 THEN 'Warga Emas' ELSE 'Lain-lain' END as klasifikasi, COALESCE(status_sokongan, 'Tiada') as sokongan, COUNT(*) as jumlah FROM pengundi {where} GROUP BY klasifikasi, sokongan ORDER BY klasifikasi, sokongan"),
]

for name, sql in queries:
    try:
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        print(f'✅ {name}: {len(rows)} rows')
        if rows:
            print(f'   First row keys: {list(rows[0].keys()) if hasattr(rows[0], \"keys\") else type(rows[0])}')
            print(f'   First row values: {dict(rows[0]) if hasattr(rows[0], \"keys\") else rows[0]}')
    except Exception as e:
        print(f'❌ {name}: {e}')

db.close()
print('\nSelesai!')