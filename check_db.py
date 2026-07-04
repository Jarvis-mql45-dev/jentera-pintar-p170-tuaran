"""Check local pengundi.db contents"""
import sqlite3

conn = sqlite3.connect("pengundi.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM pengundi")
count = cur.fetchone()[0]
print(f"Jumlah rekod dalam pengundi.db: {count}")

cur.execute("SELECT DISTINCT dm FROM pengundi WHERE dm IS NOT NULL ORDER BY dm")
dms = [r[0] for r in cur.fetchall()]
print(f"Pilihan DM: {dms}")

pdm = [d for d in dms if d.upper().startswith("PDM ")]
print(f"PDM dalam DB tempatan: {len(pdm)}")
if pdm:
    print(f"  Nilai PDM: {pdm}")

cur.execute("SELECT status_sokongan, COUNT(*) as jumlah FROM pengundi GROUP BY status_sokongan ORDER BY jumlah DESC")
for r in cur.fetchall():
    key = r["status_sokongan"] or "Tiada"
    print(f"  {key}: {r['jumlah']}")

conn.close()

print(f"\nKesimpulan: Database tempatan ada {count} rekod data sebenar (belum termasuk PDM)")