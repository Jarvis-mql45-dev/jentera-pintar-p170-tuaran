"""
Exact row-by-row comparison: N12 Excel rows vs Supabase records.
Count Excel rows, count DB records, find the EXACT difference.
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
df = pd.read_excel(n12_excel_path)
print("=" * 60)
print("N12 EXCEL ANALYSIS")
print(f"Total rows in sheet: {len(df)}")
print(f"Column names: {list(df.columns)}")

# Count by NO column (row number)
if 'NO' in df.columns:
    print(f"NO column unique count: {df['NO'].nunique()} (should match row count)")

# Count unique no_kp in Excel 
if 'NO KP' in df.columns:
    # How many unique raw values?
    raw_unique = df['NO KP'].nunique()
    print(f"NO KP raw unique values: {raw_unique}")
    
    # Normalise with leading zeros
    normalised = set()
    for val in df['NO KP']:
        if pd.notna(val):
            s = str(val).strip().replace('-', '').replace(' ', '')
            digits = ''.join(c for c in s if c.isdigit())
            if len(digits) >= 12:
                normalised.add(digits[-12:])
            else:
                normalised.add(digits)
    print(f"NO KP normalised unique: {len(normalised)}")

# ===== 2. Query SUPABASE =====
import psycopg2
DATABASE_URL = os.environ.get('DATABASE_URL')
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

cur.execute("SELECT id FROM dun WHERE kod = 'N12'")
dun_n12_id = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM pengundi WHERE dun_id = %s", (dun_n12_id,))
db_count = cur.fetchone()[0]
print(f"\nSupabase N12 total records: {db_count}")

cur.execute("SELECT COUNT(DISTINCT no_kp) FROM pengundi WHERE dun_id = %s", (dun_n12_id,))
db_unique = cur.fetchone()[0]
print(f"Supabase N12 unique no_kp: {db_unique}")

# Get all distinct no_kp from DB
cur.execute("SELECT DISTINCT no_kp FROM pengundi WHERE dun_id = %s ORDER BY no_kp", (dun_n12_id,))
db_noks = set(r[0] for r in cur.fetchall())

# ===== 3. Cross-check with Excel =====
print(f"\n{'='*60}")
print("CROSS-CHECK: Normalised match")

# Match each DB no_kp against Excel normalised values
matched = set()
unmatched_db = set()

# Try matching with leading zeros stripped (9-digit format)
excel_norm_9 = set()
for val in df['NO KP']:
    if pd.notna(val):
        s = str(val).strip().replace('-', '').replace(' ', '')
        digits = ''.join(c for c in s if c.isdigit())
        excel_norm_9.add(digits)  # keep the actual digits as stored

for db_nok in db_noks:
    # Strip leading zeros
    stripped = db_nok.lstrip('0') or '0'
    if stripped in excel_norm_9:
        matched.add(db_nok)
    else:
        unmatched_db.add(db_nok)

print(f"DB no_kp matched to Excel: {len(matched)}")
print(f"DB no_kp UNMATCHED (truly extra): {len(unmatched_db)}")

if unmatched_db:
    print(f"\nThese {len(unmatched_db)} no_kp exist in DB but NOT in ANY form in Excel:")
    for nk in sorted(unmatched_db):
        cur.execute("SELECT nama_penuh, sumber_pdm, dm, lokaliti, dicipta_pada FROM pengundi WHERE no_kp = %s AND dun_id = %s", (nk, dun_n12_id))
        r = cur.fetchone()
        if r:
            print(f"  no_kp={nk}, nama={str(r[0])[:30]}, src={r[1]}, dm={r[2]}, lokaliti={r[3]}")

# Also check: DB records where no_kp is NULL or empty
cur.execute("SELECT COUNT(*) FROM pengundi WHERE dun_id = %s AND (no_kp IS NULL OR no_kp = '')", (dun_n12_id,))
null_nok = cur.fetchone()[0]
print(f"\nDB records with NULL/empty no_kp: {null_nok}")

# Check any 0 or '0' no_kp
cur.execute("SELECT COUNT(*) FROM pengundi WHERE dun_id = %s AND no_kp IN ('0', '000000000000')", (dun_n12_id,))
zero_nok = cur.fetchone()[0]
print(f"DB records with no_kp='0' or '000000000000': {zero_nok}")

cur.close()
conn.close()
print(f"\n{'='*60}")
print("INVESTIGATION COMPLETE")