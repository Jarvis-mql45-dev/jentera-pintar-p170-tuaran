"""
Fix migration data: padam sample N12, re-import N13 & N14.
Guna: python fix_migration.py
"""
import sys, os
sys.path.insert(0, 'backend')
import pandas as pd
from datetime import datetime
from database import get_db

CHUNK = 10000

def checked(v):
    if pd.isna(v): return False
    return str(v).strip().upper() in ('1','1.0','Y','YES','TRUE')

def kp(raw):
    if pd.isna(raw): return None
    s = str(raw).strip().replace('-','').replace(' ','')
    d = ''.join(c for c in s if c.isdigit())
    return d[-12:] if len(d) >= 12 else (d or None)

def esc(v):
    if v is None: return 'NULL'
    if isinstance(v, int) and not isinstance(v, bool): return str(v)
    return chr(39) + str(v).replace(chr(39), chr(39)+chr(39)) + chr(39)

def main():
    db = get_db()
    c = db.cursor()
    
    c.execute("SELECT id FROM parlimen WHERE kod = 'P170'")
    pid = c.fetchone()[0]
    print(f"Parlimen ID: {pid}")
    
    # 1. PADAM SAMPLE DATA N12
    print("\n1️⃣  MEMBUANG SAMPLE DATA N12...")
    c.execute("DELETE FROM pengundi WHERE sumber_pdm = 'Seed Data'")
    deleted = c.rowcount
    db.commit()
    print(f"   Dibuang {deleted} sample records")
    
    # Count N12 now
    c.execute("SELECT id FROM dun WHERE kod = 'N12'")
    n12_id = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM pengundi WHERE dun_id = ?", (n12_id,))
    print(f"   N12 sekarang: {c.fetchone()[0]} pengundi")
    
    # 2. PADAM & IMPORT SEMULA N13
    for kod, nama, fn in [("N13", "Pantai Dalit", "SENARAI PENGUNDI PANTAI DALIT.xlsx")]:
        print(f"\n2️⃣  IMPORT SEMULA {kod} {nama}...")
        
        c.execute("SELECT id FROM dun WHERE kod = ?", (kod,))
        did = c.fetchone()[0]
        
        # Padam semua pengundi untuk DUN ini
        c.execute("DELETE FROM pengundi WHERE dun_id = ?", (did,))
        db.commit()
        print(f"   Dibuang semua pengundi {kod}")
        
        # Baca Excel
        df = pd.read_excel(f"DUN {kod} {nama}/{fn}")
        df.columns = [str(x).strip().upper() for x in df.columns]
        total = len(df)
        print(f"   Fail: {total} pengundi")
        
        # Pre-load PDM & kampung
        c.execute("SELECT id, nama FROM pdm WHERE dun_id = ?", (did,))
        pdm_c = {r[1]: r[0] for r in c.fetchall()}
        c.execute("SELECT id, nama FROM kampung WHERE pdm_id IN (SELECT id FROM pdm WHERE dun_id = ?)", (did,))
        kg_c = {r[1]: r[0] for r in c.fetchall()}
        
        now = datetime.now().isoformat()
        rows = []
        
        for _, row in df.iterrows():
            try:
                nk = kp(row.get('NO KP'))
                nm = str(row.get('NAMA PENUH','')).strip().upper() if not pd.isna(row.get('NAMA PENUH')) else None
                if not nk or not nm: continue
                
                j = str(row.get('JANTINA','')).strip().upper()
                jn = 'L' if j in ('L','LELAKI') else ('P' if j in ('P','PEREMPUAN') else None)
                th = row.get('TAHUN LAHIR')
                tl = int(float(str(th))) if not pd.isna(th) else None
                
                pk = str(row.get('DAERAH MENGUNDI','')).strip().upper() if not pd.isna(row.get('DAERAH MENGUNDI')) else None
                pdi = pdm_c.get(pk) if pk else None
                if pk and pdi is None:
                    c.execute("INSERT INTO pdm (dun_id,nama,keterangan,dicipta_pada) VALUES (?,?,?,?)",
                        (did, pk, f"{pk} - {nama}", now))
                    db.commit()
                    pdi = c.lastrowid
                    pdm_c[pk] = pdi
                
                lk = str(row.get('LOKALITI','')).strip().upper() if not pd.isna(row.get('LOKALITI')) else None
                li = kg_c.get(lk) if lk else None
                if lk and li is None:
                    c.execute("INSERT INTO kampung (pdm_id,nama,keterangan,dicipta_pada) VALUES (?,?,?,?)",
                        (pdi or did, lk, f"{lk} - {pk or nama}", now))
                    db.commit()
                    li = c.lastrowid
                    kg_c[lk] = li
                
                p = checked(row.get('PUTIH'))
                h = checked(row.get('HITAM'))
                a = checked(row.get('ATAS PAGAR'))
                t2 = checked(row.get('TAK KENAL'))
                sk = "Putih" if p else ("Hitam" if h else ("Atas Pagar" if a else ("Tidak Kenal" if t2 else "Belum Dikenal Pasti")))
                fz = "Meninggal Dunia" if checked(row.get('MENINGGAL DUNIA')) else "Hidup"
                tl2 = str(row.get('NO TELEFON','')).strip() if not pd.isna(row.get('NO TELEFON')) else None
                
                rows.append((nk, nm, jn, tl, pid, did, pdi, li, pk, lk, tl2, sk, fz, 0, 'Sah', 'Migrasi P170', now))
            except:
                continue
        
        print(f"   Disiapkan: {len(rows)} rows")
        
        SQL = "INSERT INTO pengundi (no_kp,nama_penuh,jantina,tahun_lahir,parlimen_id,dun_id,pdm_id,kampung_id,dm,lokaliti,no_telefon,status_sokongan,status_fizikal,adalah_pemilik_apps,status_rekod,sumber_pdm,dicipta_pada) VALUES "
        
        done = 0
        for i in range(0, len(rows), CHUNK):
            chunk = rows[i:i+CHUNK]
            vals = ',\n'.join('(' + ','.join(esc(x) for x in r) + ')' for r in chunk)
            try:
                c.execute(SQL + vals)
                db.commit()
                done += len(chunk)
                print(f"   +{done}/{total}")
            except Exception as ex:
                print(f"   Bulk error: {ex}")
                db.rollback()
                for r in chunk:
                    try:
                        c.execute(SQL + '(' + ','.join(esc(x) for x in r) + ')')
                        db.commit()
                        done += 1
                    except:
                        db.rollback()
                print(f"   Fallback: {done}")
        
        c.execute("SELECT COUNT(*) FROM pengundi WHERE dun_id = ?", (did,))
        print(f"   ✅ {kod} {nama}: {c.fetchone()[0]}")
    
    # Summary
    db.close()
    db2 = get_db()
    c2 = db2.cursor()
    c2.execute("SELECT d.kod, d.nama, COUNT(*) FROM pengundi p JOIN dun d ON p.dun_id=d.id GROUP BY d.kod, d.nama ORDER BY d.kod")
    print(f"\n{'='*60}")
    total = 0
    for r in c2.fetchall():
        print(f"  {r[0]} {r[1]}: {r[2]}")
        total += r[2]
    print(f"  TOTAL: {total}")
    print(f"{'='*60}")
    db2.close()

if __name__ == "__main__":
    main()