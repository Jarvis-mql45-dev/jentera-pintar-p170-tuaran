"""
Script pembersihan data PDM (mock data) dari Live Render Backend.
Menggunakan API endpoints yang sedia ada:
1. POST /api/login - login admin dapat token
2. GET /api/pengundi - cari semua pengundi dengan dm LIKE 'PDM%'
3. PUT /api/pengundi/{id} - update status_rekod ke 'Dibuang'

Cara guna:
   python cleanup_pdm_data.py
"""

import requests
import json
import sys

BASE_URL = "https://jenterapintar-backend.onrender.com"
LOGIN_URL = f"{BASE_URL}/api/login"
PENGUNDI_URL = f"{BASE_URL}/api/pengundi"

# ===== KREDENSIAL ADMIN =====
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"  # Ganti jika berbeza di production


def login():
    """Login ke API dan dapatkan token JWT."""
    print(f"[1/4] Log masuk ke {LOGIN_URL} ...")
    resp = requests.post(LOGIN_URL, json={
        "username": ADMIN_USERNAME,
        "kata_laluan": ADMIN_PASSWORD
    }, timeout=30)

    if resp.status_code != 200:
        print(f"✗ Gagal login! Status: {resp.status_code}")
        print(f"  Response: {resp.text}")
        sys.exit(1)

    data = resp.json()
    token = data.get("access_token")
    if not token:
        print(f"✗ Tiada access_token dalam response!")
        print(f"  Response: {json.dumps(data, indent=2)}")
        sys.exit(1)

    print(f"✓ Login berjaya. Token: {token[:50]}...")
    return token


def cari_pengundi_pdm(token):
    """Cari semua pengundi yang dm bermula dengan 'PDM '."""
    headers = {"Authorization": f"Bearer {token}"}

    # Kita kena loop through pages untuk dapat semua
    semua_pdm = []
    page = 1
    total_pages = 1

    while page <= total_pages:
        print(f"  Memuat halaman {page}...")
        resp = requests.get(
            PENGUNDI_URL,
            headers=headers,
            params={"page": page, "per_page": 100},
            timeout=30
        )

        if resp.status_code != 200:
            print(f"✗ Gagal dapat data pengundi! Status: {resp.status_code}")
            print(f"  Response: {resp.text}")
            sys.exit(1)

        data = resp.json()
        total_pages = data.get("total_pages", 1)
        pengundi_list = data.get("data", [])

        for p in pengundi_list:
            dm = (p.get("dm") or "").strip()
            lokaliti = (p.get("lokaliti") or "").strip()
            sumber_pdm = (p.get("sumber_pdm") or "").strip()

            # Cari yang dm/lokaliti/sumber_pdm bermula dengan PDM
            if (dm.upper().startswith("PDM ") or
                lokaliti.upper().startswith("PDM ") or
                sumber_pdm.upper().startswith("PDM ")):
                semua_pdm.append(p)

        page += 1

    print(f"\n✓ Dijumpai {len(semua_pdm)} rekod PDM dalam sistem.")
    return semua_pdm


def padam_pdm_records(token, rekod_list, kaedah="fizikal"):
    """Proses rekod PDM untuk dibuang dari statistik.

    Parameters:
        kaedah: 'fizikal' - set status_fizikal='Mati' (disokong oleh API)
                'rekod'  - set status_rekod='Dibuang' (tidak disokong, tapi cuba)
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    berjaya = 0
    gagal = 0

    if kaedah == "fizikal":
        field_name = "status_fizikal"
        field_value = "Mati"
        print(f"\n[3/4] Menukar status_fizikal ke 'Mati' untuk {len(rekod_list)} rekod PDM...")
    else:
        field_name = "status_rekod"
        field_value = "Dibuang"
        print(f"\n[3/4] Menukar status_rekod ke 'Dibuang' untuk {len(rekod_list)} rekod PDM...")

    for i, p in enumerate(rekod_list, 1):
        pid = p["id"]
        nama = p.get("nama_penuh", "?")
        dm = p.get("dm", "?")
        sokongan = p.get("status_sokongan", "?")

        update_url = f"{BASE_URL}/api/pengundi/{pid}"
        resp = requests.put(
            update_url,
            headers=headers,
            json={field_name: field_value},
            timeout=30
        )

        if resp.status_code == 200:
            berjaya += 1
            status = "✓"
        else:
            gagal += 1
            status = "✗"

        print(f"  {i}/{len(rekod_list)} {status} ID {pid}: {nama[:30]:30s} | DM: {dm:20s} | {sokongan:12s} -> {resp.status_code}")

    print(f"\n✓ Berjaya diproses: {berjaya}")
    if gagal > 0:
        print(f"✗ Gagal diproses: {gagal}")

    return berjaya, gagal


def pulihkan_pdm_records(token, rekod_list):
    """Pulihkan rekod PDM (untuk rollback) - tukar status_fizikal balik ke 'Hidup'."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    print(f"\n[Rollback] Memulihkan {len(rekod_list)} rekod PDM...")
    berjaya = 0
    gagal = 0

    for i, p in enumerate(rekod_list, 1):
        pid = p["id"]
        resp = requests.put(
            f"{BASE_URL}/api/pengundi/{pid}",
            headers=headers,
            json={"status_fizikal": "Hidup"},
            timeout=30
        )
        if resp.status_code == 200:
            berjaya += 1
        else:
            gagal += 1
        print(f"  {i}/{len(rekod_list)} ID {pid}: {'✓' if resp.status_code == 200 else '✗'} -> {resp.status_code}")

    print(f"\n  Pulih: {berjaya}, Gagal: {gagal}")
    return berjaya, gagal


