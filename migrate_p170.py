"""
Migrasi data P170 Tuaran ke Supabase (v3 - executemany batch).
Guna: python migrate_p170.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
import pandas as pd
from datetime import datetime
from database import get_db, init_db

DUN_CONFIG = [
    ("DUN N12 SULAMAN", "SENARAI PENGUNDI SULAMAN.xlsx", "N12", "Sulaman"),
    ("DUN N13 PANTAI DALIT", "SENARAI PENGUNDI PANTAI DALIT.xlsx", "N13", "Pantai Dalit"),
    ("DUN N14 TAMPARULI", "SENARAI PENGUNDI TAMPARULI.xlsx", "N14", "Tamparuli"),
    ("DUN N15 KIULU", "SENARAI PENGUNDI KIULU.xlsx", "N15", "Kiulu"),
]

def is_checked(val):
    if pd.isna(val): return False
    return str(val).strip().upper() in ['1','1.0','Y','YES','TRUE']

def main():
    print("="*60)
    print("MIGRASI P170 TUARAN v3 (executemany batch)")
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
    
    total = 0
    
    for folder, filename, dun_kod, dun_nama in DUN_CONFIG:
        path = os.path.join(folder, filename)
        if not os.path.exists(path): continue
        
        print(f"\n📂 {dun_kod} {dun_nama}")
        df = pd.read_excel(path)
        df.columns = [str(c).strip().upper() for c in df.columns]
        
        # DUN ID
        cursor.execute("SELECT id FROM dun WHERE kod = ?", (dun_kod,))
        r = cursor.fetchone()
        dun_id = r[0] if r else (cursor.execute("INSERT INTO dun (parlimen_id,kod,nama,keterangan,dicipta_pada) VALUES (?,?,?,?,?)", (parlimen_id,dun_kod,dun_nama,f"DUN {dun_kod} {dun_nama}",now)), db.commit(), cursor.lastrowid)[2]
        
        # Pre-load PDM & kampung cache
        cursor.execute("SELECT id, nama FROM pdm WHERE dun_id = ?", (dun_id,))
        pdm_cache = {r2[1]: r2[0] for r2 in cursor.fetchall()}
        
        cursor.execute("SELECT id, nama FROM kampung WHERE pdm_id IN (SELECT id FROM pdm WHERE dun_id = ?)", (dun_id,))
        kg_cache = {r2[1]: r2[0] for r2 in cursor.fetchall()}
        
        print(f"  📊 {len(df)} pengundi")
        
        batch = []
        BATCH_SIZE = 500
        
        for _, r in df.iterrows():
            try:
                no_kp = str(r.get('NO KP','')).strip().replace('-','').replace(' ','')
                digits = ''.join(c for c in no_kp if c.isdigit())
                no_kp = digits[-12:] if len(digits) >= 12 else digits
                if not no_kp: continue
                
                nama = str(r.get('NAMA PENUH','')).strip().upper()
                if not nama: continue
                
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
                        cursor.execute("INSERT INTO pdm (dun_id,nama,keterangan,dicipta_pada) VALUES (?,?,?,?)", (dun_id,pdm_key,f"{pdm_key} - {dun_nama}",now))
                        db.commit()
                        pdm_id = cursor.lastrowid
                        pdm_cache[pdm_key] = pdm_id
                
                kg_raw = r.get('LOKALITI')
                kg_key = str(kg_raw).strip().upper() if not pd.isna(kg_raw) else None
                kg_id = None
                if kg_key:
                    kg_id = kg_cache.get(kg_key)
                    if kg_id is None:
                        cursor.execute("INSERT INTO kampung (pdm_id,nama,keterangan,dicipta_pada) VALUES (?,?,?,?)", (pdm_id or dun_id,kg_key,f"{kg_key} - {pdm_key or dun_nama}",now))
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
                    cursor.executemany(INSERT_SQL, batch)
                    db.commit()
                    print(f"  ⏳ +{len(batch)} ({len(df) - (len(batch) * (len(batch) // BATCH_SIZE))} remaining)" if len(batch) == BATCH_SIZE else "", end="")
                    batch = []
                    
            except Exception as e:
                continue
        
        # Flush remaining
        if batch:
            cursor.executemany(INSERT_SQL, batch)
            db.commit()
        
        # Count for this DUN
        cursor.execute("SELECT COUNT(*) FROM pengundi WHERE dun_id = ? AND sumber_pdm = 'Migrasi P170'", (dun_id,))
        count = cursor.fetchone()[0]
        total += count
        print(f"\n  ✅ {dun_kod} {dun_nama}: {count} rekod di Supabase")
    
    db.close()
    print(f"\n{'='*60}")
    print(f"✅ MIGRASI SELESAI! Jumlah: {total} rekod di Supabase")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()