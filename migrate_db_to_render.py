"""
Migrate local pengundi.db ke Render Backend.
Pendekatan: export data ke Excel format yang betul, upload melalui API import-excel.
"""
import requests
import sqlite3
import os
import json

BACKEND_URL = "https://jenterapintar-backend.onrender.com"

def login():
    resp = requests.post(f"{BACKEND_URL}/api/login",
                         json={"username": "admin", "kata_laluan": "admin123"},
                         timeout=30)
    if resp.status_code != 200:
        print(f"❌ Login gagal: {resp.text}")
        return None
    data = resp.json()
    print(f"✅ Login berjaya: {data['user']['nama_penuh']} ({data['user']['peranan']})")
    return data["access_token"]

def main():
    print("=" * 60)
    print("  MIGRATE DATABASE TEMPATAN KE RENDER")
    print("=" * 60)

    # 1. Login
    token = login()
    if not token:
        return
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Baca data dari pengundi.db
    print("\n[1/3] Membaca data dari pengundi.db...")
    conn = sqlite3.connect("pengundi.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM pengundi ORDER BY id")
    rows = cur.fetchall()
    conn.close()
    print(f"  → {len(rows)} rekod dijumpai")

    # 3. Hantar data melalui API import-excel
    # Kita perlu create Excel dalam memory dengan format yang betul
    print("\n[2/3] Menyediakan data untuk import...")
    
    # Bina data untuk Excel
    import pandas as pd
    from io import BytesIO
    
    data_records = []
    for r in rows:
        r = dict(r)
        # Tentukan lajur sokongan (PUTIH/ATAS PAGAR/HITAM/TAK KENAL)
        putih = 0
        atas_pagar = 0
        hitam = 0
        tak_kenal = 0
        sok = r.get("status_sokongan")
        if sok == "Putih":
            putih = 1
        elif sok == "Atas Pagar":
            atas_pagar = 1
        elif sok == "Hitam":
            hitam = 1
        elif sok == "Tidak Kenal":
            tak_kenal = 1
        
        data_records.append({
            "NO KP": r.get("no_kp", ""),
            "NAMA PENUH": r.get("nama_penuh", ""),
            "JANTINA": r.get("jantina", ""),
            "TAHUN LAHIR": r.get("tahun_lahir", ""),
            "DM": r.get("dm", ""),
            "LOKALITI": r.get("lokaliti", ""),
            "NO TELEFON": r.get("no_telefon", ""),
            "PUTIH": putih,
            "ATAS PAGAR": atas_pagar,
            "HITAM": hitam,
            "TAK KENAL": tak_kenal,
            "X DUNIA": 1 if r.get("status_fizikal") == "Meninggal Dunia" else 0
        })
    
    df = pd.DataFrame(data_records)
    
    # Simpan ke BytesIO
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="Data Pengundi")
    output.seek(0)
    
    print(f"  → {len(data_records)} rekod sedia untuk import")
    
    # 4. Upload melalui API
    print("\n[3/3] Mengimport ke Render...")
    
    # Hantar dalam batch 1000 untuk elak timeout
    batch_size = 1000
    total_berjaya = 0
    total_gagal = 0
    
    for start in range(0, len(data_records), batch_size):
        batch_df = df.iloc[start:start+batch_size]
        batch_output = BytesIO()
        with pd.ExcelWriter(batch_output, engine='openpyxl') as writer:
            batch_df.to_excel(writer, index=False, sheet_name="Data Pengundi")
        batch_output.seek(0)
        
        files = {"file": ("batch_pengundi.xlsx", batch_output, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        resp = requests.post(
            f"{BACKEND_URL}/api/pengundi/import-excel",
            headers=headers,
            files=files,
            timeout=120
        )
        
        if resp.status_code == 200:
            result = resp.json()
            total_berjaya += result["berjaya"]
            total_gagal += result["gagal"]
            print(f"  Batch {start//batch_size + 1}: {result['berjaya']} berjaya, {result['gagal']} gagal")
            if result.get("errors"):
                for err in result["errors"][:3]:
                    print(f"    ⚠ {err}")
        else:
            print(f"  ❌ Batch gagal: {resp.status_code} - {resp.text[:200]}")
            total_gagal += len(batch_df)
    
    print(f"\n📊 RINGKASAN:")
    print(f"  ✅ Berjaya: {total_berjaya}")
    print(f"  ❌ Gagal: {total_gagal}")
    
    # 5. Approve all pending
    if total_berjaya > 0:
        print("\n🔄 Meluluskan semua rekod...")
        resp = requests.post(f"{BACKEND_URL}/api/pengundi/approve-all", headers=headers, timeout=30)
        if resp.status_code == 200:
            print(f"  ✅ {resp.json().get('jumlah', '?')} rekod diluluskan!")
        
        # Verify
        print("\n📋 VERIFIKASI:")
        resp = requests.get(f"{BACKEND_URL}/api/dashboard", headers=headers, timeout=30)
        if resp.status_code == 200:
            d = resp.json()
            print(f"  Dashboard: {d.get('jumlah_pengundi', '?')} pengundi")
            print(f"  Sokongan: {d.get('sokongan', {})}")
        
        resp = requests.get(f"{BACKEND_URL}/api/pdm", headers=headers, timeout=30)
        if resp.status_code == 200:
            pdms = resp.json()
            pdm_palsu = [p for p in pdms if p.upper().startswith("PDM ")]
            print(f"  Dropdown PDM: {len(pdms)} pilihan, PDM palsu: {len(pdm_palsu)}")
    
    print("\n" + "=" * 60)
    print("  SELESAI!")
    print("=" * 60)

if __name__ == "__main__":
    main()