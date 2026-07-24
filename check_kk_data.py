"""
Check KK data sources - both ketua_keluarga master table and pengundi self-reference
"""
import os, sys
sys.path.insert(0, '.')
from backend.database import get_db

db = get_db()
cursor = db.cursor()

# ===== 1. ketua_keluarga MASTER TABLE =====
print("=" * 70)
print("1. KETUA_KELUARGA MASTER TABLE")
print("=" * 70)

# Columns
cursor.execute("""
    SELECT column_name, data_type, is_nullable, column_default 
    FROM information_schema.columns 
    WHERE table_name = 'ketua_keluarga'
    ORDER BY ordinal_position
""")
cols = cursor.fetchall()
print("COLUMNS:")
for c in cols:
    print(f"  {c[0]:25s} {c[1]:20s} nullable={c[2]} default={c[3]}")

# Count
cursor.execute("SELECT COUNT(*) FROM ketua_keluarga")
total_kk = cursor.fetchone()[0]
print(f"\nTotal KK records: {total_kk}")

# By is_active
cursor.execute("SELECT is_active, COUNT(*) FROM ketua_keluarga GROUP BY is_active ORDER BY is_active")
print("\nKK by is_active:")
for r in cursor.fetchall():
    print(f"  is_active={r[0]}: {r[1]}")

# Sample
cursor.execute("""
    SELECT id, nama_penuh, COALESCE(no_kp,'-'), COALESCE(dm,'-'), COALESCE(dun,'-'), is_active 
    FROM ketua_keluarga ORDER BY id LIMIT 50
""")
print("\nSAMPLE KKs (first 50):")
print(f"{'ID':>5} | {'NAMA':30s} | {'KP':15s} | {'DM':15s} | {'DUN':6s} | aktif")
print("-" * 80)
for r in cursor.fetchall():
    print(f"{r[0]:5d} | {r[1]:30s} | {r[2]:15s} | {r[3]:15s} | {str(r[4]):6s} | {r[5]}")

# ===== 2. PENGUNDI TABLE - KK REFERENCES =====
print("\n" + "=" * 70)
print("2. PENGUNDI TABLE - KK REFERENCES")
print("=" * 70)

# Total pengundi with ketua_keluarga_id
cursor.execute("SELECT COUNT(*) FROM pengundi WHERE ketua_keluarga_id IS NOT NULL")
p_with_kk = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM pengundi")
total_p = cursor.fetchone()[0]
print(f"Pengundi with KK assigned: {p_with_kk} / {total_p}")
if total_p > 0:
    print(f"  Percentage: {round(p_with_kk/total_p*100, 1)}%")

# Distinct ketua_keluarga_id values
cursor.execute("""
    SELECT COUNT(DISTINCT ketua_keluarga_id) 
    FROM pengundi WHERE ketua_keluarga_id IS NOT NULL
""")
distinct_kk_refs = cursor.fetchone()[0]
print(f"Distinct ketua_keluarga_id references: {distinct_kk_refs}")

# Valid references
cursor.execute("""
    SELECT COUNT(*) FROM pengundi p 
    WHERE p.ketua_keluarga_id IS NOT NULL 
    AND EXISTS (SELECT 1 FROM ketua_keluarga kk WHERE kk.id = p.ketua_keluarga_id)
""")
valid = cursor.fetchone()[0]
print(f"Valid references (KK exists in ketua_keluarga table): {valid}")

# Orphaned
cursor.execute("""
    SELECT COUNT(*) FROM pengundi p 
    WHERE p.ketua_keluarga_id IS NOT NULL 
    AND NOT EXISTS (SELECT 1 FROM ketua_keluarga kk WHERE kk.id = p.ketua_keluarga_id)
""")
orphaned = cursor.fetchone()[0]
print(f"Orphaned references (KK does NOT exist): {orphaned}")

# ===== 3. PENGUNDI SELF-REFERENCE AS KK (old method) =====
print("\n" + "=" * 70)
print("3. PENGUNDI SELF-REFERENCE AS KK (old method - pengundi referencing other pengundi)")
print("=" * 70)

cursor.execute("""
    SELECT COUNT(*) FROM pengundi 
    WHERE id IN (SELECT DISTINCT ketua_keluarga_id FROM pengundi WHERE ketua_keluarga_id IS NOT NULL)
""")
old_kk_count = cursor.fetchone()[0]
print(f"Pengundi records that ARE themselves KK (referenced by other pengundi): {old_kk_count}")

