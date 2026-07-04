"""
Script untuk PADAM TERUS data PDM mock dari Live Render Backend.
Tindakan: Kosongkan dm, lokaliti, status_sokongan untuk 12 rekod PDM.
Ini akan mengeluarkan mereka dari dropdown /api/pdm dan dashboard.

Cara guna:
   python hapus_pdm_terus.py
"""

import requests
import sys

BASE_URL = "https://jenterapintar-backend.onrender.com"
LOGIN_URL = f"{BASE_URL}/api/login"
PENGUNDI_URL = f"{BASE_URL}/api/pengundi"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


def login():
    print(f"[1/4] Log masuk...")
    resp = requests.post(LOGIN_URL, json={
        "username": ADMIN_USERNAME,
        "kata_laluan": ADMIN_PASSWORD
    }, timeout=30)

    if resp.status_code != 200:
        print(f"✗ Gagal login! Status: {resp.status_code}")
        print(f"  Response: {resp.text}")
        sys.exit(1)

    token = resp.json().get("access_token")
    print(f"✓ Login berjaya.")
    return token


def cari_rekod_pdm(token):
    """Cari semua pengundi yang dm bermula dengan 'PDM '."""
    headers = {"Authorization": f"Bearer {token}"}
    semua_pdm = []
    page = 1
    total_pages = 1

    while page <= total_pages:
        resp = requests.get(
            PENGUNDI_URL,
            headers=headers,
            params={"page": page, "per_page": 100},
            timeout=30
        )
        data = resp.json()
        total_pages = data.get("total_pages", 1)
        for p in data.get("data", []):
            dm = (p.get("dm") or "").strip()
            lokaliti = (p.get("lokaliti") or "").strip()
            sumber = (p.get("sumber_pdm") or "").strip()
            if (dm.upper().startswith("PDM ") or
                lokaliti.upper().startswith("PDM ") or
                sumber.upper().startswith("PDM ")):
                semua_pdm.append(p)
        page += 1

    print(f"[2/4] Dijumpai {len(semua_pdm)} rekod PDM dalam sistem.")
    return semua_pdm


def kosongkan_rekod(token, rekod_list):
    """Kosongkan dm, lokaliti, status_sokongan untuk rekod PDM."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    print(f"[3/4] Mengosongkan field untuk {len(rekod_list)} rekod PDM...")
    berjaya = 0
    gagal = 0

    for i, p in enumerate(rekod_list, 1):
        pid = p["id"]
        nama = p.get("nama_penuh", "?")
        dm = p.get("dm", "?")

        # Kosongkan dm, lokaliti, status_sokongan guna string kosong
        resp = requests.put(
            f"{BASE_URL}/api/pengundi/{pid}",
            headers=headers,
            json={
                "dm": "",
                "lokaliti": "",
                "status_sokongan": ""
            },
            timeout=30
        )

        if resp.status_code == 200:
            berjaya += 1
            status = "✓"
        else:
            gagal += 1
            status = "✗"

        print(f"  {i}/{len(rekod_list)} {status} ID {pid}: {nama[:30]:30s} | DM: {dm:20s} -> {resp.status_code}")

    print(f"\n✓ Berjaya: {berjaya}, ✗ Gagal: {gagal}")
    return berjaya, gagal


def verify_live_count(token):
    """Semak dashboard dan PDM list selepas cleanup."""
    headers = {"Authorization": f"Bearer {token}"}

    print(f"[4/4] Mengesahkan...")

    # Semak dashboard
    resp = requests.get(f"{BASE_URL}/api/dashboard", headers=headers, timeout=30)
    if resp.status_code == 200:
        data = resp.json()
        print(f"\n  DASHBOARD:")
        print(f"    Jumlah Pengundi: {data.get('jumlah_pengundi', '?')}")
        sokongan = data.get('sokongan', {})
        if len(sokongan) <= 1:
            print(f"    ✅ Status sokongan bersih dari PDM!")
        else:
            print(f"    ⚠ Status sokongan masih ada data: {sokongan}")

    # Semak dropdown PDM
    resp = requests.get(f"{BASE_URL}/api/pdm", headers=headers, timeout=30)
    if resp.status_code == 200:
        pdms = resp.json()
        pdm_palsu = [p for p in pdms if p.upper().startswith("PDM ")]
        print(f"\n  DROPDOWN PDM:")
        print(f"    Jumlah pilihan: {len(pdms)}")
        if pdm_palsu:
            print(f"    ⚠ Masih ada PDM palsu: {pdm_palsu}")
        else:
            print(f"    ✅ Tiada lagi PDM palsu dalam dropdown!")
        print(f"    Pilihan: {pdms}")
    else:
        print(f"    ✗ Gagal dapat PDM list")


def main():
    print("=" * 60)
    print("  HAPUS DATA PDM TERUS - JenteraPintar N05 Matunggong")
    print("=" * 60)

    auto = "--force" in sys.argv or "-y" in sys.argv

    token = login()
    rekod_pdm = cari_rekod_pdm(token)

    if not rekod_pdm:
        print("\n✓ Tiada rekod PDM ditemui. Sistem sudah bersih!")
        verify_live_count(token)
        return

    print(f"\n  Rekod yang akan dikosongkan field-nya:")
    for p in rekod_pdm:
        print(f"    ID {p['id']:>3}: {p.get('nama_penuh','?'):30s} | DM: {p.get('dm','?'):20s} | {p.get('status_sokongan','?'):12s}")

    if not auto:
        print(f"\n  >> Tindakan: dm, lokaliti, status_sokongan untuk {len(rekod_pdm)} rekod akan dikosongkan.")
        print(f"  >> Ini akan menghilangkan 'PDM ...' dari dropdown dan dashboard.")
        confirm = input("  >> Teruskan? (y/N): ").strip().lower()
        if confirm != "y":
            print("  ✗ Dibatalkan.")
            return
    else:
        print(f"\n  >> Auto-confirm: Meneruskan...")

    berjaya, gagal = kosongkan_rekod(token, rekod_pdm)
    verify_live_count(token)

    print(f"\n  {'='*60}")
    print(f"  SELESAI! {berjaya} rekod PDM telah dibersihkan.")
    if gagal > 0:
        print(f"  ⚠ {gagal} rekod gagal. Sila semak semula.")
    print(f"  {'='*60}")


if __name__ == "__main__":
    main()