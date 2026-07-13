"""
Forensic analysis: N12 Sulaman - find the 112 extra records in Supabase vs Excel
"""
import os, sys, pandas as pd

# Load .env
env_path = '.env'
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                os.environ[key.strip()] = val.strip()

# ===== 1. Read N12 EXCEL =====
n12_excel_path = r'DUN N12 SULAMAN\SENARAI PENGUNDI SULAMAN.xlsx'
df_excel = pd.read_excel(n12_excel_path)
df_excel.columns = [str(c).strip().upper() for c in df_excel.columns]
print(f"Excel row count: {len(df_excel)}")

excel_no_kp = set()
for val in df_excel['NO KP']:
    if pd.notna(val):
        no_kp = str(val).strip().replace('-', '').replace(' ', '')
        digits = ''.join(c for c in no_kp if c.isdigit())
        if len(digits) >= 12:
            no_kp = digits[-12:]
        else:
            no_kp = digits
        if no_kp:
            excel_no_kp.add(no_kp)

print(f"Excel unique no_kp: {len(excel_no_kp)}")

# ===== 2. Query SUPABASE =====
import psycopg2
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("DATABASE_URL not found")
    sys.exit(1)

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

cur.execute("SELECT id FROM dun WHERE kod = 'N12'")
dun_n12_id = cur.fetchone()[0]
print(f"\nN12 DUN ID: {dun_n12_id}")

cur.execute("""
    SELECT id, no_kp, nama_penuh, sumber_pdm, dicipta_pada, dm, lokaliti
    FROM pengundi
    WHERE dun_id = %s
    ORDER BY no_kp
""", (dun_n12_id,))

db_rows = cur.fetchall()
print(f"Supabase N12 records: {len(db_rows)}")

db_no_kp = set()
db_by_kp = {}
for r in db_rows:
    db_no_kp.add(r[1])
    if r[1] not in db_by_kp:
        db_by_kp[r[1]] = []
    db_by_kp[r[1]].append(r)

print(f"Supabase unique no_kp: {len(db_no_kp)}")

# ===== 3. FIND DIFFERENCES =====
only_in_db = db_no_kp - excel_no_kp
only_in_excel = excel_no_kp - db_no_kp

print(f"\n{'='*60}")
print(f"RECORDS ONLY IN SUPABASE (extra): {len(only_in_db)}")
print(f"RECORDS ONLY IN EXCEL (missing from DB): {len(only_in_excel)}")

# ===== 4. ANALYZE EXTRA RECORDS =====
if only_in_db:
    print(f"\n{'='*60}")
    print("DETAILED ANALYSIS OF EXTRA SUPABASE RECORDS:")
    for nk in sorted(list(only_in_db))[:30]:  # first 30
        for r in db_by_kp.get(nk, []):
            print(f"  id={r[0]}, no_kp={r[1]}, nama={str(r[2])[:30]}, src={r[3]}, created={str(r[4])[:19]}, dm={r[5]}, lokaliti={r[6]}")
    
    if len(only_in_db) > 30:
        print(f"  ... and {len(only_in_db) - 30} more")
    
    # Source breakdown
    print(f"\nSource breakdown of extra records:")
    src_count = {}
    for nk in only_in_db:
        for r in db_by_kp.get(nk, []):
            src = r[3] or 'NULL'
            src_count[src] = src_count.get(src, 0) + 1
    for src, cnt in sorted(src_count.items(), key=lambda x: -x[1]):
        print(f"  {src}: {cnt}")

    print(f"\nDM breakdown of extra records:")
    dm_count = {}
    for nk in only_in_db:
        for r in db_by_kp.get(nk, []):
            dm = r[5] or 'NULL'
            dm_count[dm] = dm_count.get(dm, 0) + 1
    for dm, cnt in sorted(dm_count.items(), key=lambda x: -x[1])[:10]:
        print(f"  {dm}: {cnt}")

# ===== 5. CROSS-DUN CHECK =====
print(f"\n{'='*60}")
print("CROSS-DUN CHECK: Extra no_kp in OTHER DUNs?")
cross_count = 0
for nk in list(only_in_db)[:50]:
    cur.execute("""
        SELECT d.kod, p.nama_penuh, p.sumber_pdm
        FROM pengundi p
        JOIN dun d ON p.dun_id = d.id
        WHERE p.no_kp = %s AND p.dun_id != %s
        LIMIT 3
    """, (nk, dun_n12_id))
    others = cur.fetchall()
    for o in others:
        cross_count += 1
        if cross_count <= 10:
            print(f"  no_kp={nk}: also in {o[0]} as '{str(o[1])[:25]}' src={o[2]}")

if cross_count == 0:
    print(f"  None found across all extra records.")

cur.close()
conn.close()
print(f"\n{'='*60}")
print("ANALYSIS COMPLETE")