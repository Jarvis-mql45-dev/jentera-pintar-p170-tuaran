"""
Import data Excel ke backend Render untuk JenteraPintar N05 Matunggong.
Guna: python import_to_render.py
"""
import requests
import json
import os
import glob

BACKEND_URL = "https://jenterapintar-backend.onrender.com"
USERNAME = "admin"
PASSWORD = "admin123"

def login():
    """Login dan dapatkan token."""
    resp = requests.post(f"{BACKEND_URL}/api/login", 
                         json={"username": USERNAME, "kata_laluan": PASSWORD},
                         timeout=30)
    if resp.status_code != 200:
        print(f"❌ Login gagal: {resp.text}")
        return None
    data = resp.json()
    print(f"✅ Login berjaya sebagai: {data['user']['nama_penuh']} ({data['user']['peranan']})")
    return data["access_token"]

def import_excel(filepath, token):
    """Import fail Excel ke sistem."""
    headers = {"Authorization": f"Bearer {token}"}
    
    with open(filepath, "rb") as f:
        files = {"file": (os.path.basename(filepath), f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        resp = requests.post(f"{BACKEND_URL}/api/pengundi/import-excel", 
                            headers=headers, files=files, timeout=120)
    
    if resp.status_code == 200:
        result = resp.json()
        print(f"✅ {os.path.basename(filepath)}: {result['berjaya']} berjaya, {result['gagal']} gagal (dari {result['jumlah']} rekod)")
        if result['gagal'] > 0 and result.get('errors'):
            for err in result['errors'][:5]:
                print(f"   ⚠️  {err}")
        return result
    else:
        print(f"❌ {os.path.basename(filepath)}: Gagal - {resp.text[:200]}")
        return None

def main():
    print("=" * 60)
    print("  📤 IMPORT DATA KE RENDER BACKEND")
    print("  URL:", BACKEND_URL)
    print("=" * 60)
    
    # Login
    token = login()
    if not token:
        return
    
    print()
    
    # Cari fail Excel dalam projek
    excel_files = []
    
    # PDM Excel files
    pdm_dir = os.path.join(os.path.dirname(__file__), "DUN N05 MATUNGGUNG")
    if os.path.exists(pdm_dir):
        for pdm_folder in sorted(os.listdir(pdm_dir)):
            pdm_path = os.path.join(pdm_dir, pdm_folder)
            if os.path.isdir(pdm_path):
                for f in os.listdir(pdm_path):
                    if f.endswith('.xlsx'):
                        excel_files.append(os.path.join(pdm_path, f))
    
    # Dashboard Excel
    dashboard_path = os.path.join(pdm_dir, "DASHBOARD N05 MATUNGGUNG.xlsx")
    if os.path.exists(dashboard_path):
        excel_files.insert(0, dashboard_path)  # Import dashboard first
    
    if not excel_files:
        print("⚠️  Tiada fail Excel dijumpai!")
        return
    
    print(f"Dijumpai {len(excel_files)} fail Excel:")
    for f in excel_files:
        print(f"  📄 {os.path.basename(f)}")
    print()
    
    # Import each file
    total_berjaya = 0
    total_gagal = 0
    
    for filepath in excel_files:
        result = import_excel(filepath, token)
        if result:
            total_berjaya += result['berjaya']
            total_gagal += result['gagal']
    
    print()
    print("=" * 60)
    print(f"  📊 RINGKASAN IMPORT:")
    print(f"     ✅ Berjaya: {total_berjaya}")
    print(f"     ❌ Gagal: {total_gagal}")
    print(f"     📈 Jumlah: {total_berjaya + total_gagal}")
    print("=" * 60)
    
    # Approve all pending records
    if total_berjaya > 0:
        print()
        print("  🔄 Meluluskan semua rekod yang menunggu...")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get approval queue
        resp = requests.get(f"{BACKEND_URL}/api/approval-queue?per_page=100", headers=headers, timeout=30)
        if resp.status_code == 200:
            queue = resp.json()
            approved = 0
            for item in queue.get('data', []):
                rid = item['id']
                resp2 = requests.post(f"{BACKEND_URL}/api/approval-queue/{rid}/lulus", headers=headers, timeout=30)
                if resp2.status_code == 200:
                    approved += 1
            
            if approved > 0:
                print(f"  ✅ {approved} rekod telah diluluskan!")
            else:
                print(f"  ℹ️  Tiada rekod untuk diluluskan.")

if __name__ == "__main__":
    main()