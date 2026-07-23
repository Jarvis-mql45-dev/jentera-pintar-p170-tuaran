"""
Fix all kk.dun_id -> kk.dun references in backend/main.py
The ketua_keluarga table has TEXT column 'dun' not FK 'dun_id'
"""
import re

with open('backend/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Count occurrences before fix
before = content.count('kk.dun_id')
print(f"Found {before} occurrences of 'kk.dun_id'")

# Fix: In ketua_keluarga queries, dun_id doesn't exist - use kk.dun instead
# The table columns are: id, nama_penuh, no_kp, jantina, tahun_lahir, dm, lokaliti, no_telefon, dun (TEXT), pengundi_id, ...
# So we need to JOIN ketua_keluarga with dun using kk.dun (text) -> d.kod

# Pattern 1: LEFT JOIN dun d ON d.id = kk.dun_id -> LEFT JOIN dun d ON d.kod = kk.dun
content = content.replace(
    "LEFT JOIN dun d ON d.id = kk.dun_id",
    "LEFT JOIN dun d ON d.kod = UPPER(kk.dun)"
)

# Pattern 2: WHERE kk.is_active = 1 AND kk.dun_id IS NOT NULL -> WHERE kk.is_active = 1 AND kk.dun IS NOT NULL AND kk.dun != ''
content = content.replace(
    "kk.dun_id IS NOT NULL",
    "kk.dun IS NOT NULL AND kk.dun != ''"
)

# Pattern 3: JOIN dun d WHERE d.id = kk.dun_id (in subquery) -> already handled by pattern 1
# Pattern 4: Any remaining d.id = kk.dun_id in ketua_keluarga context
content = content.replace(
    "d.id = kk.dun_id",
    "d.kod = UPPER(kk.dun)"
)

# Count after
after = content.count('kk.dun_id')
print(f"After fix: {after} occurrences remaining (should be 0)")

with open('backend/main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Fixed backend/main.py")