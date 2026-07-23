"""
Fix kk.dun values from text names to DUN codes, and add frontend fallback.
"""
import os, sys
sys.path.insert(0, '.')
from backend.database import get_db

# Map stored DUN text names → DUN codes
DUN_NAME_TO_CODE = {
    "SULAMAN": "N12",
    "P DALIT": "N13",
    "TAMPARULI": "N14",
    "KIULU": "N15"
}

# Also try partial matches for names stored differently
DUN_NAME_FUZZY = {
    "DALIT": "N13",  # for "P DALIT"
    "SULAMAN": "N12",
    "TAMPARULI": "N14",
    "KIULU": "N15"
}

db = get_db()
cursor = db.cursor()

# Show all current DUN values
cursor.execute("SELECT DISTINCT dun FROM ketua_keluarga WHERE dun IS NOT NULL ORDER BY dun")
print("Current distinct DUN values in ketua_keluarga:")
for r in cursor.fetchall():
    print(f"  '{r[0]}'")

# Fix each record
cursor.execute("""
    SELECT id, nama_penuh, dm, dun FROM ketua_keluarga WHERE is_active = 1 ORDER BY id
""")
records = cursor.fetchall()

updated = 0
for r in records:
    old_dun = r[3]
    if not old_dun:
        continue
    
    old_upper = old_dun.upper().strip()
    
    # Direct mapping
    new_code = DUN_NAME_TO_CODE.get(old_upper)
    
    # Fuzzy match
    if not new_code:
        for key, val in DUN_NAME_FUZZY.items():
            if key in old_upper:
                new_code = val
                break
    
    if new_code and new_code != old_upper:
        cursor.execute("UPDATE ketua_keluarga SET dun = ? WHERE id = ?", (new_code, r[0]))
        print(f"  ID={r[0]:3d} | {r[1]:35s} | '{old_dun}' → '{new_code}'")
        updated += 1

if updated:
    db.commit()
    print(f"\n✅ Updated {updated} records")
else:
    print("\nNo updates needed - all DUN values already correct")

# Verify
cursor.execute("SELECT DISTINCT dun FROM ketua_keluarga WHERE dun IS NOT NULL ORDER BY dun")
print("\nDistinct DUN values after fix:")
for r in cursor.fetchall():
    print(f"  '{r[0]}'")

db.close()