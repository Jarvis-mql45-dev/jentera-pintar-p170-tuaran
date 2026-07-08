import sys, os
sys.path.insert(0, 'backend')
from database import get_db

db = get_db()
c = db.cursor()
c.execute("SELECT COUNT(*) FROM pengundi")
total = c.fetchone()[0]
print(f"Jumlah pengundi dalam database: {total}")

c.execute("SELECT COUNT(*) FROM pengundi WHERE sumber_pdm = 'Migrasi P170'")
migrated = c.fetchone()[0]
print(f"Rekod dari Migrasi P170: {migrated}")

c.execute("SELECT d.kod, d.nama, COUNT(*) FROM pengundi p LEFT JOIN dun d ON p.dun_id=d.id GROUP BY d.kod, d.nama ORDER BY d.kod")
for row in c.fetchall():
    print(f"  DUN {row[0]} ({row[1]}): {row[2]} pengundi")

c.execute("SELECT COUNT(DISTINCT dm) FROM pengundi WHERE dm IS NOT NULL")
print(f"Jumlah PDM unik: {c.fetchone()[0]}")

c.execute("SELECT COUNT(DISTINCT lokaliti) FROM pengundi WHERE lokaliti IS NOT NULL")
print(f"Jumlah Kampung/Lokaliti unik: {c.fetchone()[0]}")

db.close()