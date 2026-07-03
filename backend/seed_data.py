"""
Seed data script untuk JenteraPintar N05 Matunggong.
Insert sample data pengundi untuk tujuan testing di Render.
Guna: python seed_data.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from database import get_db
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
    db = get_db()
    cursor = db.cursor()
    
    # Check if pengundi already have data
    cursor.execute("SELECT COUNT(*) FROM pengundi")
    count = cursor.fetchone()[0]
    
    if count > 0:
        print(f"✅ Database already has {count} records. Skipping seed.")
        db.close()
        return
    
    now = datetime.now().isoformat()
    inserted = 0
    
    for data in SAMPLE_DATA:
        cursor.execute("""
            INSERT INTO pengundi 
            (no_kp, nama_penuh, jantina, tahun_lahir, dm, lokaliti, 
             status_sokongan, status_fizikal, status_rekod, sumber_pdm, dicipta_pada)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["no_kp"], data["nama"], data["jantina"], data["tahun_lahir"],
            data["dm"], data["lokaliti"], data["sokongan"],
            "Hidup", "Sah", "Seed Data", now
        ))
        inserted += 1
    
    db.commit()
    db.close()
    print(f"✅ {inserted} sample records inserted successfully!")

if __name__ == "__main__":
    seed_database()