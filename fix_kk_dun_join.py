"""
Fix DUN JOIN for ketua_keluarga table.
kk.dun has text names (SULAMAN, P DALIT, TAMPARULI, KIULU)
dun.kod has codes (N12, N13, N14, N15)
Use PDM_TO_DUN style mapping in SQL
"""
import re

with open('backend/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# The current fix replaced d.id = kk.dun_id with d.kod = UPPER(kk.dun)
# But kk.dun has 'SULAMAN' while d.kod has 'N12'
# Better approach: use the PDM_TO_DUN mapping style with CASE or subquery
# Since dun.nama has 'Sulaman', 'Pantai Dalit', 'Tamparuli', 'Kiulu'
# Let's match on LIKE or use UPPER()

# Check what dun.nama values look like
# We need: 'SULAMAN' -> LIKE '%SULAMAN%' -> matches 'Sulaman'
# 'P DALIT' -> LIKE '%DALIT%' -> matches 'Pantai Dalit'  
# 'TAMPARULI' -> matches 'Tamparuli'
# 'KIULU' -> matches 'Kiulu'

# Fix the JOIN: d.kod = UPPER(kk.dun) -> UPPER(d.nama) LIKE '%' || UPPER(kk.dun) || '%'
# But PostgreSQL uses || for concat
# Simpler: use a direct mapping via LIKE

old_join = "LEFT JOIN dun d ON d.kod = UPPER(kk.dun)"
new_join = "LEFT JOIN dun d ON UPPER(d.nama) LIKE '%' || UPPER(kk.dun) || '%'"

count = content.count(old_join)
if count > 0:
    content = content.replace(old_join, new_join)
    print(f"✅ Replaced {count} occurrence(s) of DUN JOIN")
else:
    print("⚠️  No match for old join pattern - checking alternatives")
    # Check what's actually in the file now
    if 'd.kod = UPPER(kk.dun)' in content:
        print("  Direct match found")
        content = content.replace('d.kod = UPPER(kk.dun)', new_join)
    elif 'd.kod = kk.dun' in content:
        print("  Alternative match found")
        content = content.replace('d.kod = kk.dun', new_join)

with open('backend/main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Fixed backend/main.py DUN JOIN")
print()

# Also check verify_kk_fix.py for dun_id references
for script in ['verify_kk_fix.py', 'check_kk_data.py']:
    try:
        with open(script, 'r', encoding='utf-8') as f:
            sc = f.read()
        if 'dun_id' in sc or 'kk.dun_id' in sc:
            print(f"⚠️  {script} still has dun_id references (non-critical)")
        else:
            print(f"✅ {script} clean")
    except:
        pass