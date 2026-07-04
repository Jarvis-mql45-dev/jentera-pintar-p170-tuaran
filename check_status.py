"""Semak status backend selepas cleanup PDM"""
import requests

BASE = "https://jenterapintar-backend.onrender.com"

# 1. Semak root
print("=== STATUS BACKEND ===")
r = requests.get(f"{BASE}/", timeout=30)
print(f"Root API: {r.status_code} - {r.json().get('status', '?')}")

# 2. Login
r = requests.post(f"{BASE}/api/login", json={"username":"admin","kata_laluan":"admin123"}, timeout=30)
if r.status_code != 200:
    print(f"GAGAL LOGIN: {r.status_code} - {r.text[:200]}")
    exit()

token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print("Login: OK")

# 3. Dashboard
r = requests.get(f"{BASE}/api/dashboard", headers=headers, timeout=30)
if r.status_code == 200:
    d = r.json()
    print(f"\n=== DASHBOARD ===")
    print(f"Jumlah Pengundi: {d.get('jumlah_pengundi', '?')}")
    print(f"Status Sokongan: {d.get('sokongan', {})}")
else:
    print(f"DASHBOARD ERROR: {r.status_code} - {r.text[:300]}")

# 4. Total rekod
r = requests.get(f"{BASE}/api/pengundi", headers=headers, params={"page":1,"per_page":1}, timeout=30)
if r.status_code == 200:
    print(f"Total rekod: {r.json().get('total', '?')}")
else:
    print(f"PENGUNDI LIST ERROR: {r.status_code} - {r.text[:300]}")

# 5. Dropdown PDM
r = requests.get(f"{BASE}/api/pdm", headers=headers, timeout=30)
if r.status_code == 200:
    pdms = r.json()
    print(f"Dropdown PDM: {pdms}")
    pdm_palsu = [p for p in pdms if p.upper().startswith("PDM ")]
    print(f"  PDM palsu: {len(pdm_palsu)}")
else:
    print(f"PDM LIST ERROR: {r.status_code} - {r.text[:300]}")

# 6. Cari rekod PDM
r = requests.get(f"{BASE}/api/pengundi", headers=headers, params={"page":1,"per_page":200}, timeout=60)
if r.status_code == 200:
    semua = r.json().get("data", [])
    pdm = [p for p in semua if (p.get("dm") or "").strip().upper().startswith("PDM ")]
    print(f"\nRekod PDM dalam sistem: {len(pdm)}")
    if pdm:
        for p in pdm:
            print(f"  ID {p['id']}: {p.get('nama_penuh','?'):30s} DM: {p.get('dm','?')}")
    else:
        print("  ✅ Tiada langsung!")

print("\n=== SELESAI ===")