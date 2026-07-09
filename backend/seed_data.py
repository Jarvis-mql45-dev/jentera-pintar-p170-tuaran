"""
Seed data script untuk JenteraPintar P170 Tuaran.
Insert sample data pengundi untuk tujuan testing.
Guna: python seed_data.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from backend.database import get_db, init_db
from datetime import datetime

SAMPLE_DATA = [
    # DUN N12 Sulaman
    {"no_kp": "900101085671", "nama": "AHMAD BIN ISMAIL", "jantina": "L", "tahun_lahir": 1990, "dm": "PDM BINGOLON", "lokaliti": "Kampung Bingolon", "sokongan": "Putih", "dun_kod": "N12"},
    {"no_kp": "850512085432", "nama": "SITI BINTI ABDULLAH", "jantina": "P", "tahun_lahir": 1985, "dm": "PDM BINGOLON", "lokaliti": "Kampung Bingolon", "sokongan": "Atas Pagar", "dun_kod": "N12"},
    {"no_kp": "920803085123", "nama": "MOHAMAD BIN ALI", "jantina": "L", "tahun_lahir": 1992, "dm": "PDM DUALOG", "lokaliti": "Kampung Dualog", "sokongan": "Putih", "dun_kod": "N12"},
    {"no_kp": "780615084567", "nama": "FATIMAH BINTI HASSAN", "jantina": "P", "tahun_lahir": 1978, "dm": "PDM DUALOG", "lokaliti": "Kampung Dualog", "sokongan": "Hitam", "dun_kod": "N12"},
    # DUN N13 Pantai Dalit
    {"no_kp": "950101089012", "nama": "AZMAN BIN OTHMAN", "jantina": "L", "tahun_lahir": 1995, "dm": "PDM DALIT", "lokaliti": "Kampung Dalit", "sokongan": "Atas Pagar", "dun_kod": "N13"},
    {"no_kp": "881220087654", "nama": "NORMAH BINTI YUSOF", "jantina": "P", "tahun_lahir": 1988, "dm": "PDM DALIT", "lokaliti": "Kampung Dalit", "sokongan": "Putih", "dun_kod": "N13"},
    # DUN N14 Tamparuli
    {"no_kp": "700315086789", "nama": "RAMLI BIN KAMARUDIN", "jantina": "L", "tahun_lahir": 1970, "dm": "PDM TAMPARULI", "lokaliti": "Kampung Tamparuli", "sokongan": "Tidak Kenal", "dun_kod": "N14"},
    {"no_kp": "930820084321", "nama": "ZAINAB BINTI AHMAD", "jantina": "P", "tahun_lahir": 1993, "dm": "PDM TAMPARULI", "lokaliti": "Kampung Tamparuli", "sokongan": "Putih", "dun_kod": "N14"},
    # DUN N15 Kiulu
    {"no_kp": "650101083210", "nama": "JAMAL BIN BASRI", "jantina": "L", "tahun_lahir": 1965, "dm": "PDM KIULU", "lokaliti": "Kampung Kiulu", "sokongan": "Atas Pagar", "dun_kod": "N15"},
    {"no_kp": "970512088765", "nama": "ROSNANI BINTI ABU", "jantina": "P", "tahun_lahir": 1997, "dm": "PDM KIULU", "lokaliti": "Kampung Kiulu", "sokongan": "Putih", "dun_kod": "N15"},
]

def seed_database():
    # Pastikan semua jadual wujud sebelum seed
    init_db()
    
    db = get_db()
    cursor = db.cursor()
    
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
    
    # Ambil ID untuk setiap DUN yang dirujuk dalam sample data
    cursor.execute("SELECT id, kod FROM dun")
    dun_rows = cursor.fetchall()
    dun_id_map = {row["kod"]: row["id"] for row in dun_rows}
    
    # Daftar PDM & Kampung untuk sample data setiap DUN
    pdm_map = {
        "PDM BINGOLON":  ("Kampung Bingolon", "N12"),
        "PDM DUALOG":    ("Kampung Dualog", "N12"),
        "PDM DALIT":     ("Kampung Dalit", "N13"),
        "PDM TAMPARULI": ("Kampung Tamparuli", "N14"),
        "PDM KIULU":     ("Kampung Kiulu", "N15"),
    }
    pdm_ids = {}
    kampung_ids = {}
    for pdm_nama, (kampung_nama, dun_kod) in pdm_map.items():
        dun_id = dun_id_map.get(dun_kod)
        if not dun_id:
            continue
        # Daftar PDM
        cursor.execute("SELECT id FROM pdm WHERE nama = ?", (pdm_nama,))
        row = cursor.fetchone()
        if row:
            pdm_ids[pdm_nama] = row[0]
        else:
            cursor.execute(
                "INSERT INTO pdm (dun_id, nama, keterangan, dicipta_pada) VALUES (?, ?, ?, ?)",
                (dun_id, pdm_nama, f"{pdm_nama} - DUN {dun_kod}", now)
            )
            pdm_ids[pdm_nama] = cursor.lastrowid
        # Daftar kampung
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
    print(f"✅ Seed data PDM & Kampung untuk P170 Tuaran telah dimasukkan")
    
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
        # Cuba cari FK
        cursor.execute("SELECT id FROM parlimen WHERE kod = 'P170'")
        parlimen_row = cursor.fetchone()
        parlimen_id = parlimen_row[0] if parlimen_row else None
        
        cursor.execute("SELECT id FROM dun WHERE kod = ?", (data["dun_kod"],))
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