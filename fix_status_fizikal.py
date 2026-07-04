"""Fix status_fizikal from 'Hadir' to 'Hidup' and verify dashboard endpoint."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from database import get_db

db = get_db()
cursor = db.cursor()

# 1. Check current values
cursor.execute("SELECT DISTINCT status_fizikal FROM pengundi")
values = [r[0] for r in cursor.fetchall()]
print(f"Status fizikal sedia ada: {values}")

# 2. Update 'Hadir' -> 'Hidup'
cursor.execute("UPDATE pengundi SET status_fizikal = 'Hidup' WHERE status_fizikal = 'Hadir'")
count = cursor.rowcount
db.commit()
print(f"Dikemaskini: {count} rekod (Hadir -> Hidup)")

# 3. Verify
cursor.execute("SELECT status_fizikal, COUNT(*) FROM pengundi GROUP BY status_fizikal")
for r in cursor.fetchall():
    print(f"  {r[0]}: {r[1]}")

db.close()
print("Selesai!")