# Sample of pengundi acting as KK
cursor.execute("""
    SELECT p.id, p.nama_penuh, p.no_kp, p.dm
    FROM pengundi p
    WHERE p.id IN (SELECT DISTINCT ketua_keluarga_id FROM pengundi WHERE ketua_keluarga_id IS NOT NULL)
    ORDER BY p.id LIMIT 20
""")
print("\nSample of pengundi that are KKs (self-reference):")
for r in cursor.fetchall():
    print(f"  ID={r[0]:5d} | {r[1]:35s} | KP={str(r[2]):15s} | DM={str(r[3]):15s}")

# Overlap: Are those self-referenced KKs also in ketua_keluarga table?
cursor.execute("""
    SELECT COUNT(*) FROM pengundi p
    WHERE p.id IN (SELECT DISTINCT ketua_keluarga_id FROM pengundi WHERE ketua_keluarga_id IS NOT NULL)
    AND EXISTS (SELECT 1 FROM ketua_keluarga kk WHERE kk.id = p.id)
""")
overlap = cursor.fetchone()[0]
print(f"\nOverlap (pengundi-as-KK also exists in ketua_keluarga table): {overlap}")
print(f"NOT in ketua_keluarga table: {old_kk_count - overlap}")

# ===== 3b. DUN breakdown in ketua_keluarga =====
print("\n" + "=" * 70)
print("3b. DUN BREAKDOWN IN ketua_keluarga TABLE")
print("=" * 70)
cursor.execute("SELECT DISTINCT dun FROM ketua_keluarga ORDER BY dun")
print("DISTINCT DUN values:")
for r in cursor.fetchall():
    print(f"  '{r[0]}'")

cursor.execute("SELECT dun, COUNT(*) FROM ketua_keluarga GROUP BY dun ORDER BY dun")
print("\nKK COUNT BY DUN:")
for r in cursor.fetchall():
    print(f"  {str(r[0]):20s}: {r[1]}")

# ===== 4. N12 SULAMAN SPECIFIC =====
print("\n" + "=" * 70)
print("4. N12 SULAMAN - SPECIFIC CHECK")
print("=" * 70)

# KK in N12 - also try by full name
cursor.execute("SELECT COUNT(*) FROM ketua_keluarga WHERE UPPER(dun) LIKE '%SULAMAN%'")
kk_sulaman = cursor.fetchone()[0]
print(f"KK with DUN containing 'SULAMAN': {kk_sulaman}")

# All pengundi columns
cursor.execute("""
    SELECT column_name FROM information_schema.columns 
    WHERE table_name = 'pengundi'
    ORDER BY ordinal_position
""")
all_cols = [r[0] for r in cursor.fetchall()]
print(f"\nALL pengundi columns ({len(all_cols)} total):")
for i, c in enumerate(all_cols):
    print(f"  {i:3d}. {c}")

# KK in N12 from ketua_keluarga table (using text field 'dun')
cursor.execute("""
    SELECT COUNT(*) FROM ketua_keluarga 
    WHERE dun = 'N12' OR dun LIKE 'N12%'
""")
kk_n12 = cursor.fetchone()[0]
print(f"KK in N12 Sulaman (ketua_keluarga table): {kk_n12}")

# Pengundi in N12 with KK assigned
cursor.execute("""
    SELECT COUNT(*) FROM pengundi p 
    JOIN dun d ON d.id = p.dun_id 
    WHERE d.kod = 'N12' AND p.ketua_keluarga_id IS NOT NULL
""")
p_n12_kk = cursor.fetchone()[0]
cursor.execute("""
    SELECT COUNT(*) FROM pengundi p 
    JOIN dun d ON d.id = p.dun_id 
    WHERE d.kod = 'N12'
""")
p_n12 = cursor.fetchone()[0]
print(f"Pengundi in N12 with KK: {p_n12_kk} / {p_n12}")
if p_n12 > 0:
    print(f"  Coverage: {round(p_n12_kk/p_n12*100, 1)}%")

# List KK names in N12
cursor.execute("""
    SELECT kk.id, kk.nama_penuh, kk.no_kp, kk.dm,
           (SELECT COUNT(*) FROM pengundi p WHERE p.ketua_keluarga_id = kk.id AND p.status_fizikal = 'Hidup') AS ahli
    FROM ketua_keluarga kk
    WHERE (kk.dun = 'N12' OR kk.dun LIKE 'N12%') AND kk.is_active = 1
    ORDER BY kk.nama_penuh
""")
kk_n12_list = cursor.fetchall()
print(f"\nKK in N12 Sulaman (nama & ahli keluarga):")
for r in kk_n12_list:
    print(f"  ID={r[0]:5d} | {r[1]:35s} | KP={str(r[2]):15s} | DM={str(r[3]):15s} | Ahli={r[4]}")

