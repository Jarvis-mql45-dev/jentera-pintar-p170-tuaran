"""
Sambung migrasi untuk DUN yang belum selesai (N13, N14, N15).
Guna: python migrate_p170_continue.py
"""
import sys, os
sys.path.insert(0, 'backend')
import pandas as pd
from datetime import datetime
from database import get_db, init_db

DUN_CONFIG = [
    ("DUN N13 PANTAI DALIT", "SENARAI PENGUNDI PANTAI DALIT.xlsx", "N13", "Pantai Dalit"),
    ("DUN N14 TAMPARULI", "SENARAI PENGUNDI TAMPARULI.xlsx", "N14", "Tamparuli"),
    ("DUN N15 KIULU", "SENARAI PENGUNDI KIULU.xlsx", "N15", "Kiulu"),
]

def is_checked(val):
    if pd.isna(val): return False
    return str(val).strip().upper() in ['1','1.0','Y','YES','TRUE']

def main():
    print("="*60)
    print("SAMBUNG MIGRASI P170 - DUN N13, N14, N15")
    print("="*60)
    
    init_db()
    db = get_db()
    cursor = db.cursor()
    now = datetime.now().isoformat()
    
    cursor.execute("SELECT id FROM parlimen WHERE kod = 'P170'")
    parlimen_id = cursor.fetchone()[0]
    
    INSERT_SQL = """
        INSERT INTO pengundi 
        (no_kp, nama_penuh, jantina, tahun_lahir,
         parlimen_id, dun_id, pdm_id, kampung_id,
         dm, lokaliti, no_telefon,
         status_sokongan, status_fizikal,
         adalah_pemilik_apps, status_rekod, sumber_pdm, dicipta_pada)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """
    
    for folder, filename, dun_kod, dun_nama in DUN_CONFIG:
        path = os.path.join(folder, filename)
        if not os.path.exists(path):
            print(f"⚠️  {path} tidak wujud")
            continue
        
        print(f"\n📂 {dun_kod} {dun_nama}")
        
        cursor.execute("SELECT id FROM dun WHERE kod = ?", (dun_kod,))
        r = cursor.fetchone()
        if not r:
            cursor.execute("INSERT INTO dun (parlimen_id,kod,nama,keterangan,dicipta_pada) VALUES (?,?,?,?,?)",
                (parlimen_id, dun_kod, dun_nama, f"DUN {dun_kod} {dun_nama}", now))
            db.commit()
            dun_id = cursor.lastrowid
        else:
            dun_id = r[0]
        
        df = pd.read_excel(path)
        df.columns = [str(c).strip().upper() for c in df.columns]
        total_rows = len(df)
        print(f"  📊 {total_rows} pengundi dalam fail")
        
        cursor.execute("SELECT COUNT(*) FROM pengundi WHERE dun_id = ?", (dun_id,))
        already = cursor.fetchone()[0]
        print(f"  ✅ {already} sudah dalam database")
        
        if already >= total_rows:
            print(f"  ✅ {dun_kod} sudah lengkap, skip")
            continue
        
        cursor.execute("SELECT id, nama FROM pdm WHERE dun_id = ?", (dun_id,))
        pdm_cache = {r2[1]: r2[0] for r2 in cursor.fetchall()}
        
        cursor.execute("SELECT id, nama FROM kampung WHERE pdm_id IN (SELECT id FROM pdm WHERE dun_id = ?)", (dun_id,))
        kg_cache = {r2[1]: r2[0] for r2 in cursor.fetchall()}
        
        BATCH_SIZE = 250  # Smaller batch for stability
        batch = []
        skipped = 0
        inserted = 0
        
        for _, r in df.iterrows():
            try:
                no_kp = str(r.get('NO KP','')).strip().replace('-','').replace(' ','')
                digits = ''.join(c for c in no_kp if c.isdigit())
                no_kp = digits[-12:] if len(digits) >= 12 else digits
                if not no_kp: 
                    skipped += 1
                    continue
                
                nama = str(r.get('NAMA PENUH','')).strip().upper()
                if not nama:
                    skipped += 1
                    continue
                
                j = str(r.get('JANTINA','')).strip().upper()
                jantina = 'L' if j in ('L','LELAKI') else ('P' if j in ('P','PEREMPUAN') else None)
                
                thn = r.get('TAHUN LAHIR')
                tahun_lahir = int(float(str(thn))) if not pd.isna(thn) else None
                
                pdm_raw = r.get('DAERAH MENGUNDI')
                pdm_key = str(pdm_raw).strip().upper() if not pd.isna(pdm_raw) else None
                pdm_id = None
                if pdm_key:
                    pdm_id = pdm_cache.get(pdm_key)
                    if pdm_id is None:
                        cursor.execute("INSERT INTO pdm (dun_id,nama,keterangan,dicipta_pada) VALUES (?,?,?,?)", 
                            (dun_id, pdm_key, f"{pdm_key} - {dun_nama}", now))
                        db.commit()
                        pdm_id = cursor.lastrowid
                        pdm_cache[pdm_key] = pdm_id
                
                kg_raw = r.get('LOKALITI')
                kg_key = str(kg_raw).strip().upper() if not pd.isna(kg_raw) else None
                kg_id = None
                if kg_key:
                    kg_id = kg_cache.get(kg_key)
                    if kg_id is None:
                        cursor.execute("INSERT INTO kampung (pdm_id,nama,keterangan,dicipta_pada) VALUES (?,?,?,?)",
                            (pdm_id or dun_id, kg_key, f"{kg_key} - {pdm_key or dun_nama}", now))
                        db.commit()
                        kg_id = cursor.lastrowid
                        kg_cache[kg_key] = kg_id
                
                p = is_checked(r.get('PUTIH'))
                h = is_checked(r.get('HITAM'))
                a = is_checked(r.get('ATAS PAGAR'))
                t = is_checked(r.get('TAK KENAL'))
                sokongan = "Putih" if p else ("Hitam" if h else ("Atas Pagar" if a else ("Tidak Kenal" if t else "Belum Dikenal Pasti")))
                
                meninggal = is_checked(r.get('MENINGGAL DUNIA'))
                fizikal = "Meninggal Dunia" if meninggal else "Hidup"
                
                tel = r.get('NO TELEFON')
                no_telefon = str(tel).strip() if not pd.isna(tel) else None
                
                batch.append((no_kp, nama, jantina, tahun_lahir,
                    parlimen_id, dun_id, pdm_id, kg_id,
                    pdm_key, kg_key, no_telefon,
                    sokongan, fizikal, 0, 'Sah', 'Migrasi P170', now))
                
                if len(batch) >= BATCH_SIZE:
                    try:
                        cursor.executemany(INSERT_SQL, batch)
                        db.commit()
                        inserted += len(batch)
                        print(f"  ⏳ +{len(batch)} (jumlah: {inserted}/{total_rows})")
                    except Exception as e:
                        print(f"  ⚠️  Batch error: {e}")
                        db.rollback()
                        # Insert one by one for this batch
                        for item in batch:
                            try:
                                cursor.execute(INSERT_SQL, item)
                                db.commit()
                                inserted += 1
                            except:
                                db.rollback()
                                pass
                    batch = []
                    
            except Exception as e:
                skipped += 1
                continue
        
        if batch:
            try:
                cursor.executemany(INSERT_SQL, batch)
                db.commit()
                inserted += len(batch)
            except:
                for item in batch:
                    try:
                        cursor.execute(INSERT_SQL, item)
                        db.commit()
                        inserted += 1
                    except:
                        pass
        
        cursor.execute("SELECT COUNT(*) FROM pengundi WHERE dun_id = ?", (dun_id,))
        final = cursor.fetchone()[0]
        print(f"\n  ✅ {dun_kod} {dun_nama}: {final} rekod di Supabase (+{inserted} baru)")
    
    db.close()
    
    cursor2 = get_db()
    c = cursor2.cursor()
    c.execute("SELECT d.kod, COUNT(*) FROM pengundi p JOIN dun d ON p.dun_id=d.id GROUP BY d.kod ORDER BY d.kod")
    summary = [f"{r[0]}:{r[1]}" for r in c.fetchall()]
    c.execute("SELECT COUNT(*) FROM pengundi")
    total = c.fetchone()[0]
    cursor2.close()
    
    print(f"\n{'='*60}")
    print(f"✅ MIGRASI SELESAI!")
    print(f"   {' | '.join(summary)}")
    print(f"   JUMLAH: {total} rekod di Supabase")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()