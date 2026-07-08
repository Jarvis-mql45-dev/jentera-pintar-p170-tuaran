"""
Bulk migrate P170 data to Supabase using multi-row INSERT for speed.
Process: dedup N13 -> bulk insert N14 (26,648) -> bulk insert N15 (17,166)
Guna: python bulk_migrate.py
"""
import sys, os
sys.path.insert(0, 'backend')
import pandas as pd
from datetime import datetime
from database import get_db

CHUNK_SIZE = 10000  # 10k rows per INSERT statement

def checked(val):
    if pd.isna(val): return False
    return str(val).strip().upper() in ('1','1.0','Y','YES','TRUE')

def normalise_kp(raw):
    if pd.isna(raw): return None
    s = str(raw).strip().replace('-','').replace(' ','')
    d = ''.join(c for c in s if c.isdigit())
    return d[-12:] if len(d) >= 12 else (d or None)

def process_dun(db, c, folder, filename, dun_kod, dun_nama, pid):
    path = os.path.join(folder, filename)
    if not os.path.exists(path):
        print(f"⚠️  {path} not found")
        return
    
    print(f"\n{'='*60}")
    print(f"📂 {dun_kod} {dun_nama}")
    
    # Get/create dun_id
    c.execute("SELECT id FROM dun WHERE kod = ?", (dun_kod,))
    r = c.fetchone()
    if r:
        dun_id = r[0]
    else:
        now = datetime.now().isoformat()
        c.execute("INSERT INTO dun (parlimen_id,kod,nama,keterangan,dicipta_pada) VALUES (?,?,?,?,?)",
            (pid, dun_kod, dun_nama, f"DUN {dun_kod} {dun_nama}", now))
        db.commit()
        dun_id = c.lastrowid
    
    # Read Excel
    df = pd.read_excel(path)
    df.columns = [str(x).strip().upper() for x in df.columns]
    total = len(df)
    print(f"  Fail: {total} pengundi")
    
    # Pre-load PDM & kampung
    c.execute("SELECT id, nama FROM pdm WHERE dun_id = ?", (dun_id,))
    pdm_cache = {r2[1]: r2[0] for r2 in c.fetchall()}
    c.execute("SELECT id, nama FROM kampung WHERE pdm_id IN (SELECT id FROM pdm WHERE dun_id = ?)", (dun_id,))
    kg_cache = {r2[1]: r2[0] for r2 in c.fetchall()}
    
    now = datetime.now().isoformat()
    
    # Prepare data
    rows = []
    skipped = 0
    pdm_new = 0
    kg_new = 0
    
    for _, row in df.iterrows():
        try:
            no_kp = normalise_kp(row.get('NO KP'))
            nama = str(row.get('NAMA PENUH','')).strip().upper() if not pd.isna(row.get('NAMA PENUH')) else None
            if not no_kp or not nama:
                skipped += 1
                continue
            
            j = str(row.get('JANTINA','')).strip().upper()
            jantina = 'L' if j in ('L','LELAKI') else ('P' if j in ('P','PEREMPUAN') else None)
            
            thn = row.get('TAHUN LAHIR')
            tahun_lahir = int(float(str(thn))) if not pd.isna(thn) else None
            
            pdm_raw = row.get('DAERAH MENGUNDI')
            pdm_key = str(pdm_raw).strip().upper() if not pd.isna(pdm_raw) else None
            pdm_id = None
            if pdm_key:
                pdm_id = pdm_cache.get(pdm_key)
                if pdm_id is None:
                    c.execute("INSERT INTO pdm (dun_id,nama,keterangan,dicipta_pada) VALUES (?,?,?,?)",
                        (dun_id, pdm_key, f"{pdm_key} - {dun_nama}", now))
                    db.commit()
                    pdm_id = c.lastrowid
                    pdm_cache[pdm_key] = pdm_id
                    pdm_new += 1
            
            kg_raw = row.get('LOKALITI')
            kg_key = str(kg_raw).strip().upper() if not pd.isna(kg_raw) else None
            kg_id = None
            if kg_key:
                kg_id = kg_cache.get(kg_key)
                if kg_id is None:
                    c.execute("INSERT INTO kampung (pdm_id,nama,keterangan,dicipta_pada) VALUES (?,?,?,?)",
                        (pdm_id or dun_id, kg_key, f"{kg_key} - {pdm_key or dun_nama}", now))
                    db.commit()
                    kg_id = c.lastrowid
                    kg_cache[kg_key] = kg_id
                    kg_new += 1
            
            p = checked(row.get('PUTIH'))
            h = checked(row.get('HITAM'))
            a = checked(row.get('ATAS PAGAR'))
            t = checked(row.get('TAK KENAL'))
            sokongan = "Putih" if p else ("Hitam" if h else ("Atas Pagar" if a else ("Tidak Kenal" if t else "Belum Dikenal Pasti")))
            fizikal = "Meninggal Dunia" if checked(row.get('MENINGGAL DUNIA')) else "Hidup"
            
            tel = row.get('NO TELEFON')
            no_telefon = str(tel).strip() if not pd.isna(tel) else None
            
            rows.append((no_kp, nama, jantina, tahun_lahir,
                pid, dun_id, pdm_id, kg_id,
                pdm_key, kg_key, no_telefon,
                sokongan, fizikal, 0, 'Sah', 'Migrasi P170', now))
            
        except:
            skipped += 1
    
    print(f"  Disiapkan: {len(rows)} rows, {skipped} skipped, {pdm_new} PDM baru, {kg_new} kampung baru")
    
    # Bulk insert using multi-row SQL
    INSERT_TEMPLATE = """INSERT INTO pengundi 
        (no_kp, nama_penuh, jantina, tahun_lahir,
         parlimen_id, dun_id, pdm_id, kampung_id,
         dm, lokaliti, no_telefon,
         status_sokongan, status_fizikal,
         adalah_pemilik_apps, status_rekod, sumber_pdm, dicipta_pada)
        VALUES """
    
    inserted = 0
    for i in range(0, len(rows), CHUNK_SIZE):
        chunk = rows[i:i+CHUNK_SIZE]
        
        # Build multi-row VALUES
        value_rows = []
        for val in chunk:
            def esc(v):
                if v is None: return 'NULL'
                if isinstance(v, int): return str(v)
                return "'" + str(v).replace("'", "''") + "'"
            value_rows.append("(" + ",".join(esc(v) for v in val) + ")")
        
        sql = INSERT_TEMPLATE + ",\n".join(value_rows)
        
        try:
            c.execute(sql)
            db.commit()
            inserted += len(chunk)
            print(f"  ✅ Bulk +{len(chunk)} ({inserted}/{total})")
        except Exception as e:
            print(f"  ⚠️  Bulk error: {e}")
            # Fall back to row by row for this chunk
            db.rollback()
            single_sql = INSERT_TEMPLATE
            for val in chunk:
                try:
                    def esc2(v):
                        if v is None: return 'NULL'
                        if isinstance(v, int): return str(v)
                        return "'" + str(v).replace("'", "''") + "'"
                    single = single_sql + "(" + ",".join(esc2(v) for v in val) + ")"
                    c.execute(single)
                    db.commit()
                    inserted += 1
                except:
                    db.rollback()
                    pass
            print(f"  ⚠️  Row-by-row fallback done: {inserted}")
    
    # Final count
    c.execute("SELECT COUNT(*) FROM pengundi WHERE dun_id = ?", (dun_id,))
    final = c.fetchone()[0]
    print(f"  ✅ {dun_kod} {dun_nama}: {final} rekod di Supabase")

