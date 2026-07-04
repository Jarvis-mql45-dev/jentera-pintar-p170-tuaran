"""Script muktamad: padam terus 12 rekod PDM menggunakan endpoint DELETE baru"""
import requests
import time

BASE = "https://jenterapintar-backend.onrender.com"

# Login
print("=== PADAM TERUS REKOD PDM ===")
r = requests.post(f"{BASE}/api/login", json={"username":"admin","kata_laluan":"admin123"}, timeout=30)
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Cari rekod PDM
semua = []
page = 1
total_pages = 1
while page <= total_pages:
    r = requests.get(f"{BASE}/api/pengundi", headers=headers, params={"page": page, "per_page": 100}, timeout=30)
    data = r.json()
    total_pages = data.get("total_pages", 1)
    for p in data.get("data", []):
        dm = (p.get("dm") or "").strip()
        if dm.upper().startswith("PDM "):
            semua.append(p)
    page += 1

print(f"Dijumpai {len(semua)} rekod PDM untuk dipadam:")
for p in semua:
    print(f"  ID {p['id']:>3}: {p.get('nama_penuh','?'):30s} DM: {p.get('dm','?'):20s} {p.get('status_sokongan','?'):12s}")

if not semua:
    print("Tiada rekod PDM. Sistem sudah bersih!")
else:
    # Test DELETE endpoint dulu pada rekod pertama
    print(f"\n=== TEST DELETE endpoint pada ID {semua[0]['id']} ===")
    r = requests.delete(f"{BASE}/api/pengundi/{semua[0]['id']}", headers=headers, timeout=30)
    print(f"Status: {r.status_code}, Response: {r.text[:200]}")
    
    if r.status_code == 200:
        print("✓ DELETE endpoint berfungsi! Meneruskan cleanup...")
        semua = semua[1:]  # skip yang dah dipadam
    else:
        print("DELETE endpoint mungkin belum deploy. Tunggu Render deploy...")
        print("Mencuba semula dalam 30 saat...")
        time.sleep(30)
        r = requests.delete(f"{BASE}/api/pengundi/{semua[0]['id']}", headers=headers, timeout=30)
        print(f"Status: {r.status_code}, Response: {r.text[:200]}")

# Padam semua PDM
if semua:
    berjaya = 0
    gagal = 0
    print(f"\n=== Padam {len(semua)} rekod PDM ===")
    for i, p in enumerate(semua, 1):
        r = requests.delete(f"{BASE}/api/pengundi/{p['id']}", headers=headers, timeout=30)
        if r.status_code == 200:
            berjaya += 1
            print(f"  {i}. ✓ Padam ID {p['id']}: {p.get('nama_penuh','?'):30s}")
        else:
            gagal += 1
            print(f"  {i}. ✗ Gagal ID {p['id']}: {r.status_code}")
    print(f"\nBerjaya: {berjaya}, Gagal: {gagal}")

# Verifikasi akhir
print("\n=== VERIFIKASI AKHIR ===")

# Semak dropdown PDM
r = requests.get(f"{BASE}/api/pdm", headers=headers, timeout=30)
pdms = r.json()
pdm_palsu = [p for p in pdms if p.upper().startswith("PDM ") or p == ""]
print(f"Dropdown PDM: {len(pdms)} pilihan")
print(f"  PDM palsu: {'TIADA ✅' if not pdm_palsu else str(pdm_palsu) + ' ⚠'}")
for p in pdms:
    print(f"    - {repr(p)}")

# Semak dashboard
r = requests.get(f"{BASE}/api/dashboard", headers=headers, timeout=30)
d = r.json()
print(f"\nDashboard:")
print(f"  Jumlah pengundi: {d.get('jumlah_pengundi', '?')}")
sokongan = d.get('sokongan', {})
print(f"  Status sokongan: {sokongan}")
if len(sokongan) <= 1:
    print("  ✅ Bersih - tiada data sokongan PDM!")
else:
    print("  ⚠ Masih ada status sokongan")

# Semak rekod PDM dalam sistem
r = requests.get(f"{BASE}/api/pengundi", headers=headers, params={"page": 1, "per_page": 200}, timeout=60)
masih_ada = [p for p in r.json()["data"] if (p.get("dm") or "").strip().upper().startswith("PDM ")]
print(f"\nRekod PDM dalam sistem: {len(masih_ada)}")
if masih_ada:
    print("  ⚠ Masih ada rekod PDM!")
else:
    print("  ✅ Tiada langsung!")

print("\n=== SELESAI! ===")