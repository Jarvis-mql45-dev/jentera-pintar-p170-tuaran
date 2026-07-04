"""Test: semak PDM dropdown selepas deploy baru - filtered version"""
import requests
import time

BASE = "https://jenterapintar-backend.onrender.com"

r = requests.post(f"{BASE}/api/login", json={"username":"admin","kata_laluan":"admin123"}, timeout=30)
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

print("=== Test dropdown PDM ===")
for i in range(5):
    time.sleep(5)
    r = requests.get(f"{BASE}/api/pdm", headers=headers, timeout=30)
    pdms = r.json()
    pdm_palsu = [p for p in pdms if p.upper().startswith("PDM ")]
    print(f"Jumlah: {len(pdms)}, PDM palsu: {len(pdm_palsu)} - {pdms}")

print("\n=== Test rekod PDM yang masih aktif ===")
r = requests.get(f"{BASE}/api/pengundi", headers=headers, params={"page":1,"per_page":200}, timeout=60)
for p in r.json()["data"]:
    dm = (p.get("dm") or "").strip()
    if dm.upper().startswith("PDM "):
        print(f"  ID {p['id']}: dm={repr(p.get('dm'))} fizikal={repr(p.get('status_fizikal'))} rekod={repr(p.get('status_rekod'))}")