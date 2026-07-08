"""
Fast bulk migration P170 - gunakan SQL DELETE + multi-row INSERT.
Guna: python fast_bulk.py
"""
import sys, os
sys.path.insert(0, 'backend')
import pandas as pd
from datetime import datetime
from database import get_db

CHUNK_SIZE = 5000

def checked(v):
    if pd.isna(v): return False
    return str(v).strip().upper() in ('1','1.0','Y','YES','TRUE')

def kp(raw):
    if pd.isna(raw): return None
    s = str(raw).strip().replace('-','').replace(' ','')
    d = ''.join(c for c in s if c.isdigit())
    return d[-12:] if len(d) >= 12 else (d or None)

def main():
    db = get_db()
    c = db.cursor()
    
    c.execute("SELECT id FROM parlimen WHERE kod = 'P170'")
    pid = c.fetchone()[0]
    print(f"Parlimen ID: {pid}")
    
    # === PAKAI SQL TERUS UNTUK DELETE DUPLIKASI N13 ===
    print("\n🧹 Delete duplicates N13 (SQL)...")
    c.execute("SELECT id FROM dun WHERE kod = 'N13'")
    r = c.fetchone()
    if r:
        did = r[0]
        # SQL: delete all but the first occurrence per no_kp
        c.execute("""
            DELETE FROM pengundi p1
            USING pengundi p2
            WHERE p1.id > p2.id 
            AND p1.no_kp = p2.no_kp 
            AND p1.dun_id = p2.dun_id
            AND p1.dun_id = %s
        """, (did,))
        deleted = c.rowcount
        db.commit()
        print(f"  Deleted {deleted} duplicates via SQL")
        
        c.execute("SELECT COUNT(*) FROM pengundi WHERE dun_id = %s", (did,))
        print(f"  N13 now: {c.fetchone()[0]} records")
    
    # === BULK INSERT N14 & N15 ===
    for folder, fn, kod, nama in [
        ("DUN N14 TAMPARULI", "SENARAI PENGUNDI TAMPARULI.xlsx", "N14", "Tamparuli"),
        ("DUN N15 KIULU", "SENARAI PENGUNDI KIULU.xlsx", "N15", "Kiulu"),
    ]:
        path = os.path.join(folder, fn)
        if not os.path.exists(path):
            print(f"⚠️  {path} not found")
            continue
        
        print(f"\n📂 {kod} {nama}")
        df = pd.read_excel(path)
        df.columns = [str(x).strip().upper() for x in df.columns]
        total = len(df)
        print(f"  File: {total} rows")
        
        c.execute("SELECT id FROM dun WHERE kod = %s", (kod,))
        r = c.fetchone()
        if r:
            did = r[0]
        else:
            now = datetime.now().isoformat()
            c.execute("INSERT INTO dun (parlimen_id,kod,nama,keterangan,dicipta_pada) VALUES (%s,%s,%s,%s,%s)",
                (pid, kod, nama, f"DUN {kod} {nama}", now))
            db.commit()
            did = c.lastrowid
        
        # Pre-load PDM & kampung
        c.execute("SELECT id, nama FROM pdm WHERE dun_id = %s", (did,))
        pdm_cache = {r2[1]: r2[0] for r2 in c.fetchall()}
        c.execute("SELECT id, nama FROM kampung WHERE pdm_id IN (SELECT id FROM pdm WHERE dun_id = %s)", (did,))
        kg_cache = {r2[1]: r2[0] for r2 in c.fetchall()}
        
        now = datetime.now().isoformat()
        
        # Prepare all rows
        all_rows = []
        for _, row in df.iterrows():
            try:
                no_kp = kp(row.get('NO KP'))
                n = str(row.get('NAMA PENUH','')).strip().upper() if not pd.isna(row.get('NAMA PENUH')) else None
                if not no_kp or not n: continue
                
                j = str(row.get('JANTINA','')).strip().upper()
                jantina = 'L' if j in ('L','LELAKI') else ('P' if j in ('P','PEREMPUAN') else None)
                thn = row.get('TAHUN LAHIR')
                tahun_lahir = int(float(str(thn))) if not pd.isna(thn) else None
                
                pk = str(row.get('DAERAH MENGUNDI','')).strip().upper() if not pd.isna(row.get('DAERAH MENGUNDI')) else None
                pdi = pdm_cache.get(pk) if pk else None
                if pk and pdi is None:
                    c.execute("INSERT INTO pdm (dun_id,nama,keterangan,dicipta_pada) VALUES (%s,%s,%s,%s)",
                        (did, pk, f"{pk} - {nama}", now))
                    db.commit()
                    pdi = c.lastrowid
                    pdm_cache[pk] = pdi
                
                lk = str(row.get('LOKALITI','')).strip().upper() if not pd.isna(row.get('LOKALITI')) else None
                li = kg_cache.get(lk) if lk else None
                if lk and li is None:
                    c.execute("INSERT INTO kampung (pdm_id,nama,keterangan,dicipta_pada) VALUES (%s,%s,%s,%s)",
                        (pdi or did, lk, f"{lk} - {pk or nama}", now))
                    db.commit()
                    li = c.lastrowid
                    kg_cache[lk] = li
                
                p = checked(row.get('PUTIH'))
                h = checked(row.get('HITAM'))
                a = checked(row.get('ATAS PAGAR'))
                t2 = checked(row.get('TAK KENAL'))
                sok = "Putih" if p else ("Hitam" if h else ("Atas Pagar" if a else ("Tidak Kenal" if t2 else "Belum Dikenal Pasti")))
                fiz = "Meninggal Dunia" if checked(row.get('MENINGGAL DUNIA')) else "Hidup"
                tel = str(row.get('NO TELEFON','')).strip() if not pd.isna(row.get('NO TELEFON')) else None
                
                all_rows.append((no_kp, n, jantina, tahun_lahir, pid, did, pdi, li, pk, lk, tel, sok, fiz, 0, 'Sah', 'Migrasi P170', now))
            except:
                continue
        
        print(f"  Prepared: {len(all_rows)} rows")
        
        # Bulk insert
        INSERT = """INSERT INTO pengundi (no_kp,nama_penuh,jantina,tahun_lahir,parlimen_id,dun_id,pdm_id,kampung_id,dm,lokaliti,no_telefon,status_sokongan,status_fizikal,adalah_pemilik_apps,status_rekod,sumber_pdm,dicipta_pada) VALUES """
        
        done = 0
        for i in range(0, len(all_rows), CHUNK_SIZE):
            chunk = all_rows[i:i+CHUNK_SIZE]
            def e(v):
                if v is None: return 'NULL'
                if isinstance(v, int): return str(v)
                return "'" + str(v).replace("'","''") + "'"
            vals = ",\n".join("(" + ",".join(e(x) for x in row) + ")" for row in chunk)
            try:
                c.execute(INSERT + vals)
                db.commit()
                done += len(chunk)
                print(f"  +{done}/{total}")
            except Exception as ex:
                print(f"  Error: {ex}")
                db.rollback()
                # Row by row fallback
                for row in chunk:
                    try:
                        v2 = "(" + ",".join(e(x) for x in row) + ")"
                        c.execute(INSERT + v2)
                        db.commit()
                        done += 1
                    except:
                        db.rollback()
                print(f"  Fallback: {done}")
        
        c.execute("SELECT COUNT(*) FROM pengundi WHERE dun_id = %s", (did,))
        print(f"  ✅ {kod} {nama}: {c.fetchone()[0]} records")
    
    db.close()
    
    # Summary
    db2 = get_db()
    c2 = db2.cursor()
    c2.execute("SELECT d.kod, d.nama, COUNT(*) FROM pengundi p JOIN dun d ON p.dun_id=d.id GROUP BY d.kod, d.nama ORDER BY d.kod")
    print(f"\n{'='*60}")
    print("✅ COMPLETE!")
    for r in c2.fetchall():
        print(f"  {r[0]} {r[1]}: {r[2]}")
    c2.execute("SELECT COUNT(*) FROM pengundi")
    print(f"  TOTAL: {c2.fetchone()[0]}")
    print(f"{'='*60}")
    db2.close()

if __name__ == "__main__":
    main()