def main():
    print("="*60)
    print("BULK MIGRASI P170 - Multi-row INSERT")
    print("="*60)
    
    db = get_db()
    c = db.cursor()
    
    # Get parlimen_id
    c.execute("SELECT id FROM parlimen WHERE kod = 'P170'")
    pid = c.fetchone()[0]
    print(f"✅ Parlimen ID: {pid}")
    
    # BUANG DUPLIKASI N13
    print("\n🧹 MEMBUANG DUPLIKASI N13...")
    c.execute("SELECT id FROM dun WHERE kod = 'N13'")
    r = c.fetchone()
    if r:
        did = r[0]
        c.execute("SELECT COUNT(*) FROM pengundi WHERE dun_id = ?", (did,))
        before = c.fetchone()[0]
        
        # Get duplicate no_kp values
        c.execute("""
            SELECT no_kp FROM pengundi 
            WHERE dun_id = ? AND no_kp IS NOT NULL
            GROUP BY no_kp HAVING COUNT(*) > 1
        """, (did,))
        dups = [row[0] for row in c.fetchall()]
        print(f"  Duplikasi: {len(dups)} no_kp")
        
        deleted = 0
        for no_kp in dups:
            c.execute("SELECT id FROM pengundi WHERE no_kp = ? AND dun_id = ? ORDER BY id", (no_kp, did))
            ids = [row[0] for row in c.fetchall()]
            for id_to_del in ids[1:]:
                c.execute("DELETE FROM pengundi WHERE id = ?", (id_to_del,))
                deleted += 1
        
        db.commit()
        c.execute("SELECT COUNT(*) FROM pengundi WHERE dun_id = ?", (did,))
        after = c.fetchone()[0]
        print(f"  Dibuang {deleted} duplicates: {before} -> {after}")
    
    # MIGRASI N14 & N15
    for folder, filename, kod, nama in [
        ("DUN N14 TAMPARULI", "SENARAI PENGUNDI TAMPARULI.xlsx", "N14", "Tamparuli"),
        ("DUN N15 KIULU", "SENARAI PENGUNDI KIULU.xlsx", "N15", "Kiulu"),
    ]:
        process_dun(db, c, folder, filename, kod, nama, pid)
    
    db.close()
    
    # Final summary
    db2 = get_db()
    c2 = db2.cursor()
    c2.execute("SELECT d.kod, d.nama, COUNT(*) FROM pengundi p JOIN dun d ON p.dun_id=d.id GROUP BY d.kod, d.nama ORDER BY d.kod")
    print(f"\n{'='*60}")
    print("✅ MIGRASI SELESAI!")
    for r in c2.fetchall():
        print(f"  {r[0]} {r[1]}: {r[2]}")
    c2.execute("SELECT COUNT(*) FROM pengundi")
    print(f"  JUMLAH: {c2.fetchone()[0]} rekod di Supabase")
    print(f"{'='*60}")
    db2.close()

if __name__ == "__main__":
    main()