# Orphaned in N12 specifically
cursor.execute("""
    SELECT COUNT(*) FROM pengundi p 
    JOIN dun d ON d.id = p.dun_id 
    WHERE d.kod = 'N12' AND p.ketua_keluarga_id IS NOT NULL
    AND NOT EXISTS (SELECT 1 FROM ketua_keluarga kk WHERE kk.id = p.ketua_keluarga_id)
""")
orphaned_n12 = cursor.fetchone()[0]
print(f"Orphaned KK references in N12: {orphaned_n12}")

# ===== 4b. TEXT COLUMNS 'ketua_keluarga' and 'pegawai_penyelaras' in pengundi =====
print("\n" + "=" * 70)
print("4b. TEXT COLUMNS 'ketua_keluarga' and 'pegawai_penyelaras' IN pengundi TABLE")
print("=" * 70)

cursor.execute("SELECT COUNT(*) FROM pengundi WHERE ketua_keluarga IS NOT NULL AND ketua_keluarga != ''")
txt_kk_cnt = cursor.fetchone()[0]
print(f"Pengundi with text 'ketua_keluarga' filled: {txt_kk_cnt}")

cursor.execute("SELECT COUNT(*) FROM pengundi WHERE pegawai_penyelaras IS NOT NULL AND pegawai_penyelaras != ''")
txt_pp_cnt = cursor.fetchone()[0]
print(f"Pengundi with text 'pegawai_penyelaras' filled: {txt_pp_cnt}")

# Show the 1 N12 pengundi with KK
cursor.execute("""
    SELECT p.id, p.nama_penuh, p.no_kp, p.dm, p.ketua_keluarga_id, p.ketua_keluarga
    FROM pengundi p 
    JOIN dun d ON d.id = p.dun_id 
    WHERE d.kod = 'N12' AND p.ketua_keluarga_id IS NOT NULL
""")
print("\n=== The 1 N12 pengundi with KK assigned (full detail) ===")
for r in cursor.fetchall():
    print(f"  Pengundi ID={r[0]:5d} | {r[1]:35s} | KP={r[2]:15s} | DM={r[3]:15s}")
    print(f"  ketua_keluarga_id={r[4]:5d} | ketua_keluarga(text)='{r[5]}'")
    # Show the KK detail
    cursor.execute("SELECT id, nama_penuh, no_kp, dm, dun FROM ketua_keluarga WHERE id = %s", (r[4],))
    kk = cursor.fetchone()
    if kk:
        print(f"  -> Referenced KK: ID={kk[0]:5d} | {kk[1]:30s} | KP={kk[2]:15s} | DM={kk[3]:15s} | DUN={kk[4]}")

# Show the 1 SULAMAN KK detail
cursor.execute("SELECT id, nama_penuh, no_kp, dm, dun FROM ketua_keluarga WHERE UPPER(dun) LIKE '%SULAMAN%'")
print("\n=== The 1 SULAMAN KK detail ===")
for r in cursor.fetchall():
    print(f"  ID={r[0]:5d} | {r[1]:30s} | KP={r[2]:15s} | DM={r[3]:15s} | DUN={r[4]}")
    cursor.execute("SELECT COUNT(*) FROM pengundi WHERE ketua_keluarga_id = %s", (r[0],))
    cnt3 = cursor.fetchone()[0]
    print(f"  -> Pengundi under this KK: {cnt3}")

# ALL KK with pengundi count
cursor.execute("""
    SELECT kk.id, kk.nama_penuh, kk.dun,
           (SELECT COUNT(*) FROM pengundi WHERE ketua_keluarga_id = kk.id) AS ahli
    FROM ketua_keluarga kk
    ORDER BY kk.dun, kk.nama_penuh
""")
print("\n=== ALL KK with ahli count by DUN ===")
for r in cursor.fetchall():
    print(f"  DUN={str(r[2]):10s} | ID={r[0]:5d} | {r[1]:35s} | Ahli={r[3]}")

# ===== 5. SUMMARY =====
print("\n" + "=" * 70)
print("5. SUMMARY")
print("=" * 70)
# Active count
cursor.execute("SELECT COUNT(*) FROM ketua_keluarga WHERE is_active = 1")
active_kk = cursor.fetchone()[0]
print(f"  ketua_keluarga master table: {total_kk} total ({active_kk} active)")
print(f"  Pengundi with KK assigned: {p_with_kk} / {total_p}")
print(f"  Valid KK references: {valid}")
print(f"  Orphaned references: {orphaned}")
print(f"  Pengundi-as-KK (old method): {old_kk_count}")
print(f"  Overlap between old+new: {overlap}")
print(f"  N12 KK count: {kk_n12}")
print(f"  N12 pengundi with KK: {p_n12_kk} / {p_n12}")

db.close()