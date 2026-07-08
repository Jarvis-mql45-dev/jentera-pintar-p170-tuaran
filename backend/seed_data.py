"""
Seed data script untuk JenteraPintar P170 Tuaran.
Insert sample data pengundi untuk tujuan testing di Render.
Guna: python seed_data.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from database import get_db, init_db
from datetime import datetime

SAMPLE_DATA = [
    {"no_kp": "900101085671", "nama": "AHMAD BIN ISMAIL", "jantina": "L", "tahun_lahir": 1990, "dm": "PDM BINGOLON", "lokaliti": "Kampung Bingolon", "sokongan": "Putih"},
    {"no_kp": "850512085432", "nama": "SITI BINTI ABDULLAH", "jantina": "P", "tahun_lahir": 1985, "dm": "PDM BINGOLON", "lokaliti": "Kampung Bingolon", "sokongan": "Atas Pagar"},
    {"no_kp": "920803085123", "nama": "MOHAMAD BIN ALI", "jantina": "L", "tahun_lahir": 1992, "dm": "PDM DUALOG", "lokaliti": "Kampung Dualog", "sokongan": "Putih"},
    {"no_kp": "780615084567", "nama": "FATIMAH BINTI HASSAN", "jantina": "P", "tahun_lahir": 1978, "dm": "PDM DUALOG", "lokaliti": "Kampung Dualog", "sokongan": "Hitam"},
    {"no_kp": "950101089012", "nama": "AZMAN BIN OTHMAN", "jantina": "L", "tahun_lahir": 1995, "dm": "PDM INDARASON", "lokaliti": "Kampung Indarason", "sokongan": "Atas Pagar"},
    {"no_kp": "881220087654", "nama": "NORMAH BINTI YUSOF", "jantina": "P", "tahun_lahir": 1988, "dm": "PDM INDARASON", "lokaliti": "Kampung Indarason", "sokongan": "Putih"},
    {"no_kp": "700315086789", "nama": "RAMLI BIN KAMARUDIN", "jantina": "L", "tahun_lahir": 1970, "dm": "PDM KANDAWAYON", "lokaliti": "Kampung Kandawayon", "sokongan": "Tidak Kenal"},
    {"no_kp": "930820084321", "nama": "ZAINAB BINTI AHMAD", "jantina": "P", "tahun_lahir": 1993, "dm": "PDM KANDAWAYON", "lokaliti": "Kampung Kandawayon", "sokongan": "Putih"},
    {"no_kp": "650101083210", "nama": "JAMAL BIN BASRI", "jantina": "L", "tahun_lahir": 1965, "dm": "PDM LAJONG", "lokaliti": "Kampung Lajong", "sokongan": "Atas Pagar"},
    {"no_kp": "970512088765", "nama": "ROSNANI BINTI ABU", "jantina": "P", "tahun_lahir": 1997, "dm": "PDM LAJONG", "lokaliti": "Kampung Lajong", "sokongan": "Putih"},
    {"no_kp": "820815089876", "nama": "HALIM BIN SAID", "jantina": "L", "tahun_lahir": 1982, "dm": "PDM LODUNG", "lokaliti": "Kampung Lodung", "sokongan": "Hitam"},
    {"no_kp": "900101089654", "nama": "MARIAH BINTI JOHARI", "jantina": "P", "tahun_lahir": 1990, "dm": "PDM LODUNG", "lokaliti": "Kampung Lodung", "sokongan": "Atas Pagar"},
]

def seed_database():
    # Pastikan semua jadual wujud sebelum seed
    init_db()
    
    db = get_db()
    cursor = db.cursor()
    
    # ================================================================
    # SEED DATA HIERARKI: parlimen, dun (dijalankan di init_db)
    # ================================================================
    # parlimen & dun sudah di-seed secara automatik dalam init_db()
    # Di sini kita cuma pastikan ia wujud sebelum insert pengundi
    now = datetime.now().isoformat()
    
    # Seed parlimen jika belum ada
    cursor.execute("SELECT COUNT(*) FROM parlimen")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO parlimen (kod, nama, keterangan, dicipta_pada) VALUES (?, ?, ?, ?)",
            ("P170", "Tuaran", "Parlimen P170 Tuaran, Sabah", now)
        )
        parlimen_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO dun (parlimen_id, kod, nama, keterangan, dicipta_pada) VALUES (?, ?, ?, ?, ?)",
            (parlimen_id, "N12", "Sulaman", "DUN N12 Sulaman", now)
        )
        cursor.execute(
            "INSERT INTO dun (parlimen_id, kod, nama, keterangan, dicipta_pada) VALUES (?, ?, ?, ?, ?)",
            (parlimen_id, "N13", "Pantai Dalit", "DUN N13 Pantai Dalit", now)
        )
        cursor.execute(
            "INSERT INTO dun (parlimen_id, kod, nama, keterangan, dicipta_pada) VALUES (?, ?, ?, ?, ?)",
            (parlimen_id, "N14", "Tamparuli", "DUN N14 Tamparuli", now)
        )
        cursor.execute(
            "INSERT INTO dun (parlimen_id, kod, nama, keterangan, dicipta_pada) VALUES (?, ?, ?, ?, ?)",
            (parlimen_id, "N15", "Kiulu", "DUN N15 Kiulu", now)
        )
        print("✅ Seed data parlimen & DUN untuk P170 Tuaran telah dimasukkan")
        db.commit()
    
    # ================================================================
    # SEED DATA PDM & KAMPUNG untuk sample data
    # ================================================================
    # Dapatkan ID DUN N12 untuk PDM sample (N05 Matunggong - data lama)
    cursor.execute("SELECT id FROM dun WHERE kod = 'N12'")
    dun_row = cursor.fetchone()
    dun_id = dun_row[0] if dun_row else None
    
    if dun_id:
        # Daftar PDM jika belum ada
        pdm_list = ["PDM BINGOLON", "PDM DUALOG", "PDM INDARASON", "PDM KANDAWAYON", "PDM LAJONG", "PDM LODUNG"]
        pdm_ids = {}
        for pdm_nama in pdm_list:
            cursor.execute("SELECT id FROM pdm WHERE nama = ?", (pdm_nama,))
            row = cursor.fetchone()
            if row:
                pdm_ids[pdm_nama] = row[0]
            else:
                cursor.execute(
                    "INSERT INTO pdm (dun_id, nama, keterangan, dicipta_pada) VALUES (?, ?, ?, ?)",
                    (dun_id, pdm_nama, f"{pdm_nama} - DUN N12 Sulaman", now)
                )
                pdm_ids[pdm_nama] = cursor.lastrowid
        
        # Daftar kampung jika belum ada
        kampung_map = {
            "PDM BINGOLON": "Kampung Bingolon",
            "PDM DUALOG": "Kampung Dualog",
            "PDM INDARASON": "Kampung Indarason",
            "PDM KANDAWAYON": "Kampung Kandawayon",
            "PDM LAJONG": "Kampung Lajong",
            "PDM LODUNG": "Kampung Lodung",
        }
        kampung_ids = {}
        for pdm_nama, kampung_nama in kampung_map.items():
            cursor.execute("SELECT id FROM kampung WHERE nama = ?", (kampung_nama,))
            row = cursor.fetchone()
            if row:
                kampung_ids[kampung_nama] = row[0]
            else:
                cursor.execute(
                    "INSERT INTO kampung (pdm_id, nama, keterangan, dicipta_pada) VALUES (?, ?, ?, ?)",
                    (pdm_ids[pdm_nama], kampung_nama, f"{kampung_nama} - {pdm_nama}", now)
                )
                kampung_ids[kampung_nama] = cursor.lastrowid
        
        db.commit()
        print(f"✅ Seed data PDM & Kampung untuk sample telah dimasukkan")
    
    # ================================================================
    # SEED DATA PENGUNDI (sedia ada)
    # ================================================================
    cursor.execute("SELECT COUNT(*) FROM pengundi")
    count = cursor.fetchone()[0]
    
    if count > 0:
        print(f"✅ Database already has {count} records. Skipping seed.")
        db.close()
        return
    
    inserted = 0
    
    for data in SAMPLE_DATA:
        # Cuba cari FK parlimen_id, dun_id, pdm_id, kampung_id
        cursor.execute("SELECT id FROM parlimen WHERE kod = 'P170'")
        parlimen_row = cursor.fetchone()
        parlimen_id = parlimen_row[0] if parlimen_row else None
        
        cursor.execute("SELECT id FROM dun WHERE kod = 'N12'")
        dun_row = cursor.fetchone()
        d_id = dun_row[0] if dun_row else None
        
        cursor.execute("SELECT id FROM pdm WHERE nama = ?", (data["dm"],))
        pdm_row = cursor.fetchone()
        pdm_id = pdm_row[0] if pdm_row else None
        
        cursor.execute("SELECT id FROM kampung WHERE nama = ?", (data["lokaliti"],))
        kampung_row = cursor.fetchone()
        kampung_id = kampung_row[0] if kampung_row else None
        
        cursor.execute("""
            INSERT INTO pengundi 
            (no_kp, nama_penuh, jantina, tahun_lahir, parlimen_id, dun_id, pdm_id, kampung_id,
             dm, lokaliti, status_sokongan, status_fizikal, status_rekod, sumber_pdm, dicipta_pada)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["no_kp"], data["nama"], data["jantina"], data["tahun_lahir"],
            parlimen_id, d_id, pdm_id, kampung_id,
            data["dm"], data["lokaliti"], data["sokongan"],
            "Hidup", "Sah", "Seed Data", now
        ))
        inserted += 1
    
    db.commit()
    db.close()
    print(f"✅ {inserted} sample records inserted successfully!")

if __name__ == "__main__":
    seed_database()