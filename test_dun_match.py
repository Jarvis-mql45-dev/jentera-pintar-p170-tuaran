import os, sys
sys.path.insert(0, '.')
from backend.database import get_db
db = get_db()
cursor = db.cursor()

# Check actual DUN names
cursor.execute('SELECT kod, nama FROM dun ORDER BY kod')
print('DUN TABLE:')
for r in cursor.fetchall():
    print(f'  {r[0]}: {r[1]}')

# Check kk.dun values
cursor.execute('SELECT DISTINCT dun FROM ketua_keluarga WHERE dun IS NOT NULL ORDER BY dun')
print('\nkk.dun VALUES:')
for r in cursor.fetchall():
    print(f'  "{r[0]}"')

# Test POSITION match
print('\nTEST POSITION MATCH (for Nama):')
cursor.execute("""
    SELECT kk.dun, d.kod, d.nama,
           POSITION(UPPER(kk.dun) IN UPPER(d.nama))
    FROM ketua_keluarga kk
    LEFT JOIN dun d ON POSITION(UPPER(kk.dun) IN UPPER(d.nama)) > 0
    WHERE kk.is_active = 1 AND kk.dun IS NOT NULL
    ORDER BY kk.id
    LIMIT 30
""")
rows = cursor.fetchall()
print(f'  Rows: {len(rows)}')
for r in rows:
    print(f'  kk.dun="{str(r[0]):10s}" -> d.kod={str(r[1]):4s}, d.nama="{str(r[2]):20s}" pos={r[3]}')

# Count matched
cursor.execute("""
    SELECT COUNT(*)
    FROM ketua_keluarga kk
    LEFT JOIN dun d ON POSITION(UPPER(kk.dun) IN UPPER(d.nama)) > 0
    WHERE kk.is_active = 1 AND kk.dun IS NOT NULL
      AND d.kod IS NOT NULL
""")
matched = cursor.fetchone()[0]
cursor.execute("""
    SELECT COUNT(*)
    FROM ketua_keluarga kk
    WHERE kk.is_active = 1 AND kk.dun IS NOT NULL
""")
total_dun = cursor.fetchone()[0]
print(f'\nDUN matched: {matched}/{total_dun}')

db.close()