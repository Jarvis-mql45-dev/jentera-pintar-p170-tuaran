"""
Audit: Compare counts between:
1. Master Excel (DASHBOARD PARLIMEN TUARAN 2026.xlsx)
2. Individual DUN Excel files
3. Supabase database
"""
import os
import sys
import pandas as pd

# ===== 1. MASTER EXCEL =====
master_path = os.path.join(os.path.dirname(__file__), 'DASHBOARD PARLIMEN TUARAN 2026.xlsx')
master_total = 0
master_by_dun = {}
try:
    xls = pd.ExcelFile(master_path)
    print(f"📊 Master Excel sheets: {xls.sheet_names}")
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet)
        # Try to count voters - look for NO KP or NAMA columns
        if 'NO KP' in df.columns:
            count = df['NO KP'].notna().sum()
            master_total += count
            master_by_dun[sheet] = count
        elif 'NO KP' in [c.strip().upper() for c in df.columns]:
            # Normalise columns
            df_norm = df.rename(columns={c: c.strip().upper() for c in df.columns})
            count = df_norm['NO KP'].notna().sum()
            master_total += count
            master_by_dun[sheet] = count
        else:
            print(f"   Sheet '{sheet}': {len(df)} rows, columns: {list(df.columns[:10])}")
            master_by_dun[sheet] = len(df)
    print(f"\n📊 MASTER EXCEL TOTAL: {master_total}")
    for k, v in master_by_dun.items():
        print(f"   {k}: {v}")
except Exception as e:
    print(f"⚠️ Master Excel error: {e}")

# ===== 2. INDIVIDUAL DUN EXCELS =====
dun_folders = [
    ("N12", "DUN N12 SULAMAN", "SENARAI PENGUNDI SULAMAN.xlsx"),
    ("N13", "DUN N13 PANTAI DALIT", "SENARAI PENGUNDI PANTAI DALIT.xlsx"),
    ("N14", "DUN N14 TAMPARULI", "SENARAI PENGUNDI TAMPARULI.xlsx"),
    ("N15", "DUN N15 KIULU", "SENARAI PENGUNDI KIULU.xlsx"),
]
individual_total = 0
print(f"\n📊 INDIVIDUAL DUN EXCELS:")
for kod, folder, filename in dun_folders:
    path = os.path.join(os.path.dirname(__file__), folder, filename)
    if os.path.exists(path):
        df = pd.read_excel(path)
        # Normalise columns
        df.columns = [str(c).strip().upper() for c in df.columns]
        count = len(df)
        individual_total += count
        print(f"   {kod} {folder}: {count} rows")
    else:
        print(f"   {kod} {folder}: FILE NOT FOUND")

print(f"\n📊 INDIVIDUAL EXCEL TOTAL: {individual_total}")

# ===== 3. SUPABASE DATABASE =====
# Load .env
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                os.environ[key.strip()] = val.strip()

DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    import psycopg2
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    print(f"\n📊 SUPABASE DATABASE:")
    
    # Raw counts
    cur.execute("SELECT COUNT(*) FROM pengundi")
    raw_total = cur.fetchone()[0]
    print(f"   Raw total records: {raw_total}")
    
    # By status_fizikal
    cur.execute("SELECT status_fizikal, COUNT(*) FROM pengundi GROUP BY status_fizikal ORDER BY COUNT(*) DESC")
    print(f"   By status_fizikal:")
    for r in cur.fetchall():
        print(f"      {r[0] or 'NULL'}: {r[1]}")
    
    # By status_rekod
    cur.execute("SELECT status_rekod, COUNT(*) FROM pengundi GROUP BY status_rekod ORDER BY COUNT(*) DESC")
    print(f"   By status_rekod:")
    for r in cur.fetchall():
        print(f"      {r[0] or 'NULL'}: {r[1]}")
    
    # Dashboard-filtered count (Hidup + Sah)
    cur.execute("SELECT COUNT(*) FROM pengundi WHERE status_fizikal = 'Hidup' AND status_rekod = 'Sah'")
    dashboard_count = cur.fetchone()[0]
    print(f"   Dashboard filter (Hidup+Sah): {dashboard_count}")
    
    # By DUN
    cur.execute("SELECT d.kod, d.nama, COUNT(p.id) as jumlah FROM pengundi p JOIN dun d ON p.dun_id = d.id GROUP BY d.kod, d.nama ORDER BY d.kod")
    print(f"   By DUN:")
    for r in cur.fetchall():
        print(f"      {r[0]} {r[1]}: {r[2]}")
    
    # Check for duplicates by no_kp
    cur.execute("SELECT no_kp, COUNT(*) as dup_count FROM pengundi GROUP BY no_kp HAVING COUNT(*) > 1 ORDER BY dup_count DESC LIMIT 20")
    dup_rows = cur.fetchall()
    if dup_rows:
        total_dups = sum(r[1] for r in dup_rows)
        print(f"\n   ⚠️ DUPLICATE no_kp FOUND: {len(dup_rows)} no_kp have duplicates")
        print(f"      Total duplicate rows: {total_dups}")
        for r in dup_rows[:5]:
            print(f"      {r[0]}: {r[1]}x")
    else:
        print(f"\n   ✅ No duplicate no_kp found")
    
    # Total unique no_kp
    cur.execute("SELECT COUNT(DISTINCT no_kp) FROM pengundi")
    unique_kp = cur.fetchone()[0]
    print(f"   Unique no_kp: {unique_kp}")
    
    # Check records with status_fizikal != 'Hidup' 
    cur.execute("SELECT COUNT(*) FROM pengundi WHERE status_fizikal IS NULL OR status_fizikal = ''")
    null_fizikal = cur.fetchone()[0]
    print(f"   NULL/empty status_fizikal: {null_fizikal}")
    
    cur.execute("SELECT COUNT(*) FROM pengundi WHERE status_fizikal != 'Hidup' AND status_fizikal IS NOT NULL AND status_fizikal != ''")
    non_hidup = cur.fetchone()[0]
    print(f"   Non-Hidup status_fizikal: {non_hidup}")
    
    # Check records with status_rekod != 'Sah'
    cur.execute("SELECT COUNT(*) FROM pengundi WHERE status_rekod IS NULL OR status_rekod = ''")
    null_rekod = cur.fetchone()[0]
    print(f"   NULL/empty status_rekod: {null_rekod}")
    
    cur.execute("SELECT COUNT(*) FROM pengundi WHERE status_rekod != 'Sah' AND status_rekod IS NOT NULL AND status_rekod != ''")
    non_sah = cur.fetchone()[0]
    print(f"   Non-Sah status_rekod: {non_sah}")
    
    # By sumber_pdm
    cur.execute("SELECT sumber_pdm, COUNT(*) FROM pengundi GROUP BY sumber_pdm ORDER BY COUNT(*) DESC")
    print(f"   By sumber_pdm:")
    for r in cur.fetchall():
        print(f"      {r[0] or 'NULL'}: {r[1]}")
    
    cur.close()
    conn.close()
else:
    print("\n⚠️ DATABASE_URL not available")

print(f"\n{'='*60}")
print(f"SUMMARY COMPARISON:")
print(f"  Master Excel:         {master_total}")
print(f"  Individual Excels:    {individual_total}")
print(f"  DB Raw Total:         {raw_total if DATABASE_URL else 'N/A'}")
print(f"  Dashboard Filter:     {dashboard_count if DATABASE_URL else 'N/A'}")
print(f"  Unique no_kp:         {unique_kp if DATABASE_URL else 'N/A'}")