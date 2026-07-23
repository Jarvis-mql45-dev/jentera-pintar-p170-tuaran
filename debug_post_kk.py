"""Debug POST /api/ketua-keluarga issue"""
import os, sys
sys.path.insert(0, '.')
from backend.database import get_db

db = get_db()
cursor = db.cursor()

# 1. Show actual columns
cursor.execute("""
    SELECT column_name, data_type, is_nullable, column_default
    FROM information_schema.columns
    WHERE table_name = 'ketua_keluarga'
    ORDER BY ordinal_position
""")
print("=== ketua_keluarga COLUMNS ===")
for c in cursor.fetchall():
    print(f"  {c[0]:20s} {c[1]:20s} nullable={c[2]} default={c[3]}")

# 2. Simulate the INSERT from create_ketua_keluarga endpoint
# From backend/main.py the INSERT is:
# INSERT INTO ketua_keluarga (nama_penuh, no_kp, no_telefon, dm, dun_id, is_active, dicipta_pada, dikemaskini_pada)
# VALUES (?, ?, ?, ?, ?, 1, ?, ?)

# Check: is there a 'dun_id' column? NO - it's 'dun' (text)
# Check: are there 'dicipta_pada' and 'dikemaskini_pada' columns? YES from the column list above

# The INSERT references 'dun_id' but the column is named 'dun' !!!
print()
print("=== CHECKING INSERT STATEMENT ===")
print("The endpoint creates with 'dun_id' but table has 'dun' column")
print("This is the cause of the 500 error!")

# Also check the KetuaKeluargaCreate model in the code
print()
print("=== FIX ===")
print("Change INSERT: dun_id -> dun")
print("Change model references: dun_id -> dun")

db.close()