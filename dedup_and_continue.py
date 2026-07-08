"""
Buang duplikasi dan sambung migrasi untuk N14 dan N15.
Guna: python dedup_and_continue.py
"""
import sys, os
sys.path.insert(0, 'backend')
import pandas as pd
from datetime import datetime
from database import get_db

def main():
    db = get_db()
    c = db.cursor()
    
    print("MEMBUANG DUPLIKASI N13...")
    c.execute("SELECT id FROM dun WHERE kod = 'P170'")  # just test connection
    c.execute("SELECT id FROM dun WHERE kod = 'N13'")
    r = c.fetchone()
    if r:
        dun_id = r[0]
        # Get total count for N13
        c.execute("SELECT COUNT(*) FROM pengundi WHERE dun_id = ?", (dun_id,))
        total = c.fetchone()[0]
        print(f"N13 total rekod: {total}")
        
        # Find duplicates by no_kp
        c.execute("""
            SELECT no_kp, COUNT(*) as cnt 
            FROM pengundi 
            WHERE dun_id = ? AND no_kp IS NOT NULL 
            GROUP BY no_kp 
            HAVING COUNT(*) > 1
        """, (dun_id,))
        dup_rows = c.fetchall()
        print(f"Duplikasi found: {len(dup_rows)} no_kp")
        
        # Delete duplicates: keep only the one with smallest id
        deleted = 0
        for dup in dup_rows:
            no_kp = dup[0]
            c.execute("""
                SELECT id FROM pengundi 
                WHERE no_kp = ? AND dun_id = ? 
                ORDER BY id
            """, (no_kp, dun_id))
            ids = [row[0] for row in c.fetchall()]
            # Keep first, delete rest
            for id_to_delete in ids[1:]:
                c.execute("DELETE FROM pengundi WHERE id = ?", (id_to_delete,))
                deleted += 1
        
        db.commit()
        print(f"Dibuang {deleted} duplicates")
    
    # --- TERUSKAN MIGRASI N14 & N15 ---
    now = datetime.now().isoformat()
    
    for folder, filename, dun_kod, dun_nama in [
        ("DUN N14 TAMPARULI", "SENARAI PENGUNDI TAMPARULI.xlsx", "N14", "Tamparuli"),
        ("DUN N15 KIULU", "SENARAI PENGUNDI KIULU.xlsx", "N15", "Kiulu"),
    ]:
        path = os.path.join(folder, filename)
        if not os.path.exists(path):
            print(f"Warning: {path} not found")
            continue
        
        print(f"\nStarting {dun_kod} {dun_nama}")
        
        c.execute("SELECT id FROM dun WHERE kod = ?", (dun_kod,))
        r = c.fetchone()
        if r:
            dun_id = r[0]
        else:
            c.execute("SELECT id FROM parlimen WHERE kod = 'P170'")
            pid = c.fetchone()[0]
            c.execute("INSERT INTO dun (parlimen_id,kod,nama,keterangan,dicipta_pada) VALUES (?,?,?,?,?)",
                (pid, dun_kod, dun_nama, f"DUN {dun_kod} {dun_nama}", now))
            db.commit()
            dun_id = c.lastrowid
        
        df = pd.read_excel(path)
        df.columns = [str(x).strip().upper() for x in df.columns]
        total = len(df)
        print(f"  File: {total} voters")
        
        c.execute("SELECT COUNT(*) FROM pengundi WHERE dun_id = ?", (dun_id,))
        already = c.fetchone()[0]
        print(f"  Already in DB: {already}")
        
        if already >= total:
            print(f"  {dun_kod} already complete")
            continue
        
        # Pre-load PDM and kampung
        c.execute("SELECT id, nama FROM pdm WHERE dun_id = ?", (dun_id,))
        pdm_cache = {r2[1]: r2[0] for r2 in c.fetchall()}
        
        c.execute("SELECT id, nama FROM kampung WHERE pdm_id IN (SELECT id FROM pdm WHERE dun_id = ?)", (dun_id,))
        kg_cache = {r2[1]: r2[0] for r2 in c.fetchall()}
        
        c.execute("SELECT id FROM parlimen WHERE kod = 'P170'")
        pid = c.fetchone()[0]
        
        INSERT_SQL = """
            INSERT INTO pengundi 
            (no_kp, nama_penuh, jantina, tahun_lahir,
             parlimen_id, dun_id, pdm_id, kampung_id,
             dm, lokaliti, no_telefon,
             status_sokongan, status_fizikal,
             adalah_pemilik_apps, status_rekod, sumber_pdm, dicipta_pada)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """
        
        batch = []
        BATCH_SIZE = 500
        inserted = 0
        
        def checked(v):
            if pd.isna(v): return False
            return str(v).strip().upper() in ('1','1.0','Y','YES','TRUE')
        
        for _, row in df.iterrows():
            try:
                no_kp_raw = row.get('NO KP')
                nama = row.get('NAMA PENUH')
                if pd.isna(no_kp_raw) or pd.isna(nama):
                    continue
                
                no_kp = str(no_kp_raw).strip().replace('-','').replace(' ','')
                digits = ''.join(c2 for c2 in no_kp if c2.isdigit())
                no_kp = digits[-12:] if len(digits) >= 12 else digits
                if not no_kp: continue
                
                nama_str = str(nama).strip().upper()
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
                
                p = checked(row.get('PUTIH'))
                h = checked(row.get('HITAM'))
                a = checked(row.get('ATAS PAGAR'))
                t = checked(row.get('TAK KENAL'))
                sokongan = "Putih" if p else ("Hitam" if h else ("Atas Pagar" if a else ("Tidak Kenal" if t else "Belum Dikenal Pasti")))
                fizikal = "Meninggal Dunia" if checked(row.get('MENINGGAL DUNIA')) else "Hidup"
                
                tel = row.get('NO TELEFON')
                no_telefon = str(tel).strip() if not pd.isna(tel) else None
                
                batch.append((no_kp, nama_str, jantina, tahun_lahir,
                    pid, dun_id, pdm_id, kg_id,
                    pdm_key, kg_key, no_telefon,
                    sokongan, fizikal, 0, 'Sah', 'Migrasi P170', now))
                
                if len(batch) >= BATCH_SIZE:
                    c.executemany(INSERT_SQL, batch)
                    db.commit()
                    inserted += len(batch)
                    print(f"  +{inserted}/{total}")
                    batch = []
                    
            except:
                continue
        
        if batch:
            try:
                c.executemany(INSERT_SQL, batch)
                db.commit()
                inserted += len(batch)
            except:
                pass
        
        c.execute("SELECT COUNT(*) FROM pengundi WHERE dun_id = ?", (dun_id,))
        final = c.fetchone()[0]
        print(f"  {dun_kod} {dun_nama}: {final} records")
    
    db.close()
    
    # Final summary
    db2 = get_db()
    c3 = db2.cursor()
    c3.execute("SELECT d.kod, d.nama, COUNT(*) FROM pengundi p JOIN dun d ON p.dun_id=d.id GROUP BY d.kod, d.nama ORDER BY d.kod")
    print("\n" + "="*60)
    print("MIGRATION COMPLETE!")
    for r3 in c3.fetchall():
        print(f"  {r3[0]} {r3[1]}: {r3[2]}")
    c3.execute("SELECT COUNT(*) FROM pengundi")
    print(f"  TOTAL: {c3.fetchone()[0]}")
    print("="*60)
    db2.close()

if __name__ == "__main__":
    main()