def verify_live_count(token):
    """Semak dashboard count selepas cleanup."""
    headers = {"Authorization": f"Bearer {token}"}
    print(f"\n[4/4] Mengesahkan jumlah pengundi selepas cleanup...")

    dashboard_url = f"{BASE_URL}/api/dashboard"
    resp = requests.get(dashboard_url, headers=headers, timeout=30)

    if resp.status_code != 200:
        print(f"✗ Gagal dapat dashboard! Status: {resp.status_code}")
        return

    data = resp.json()
    print(f"\n{'='*60}")
    print(f"  DASHBOARD SELEPAS CLEANUP")
    print(f"{'='*60}")
    print(f"  Jumlah Pengundi:        {data.get('jumlah_pengundi', '?')}")
    print(f"  Status Sokongan:")
    sokongan = data.get('sokongan', {})
    for k, v in sokongan.items():
        print(f"    - {k}: {v}")
    print(f"  Jantina:")
    jantina = data.get('jantina', {})
    for k, v in jantina.items():
        print(f"    - {k}: {v}")
    print(f"{'='*60}")

    # Dapatkan juga jumlah pengundi aktif (Sah)
    resp2 = requests.get(
        PENGUNDI_URL,
        headers=headers,
        params={"page": 1, "per_page": 1},
        timeout=30
    )
    if resp2.status_code == 200:
        total_sah = resp2.json().get("total", 0)
        print(f"  Jumlah rekod dalam sistem: {total_sah}")

    print(f"{'='*60}")


def main():
    print("=" * 60)
    print("  CLEANUP DATA PDM - JenteraPintar N05 Matunggong")
    print("=" * 60)

    # Auto-confirm jika --force diberikan
    auto_confirm = "--force" in sys.argv or "-y" in sys.argv

    # Step 1: Login
    token = login()

    # Step 2: Cari semua rekod PDM
    rekod_pdm = cari_pengundi_pdm(token)

    if not rekod_pdm:
        print("\n✓ Tiada rekod PDM ditemui. Sistem sudah bersih!")
        verify_live_count(token)
        return

    # Step 3: Papar rekod yang akan diproses
    print("\n  Rekod PDM yang akan diproses:")
    print(f"  {'ID':>5} {'NAMA':<35} {'DM':<25} {'SOKONGAN':<15}")
    print(f"  {'-'*5} {'-'*35} {'-'*25} {'-'*15}")
    for p in rekod_pdm:
        print(f"  {p['id']:>5} {(p.get('nama_penuh') or '?'):<35} {(p.get('dm') or '?'):<25} {(p.get('status_sokongan') or '?'):<15}")
    print()

    # Minta pengesahan (kecuali auto-confirm)
    if not auto_confirm:
        print("  >> Tindakan: Semua rekod di atas akan ditukar status_fizikal ke 'Mati'.")
        print("  >> Ini akan mengeluarkan mereka dari statistik dashboard.")
        print("  >> (Nota: status_rekod tidak wujud dalam model API PUT, jadi guna status_fizikal)")
        confirm = input("  >> Teruskan? (y/N): ").strip().lower()
        if confirm != 'y':
            print("  ✗ Dibatalkan oleh pengguna.")
            return
    else:
        print("  >> Auto-confirm: Meneruskan pembersihan...")

    # Cuba kaedah 1: status_fizikal = 'Mati' (pasti berfungsi)
    print("\n  ┌─ KAEDAH 1: status_fizikal = 'Mati' ─────────────────┐")
    print("  │ Field ini ada dalam PengundiUpdate model API.       │")
    print("  │ Dashboard filter: status_fizikal = 'Hidup'          │")
    print("  └─────────────────────────────────────────────────────┘")
    berjaya1, gagal1 = padam_pdm_records(token, rekod_pdm, kaedah="fizikal")

    # Cuba kaedah 2: status_rekod = 'Dibuang' (mungkin tidak berfungsi)
    print("\n  ┌─ KAEDAH 2: status_rekod = 'Dibuang' ────────────────┐")
    print("  │ Field ini TIDAK dalam PengundiUpdate model API.     │")
    print("  │ Mungkin diabaikan oleh PUT.                         │")
    print("  └─────────────────────────────────────────────────────┘")
    # Buat salinan token baru kerana token mungkin masih sama
    berjaya2, gagal2 = padam_pdm_records(token, rekod_pdm, kaedah="rekod")

    # Step 4: Verify
    verify_live_count(token)

    total_berjaya = berjaya1 + berjaya2
    total_gagal = gagal1 + gagal2
    print(f"\n  ✓ SELESAI!")
    print(f"    Kaedah 1 (status_fizikal): {berjaya1} berjaya, {gagal1} gagal")
    if berjaya2 > 0:
        print(f"    Kaedah 2 (status_rekod):  {berjaya2} berjaya, {gagal2} gagal")
    print(f"    Jumlah: {total_berjaya} rekod PDM telah dibersihkan.")
    if total_gagal > 0:
        print(f"  ⚠ {total_gagal} rekod gagal diproses. Sila semak semula.")


if __name__ == "__main__":
    main()
