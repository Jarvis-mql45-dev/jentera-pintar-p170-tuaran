"""
Migrate data pengundi dari database tempatan ke Render backend.
Guna: python migrate_to_render.py
"""
import sqlite3
import requests
import json
import os
import sys

BACKEND_URL = "https://jenterapintar-backend.onrender.com"
USERNAME = "admin"
PASSWORD = "admin123"
BATCH_SIZE = 50

def login():
    resp = requests.post(f"{BACKEND_URL}/api/login", 
                         json={"username": USERNAME, "kata_laluan": PASSWORD},
                         timeout=30)
    if resp.status_code != 200:
        print(f"❌ Login gagal: {resp.text}")
        return None
    data = resp.json()
    print(f"✅ Login berjaya sebagai: {data['user']['nama_penuh']} ({data['user']['peranan']})")
    return data["access_token"]

def main():
    print("=" * 60)
    print("  📤 MIGRATE DATA KE RENDER BACKEND")
    print("  URL:", BACKEND_URL)
    print("=" * 60)
    
    # Login
    token = login()
    if not token:
        return
    
    # Baca dari database tempatan
    db_path = os.path.join(os.path.dirname(__file__), "pengundi.db")
    if not os.path.exists(db_path):
        print(f"❌ Database tidak dijumpai: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Count total
    cursor.execute("SELECT COUNT(*) FROM pengundi")
    total = cursor.fetchone()[0]
    print(f"\n📊 Database tempatan: {total} rekod pengundi")
    
    if total == 0:
        print("⚠️  Tiada data untuk dimigrate!")
        return
    
    # Baca semua data
    cursor.execute("""
        SELECT no_kp, nama_penuh, jantina, tahun_lahir, dm, lokaliti, 
               no_telefon, status_sokongan, status_fizikal, adalah_pemilik_apps, 
               status_rekod, sumber_pdm
        FROM pengundi ORDER BY id
    """)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    # Buat fail Excel dalam format yang betul untuk import
    print("\n📝 Menyediakan data untuk import...")
    
    import pandas as pd
    from io import BytesIO
    
    # Convert to DataFrame with correct columns for import
    import_data = []
    for r in rows:
        row_data = {
            'NO KP': r['no_kp'],
            'NAMA PENUH': r['nama_penuh'],
            'JANTINA': r['jantina'],
            'TAHUN LAHIR': r['tahun_lahir'],
            'DM': r['dm'],
            'LOKALITI': r['lokaliti'],
            'NO TELEFON': r['no_telefon'],
            'PUTIH': 1 if r['status_sokongan'] == 'Putih' else 0,
            'ATAS PAGAR': 1 if r['status_sokongan'] == 'Atas Pagar' else 0,
            'HITAM': 1 if r['status_sokongan'] == 'Hitam' else 0,
            'TAK KENAL': 1 if r['status_sokongan'] == 'Tidak Kenal' else 0,
            'X DUNIA': 1 if r['status_fizikal'] == 'Meninggal Dunia' else 0,
        }
        import_data.append(row_data)
    
    df = pd.DataFrame(import_data)
    
    # Simpan ke Excel sementara
    temp_excel = os.path.join(os.path.dirname(__file__), "_temp_import.xlsx")
    df.to_excel(temp_excel, index=False)
    print(f"✅ Fail Excel sementara dicipta dengan {len(df)} rekod")
    
    # Upload ke Render
    print("\n📤 Mengupload ke Render...")
    headers = {"Authorization": f"Bearer {token}"}
    
    with open(temp_excel, "rb") as f:
        files = {"file": ("import_data.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        resp = requests.post(f"{BACKEND_URL}/api/pengundi/import-excel", 
                            headers=headers, files=files, timeout=300)
    
    # Padam fail sementara
    try:
        os.unlink(temp_excel)
    except:
        pass
    
    if resp.status_code == 200:
        result = resp.json()
        print(f"\n✅ IMPORT BERJAYA!")
        print(f"   Berjaya: {result['berjaya']}")
        print(f"   Gagal: {result['gagal']}")
        print(f"   Jumlah: {result['jumlah']}")
        
        if result['gagal'] > 0 and result.get('errors'):
            print(f"\n⚠️  Ralat (5 pertama):")
            for err in result['errors'][:5]:
                print(f"   - {err}")
        
        # Approve semua rekod
        print(f"\n🔄 Meluluskan {result['berjaya']} rekod...")
        queue_resp = requests.get(f"{BACKEND_URL}/api/approval-queue?per_page=200", 
                                 headers=headers, timeout=30)
        if queue_resp.status_code == 200:
            queue = queue_resp.json()
            approved = 0
            for item in queue.get('data', []):
                rid = item['id']
                apr_resp = requests.post(f"{BACKEND_URL}/api/approval-queue/{rid}/lulus", 
                                        headers=headers, timeout=30)
                if apr_resp.status_code == 200:
                    approved += 1
            print(f"✅ {approved} rekod telah diluluskan!")
    else:
        print(f"\n❌ Import gagal: {resp.text[:300]}")

if __name__ == "__main__":
    main()