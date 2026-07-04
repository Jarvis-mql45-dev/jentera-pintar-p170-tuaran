from fastapi import FastAPI, Depends, HTTPException, status, Query, Request, UploadFile, File, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from database import get_db, init_db
from auth import (
    hash_kata_laluan, sahkan_kata_laluan, create_access_token,
    get_current_user, get_pengguna_dari_db
)
from config import settings
import sqlite3
import pandas as pd
import openpyxl
from io import BytesIO
import re
import json
import random
from datetime import datetime
import os

app = FastAPI(title="Sistem Pengurusan Pengundi DUN N05 Matunggong")

# CORS - guna config (production: only allowed origins, dev: semua)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dalam production mode, serve static files dari frontend/dist dan tiada source maps
if settings.PRODUCTION:
    dist_path = settings.STATIC_DIR
    if os.path.exists(dist_path):
        app.mount("/", StaticFiles(directory=dist_path, html=True), name="static")
        print(f"✅ Static files served from: {dist_path} (source maps: DISABLED)")


# ===== MODEL DATA =====
class LoginRequest(BaseModel):
    username: str
    kata_laluan: str


class PengundiCreate(BaseModel):
    no_kp: str
    nama_penuh: str
    jantina: Optional[str] = None
    tahun_lahir: Optional[int] = None
    dm: str
    lokaliti: Optional[str] = None
    no_telefon: Optional[str] = None
    status_sokongan: Optional[str] = None
    status_fizikal: Optional[str] = "Hidup"


class PengundiUpdate(BaseModel):
    nama_penuh: Optional[str] = None
    jantina: Optional[str] = None
    tahun_lahir: Optional[int] = None
    dm: Optional[str] = None
    lokaliti: Optional[str] = None
    no_telefon: Optional[str] = None
    status_sokongan: Optional[str] = None
    status_fizikal: Optional[str] = None
    adalah_pemilik_apps: Optional[bool] = None


class PenggunaCreate(BaseModel):
    username: str
    nama_penuh: str
    kata_laluan: str
    peranan: str = "Pemerhati"
    dm: Optional[str] = None


# ===== AUDIT TRAIL HELPER =====
def log_activity(request: Request, user: dict, tindakan: str, penerangan: str, no_kp_terlibat: str = None):
    """Log aktiviti pengguna ke dalam audit_logs untuk pematuhan PDPA."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO audit_logs (user_id, username, peranan, tindakan, penerangan, no_kp_terlibat, endpoint, ip_address, user_agent, dicipta_pada)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user.get("user_id"),
        user["username"],
        user["peranan"],
        tindakan,
        penerangan,
        no_kp_terlibat,
        request.url.path if hasattr(request, 'url') else None,
        request.client.host if request.client else None,
        request.headers.get("user-agent") if hasattr(request, 'headers') else None,
        datetime.now().isoformat()
    ))
    db.commit()
    db.close()


# ===== EVENT STARTUP =====
@app.on_event("startup")
def startup():
    init_db()
    
    # Seed admin user if not exists
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO users (username, nama_penuh, kata_laluan, peranan, dm, aktif, dicipta_pada) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("admin", "Admin Sistem", hash_kata_laluan("admin123"), "Admin", None, 1, datetime.now().isoformat())
        )
        cursor.execute(
            "INSERT INTO users (username, nama_penuh, kata_laluan, peranan, dm, aktif, dicipta_pada) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("petugas", "Petugas Padang", hash_kata_laluan("petugas123"), "Petugas Padang", None, 1, datetime.now().isoformat())
        )
        cursor.execute(
            "INSERT INTO users (username, nama_penuh, kata_laluan, peranan, dm, aktif, dicipta_pada) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("pemerhati", "Pemerhati", hash_kata_laluan("pemerhati123"), "Pemerhati", None, 1, datetime.now().isoformat())
        )
        db.commit()
        print("✅ Pengguna lalai telah dicipta: admin/admin123, petugas/petugas123, pemerhati/pemerhati123")
    
    # Seed sample pengundi data if database empty
    cursor.execute("SELECT COUNT(*) FROM pengundi")
    pengundi_count = cursor.fetchone()[0]
    if pengundi_count == 0:
        print("📦 Database pengundi kosong - memasukkan data sample...")
        try:
            from seed_data import seed_database
            seed_database()
            print("✅ Data sample pengundi berjaya dimasukkan!")
        except Exception as e:
            print(f"⚠️ Gagal seed data: {e}")
    else:
        print(f"✅ Database pengundi sudah mempunyai {pengundi_count} rekod")
    
    db.close()


# ===== FUNGSI CHECK PERANAN =====
def check_peranan(user: dict, peranan_dibenarkan: list):
    if user["peranan"] not in peranan_dibenarkan:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Akses ditolak. Peranan '{user['peranan']}' tidak dibenarkan."
        )


# ===== ENDPOINT LOGIN =====
@app.post("/api/login")
def login(req: LoginRequest):
    user = get_pengguna_dari_db(req.username)
    if not user:
        raise HTTPException(status_code=401, detail="Nama pengguna tidak wujud")

    if not sahkan_kata_laluan(req.kata_laluan, user["kata_laluan"]):
        raise HTTPException(status_code=401, detail="Kata laluan salah")

    token = create_access_token({
        "sub": user["username"],
        "peranan": user["peranan"],
        "user_id": user["id"]
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "nama_penuh": user["nama_penuh"],
            "peranan": user["peranan"],
            "dm": user["dm"]
        }
    }


# ===== ENDPOINT PENGUNDI =====

# Senarai PDM untuk dropdown
@app.get("/api/pdm")
def get_pdm_list(user=Depends(get_current_user)):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT DISTINCT dm FROM pengundi WHERE dm IS NOT NULL AND dm != '' AND status_fizikal = 'Hidup' AND status_rekod = 'Sah' ORDER BY dm")
    pdms = [row[0] for row in cursor.fetchall()]
    db.close()
    return pdms


# Dashboard stats
@app.get("/api/dashboard")
def get_dashboard(request: Request, dm: Optional[str] = None, user=Depends(get_current_user)):
    try:
        db = get_db()
        cursor = db.cursor()

        where = "WHERE status_fizikal = 'Hidup' AND status_rekod = 'Sah'"
        params = []
        if dm:
            where += " AND dm = ?"
            params.append(dm)
        
        THN_SEMASA = 2026

        # Jumlah pengundi
        cursor.execute(f"SELECT COUNT(*) FROM pengundi {where}", params)
        jumlah_pengundi = cursor.fetchone()[0]

        # Status sokongan
        cursor.execute(f"SELECT status_sokongan, COUNT(*) as jumlah FROM pengundi {where} GROUP BY status_sokongan ORDER BY jumlah DESC", params)
        sokongan = {}
        for row in cursor.fetchall():
            key = row["status_sokongan"] or "Tiada"
            sokongan[key] = row["jumlah"]

        # Jantina
        cursor.execute(f"SELECT jantina, COUNT(*) as jumlah FROM pengundi {where} GROUP BY jantina", params)
        jantina = {}
        for row in cursor.fetchall():
            key = row["jantina"] or "Tidak Diketahui"
            jantina[key] = row["jumlah"]

        # Status fizikal
        cursor.execute(f"SELECT status_fizikal, COUNT(*) as jumlah FROM pengundi {where} GROUP BY status_fizikal", params)
        fizikal = {}
        for row in cursor.fetchall():
            key = row["status_fizikal"] or "Hidup"
            fizikal[key] = row["jumlah"]

        # Pengundi mengikut lokaliti
        cursor.execute(f"SELECT lokaliti, COUNT(*) as jumlah FROM pengundi {where} GROUP BY lokaliti ORDER BY jumlah DESC LIMIT 10", params)
        lokaliti_data = []
        for row in cursor.fetchall():
            lokaliti_data.append({"nama": row["lokaliti"] or "Tiada", "jumlah": row["jumlah"]})

        # Klasifikasi Umur
        cursor.execute(f"""
            SELECT 
                CASE 
                    WHEN (tahun_lahir IS NULL) THEN 'Tidak Diketahui'
                    WHEN ({THN_SEMASA} - tahun_lahir) BETWEEN 18 AND 30 THEN 'Belia'
                    WHEN ({THN_SEMASA} - tahun_lahir) BETWEEN 31 AND 59 THEN 'Dewasa'
                    WHEN ({THN_SEMASA} - tahun_lahir) >= 60 THEN 'Warga Emas'
                    ELSE 'Lain-lain'
                END as klasifikasi,
                COUNT(*) as jumlah,
                SUM(CASE WHEN jantina = 'L' THEN 1 ELSE 0 END) as lelaki,
                SUM(CASE WHEN jantina = 'P' THEN 1 ELSE 0 END) as perempuan
            FROM pengundi {where}
            GROUP BY klasifikasi
        """, params)
        klasifikasi_umur = {}
        for row in cursor.fetchall():
            klasifikasi_umur[row["klasifikasi"]] = {
                "jumlah": row["jumlah"],
                "lelaki": row["lelaki"],
                "perempuan": row["perempuan"]
            }

        # Umur purata
        cursor.execute(f"SELECT AVG({THN_SEMASA} - tahun_lahir) FROM pengundi {where} AND tahun_lahir IS NOT NULL", params)
        row = cursor.fetchone()
        purata_umur = round(row[0], 1) if row and row[0] is not None else 0

        # Sokongan mengikut klasifikasi umur
        cursor.execute(f"""
            SELECT 
                CASE 
                    WHEN (tahun_lahir IS NULL) THEN 'Tidak Diketahui'
                    WHEN ({THN_SEMASA} - tahun_lahir) BETWEEN 18 AND 30 THEN 'Belia'
                    WHEN ({THN_SEMASA} - tahun_lahir) BETWEEN 31 AND 59 THEN 'Dewasa'
                    WHEN ({THN_SEMASA} - tahun_lahir) >= 60 THEN 'Warga Emas'
                    ELSE 'Lain-lain'
                END as klasifikasi,
                COALESCE(status_sokongan, 'Tiada') as sokongan,
                COUNT(*) as jumlah
            FROM pengundi {where}
            GROUP BY klasifikasi, sokongan
            ORDER BY klasifikasi, sokongan
        """, params)
        sokongan_ikut_umur = {}
        for row in cursor.fetchall():
            k = row["klasifikasi"]
            s = row["sokongan"]
            j = row["jumlah"]
            if k not in sokongan_ikut_umur:
                sokongan_ikut_umur[k] = {}
            sokongan_ikut_umur[k][s] = j

        db.close()

        return {
            "jumlah_pengundi": jumlah_pengundi,
            "sokongan": sokongan,
            "jantina": jantina,
            "fizikal": fizikal,
            "lokaliti_teratas": lokaliti_data,
            "klasifikasi_umur": klasifikasi_umur,
            "purata_umur": purata_umur,
            "sokongan_ikut_umur": sokongan_ikut_umur
        }
    except Exception as e:
        import traceback
        error_detail = f"{type(e).__name__}: {str(e)}"
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_detail)


# Senarai pengundi dengan carian dan tapisan
@app.get("/api/pengundi")
def get_pengundi(
    request: Request,
    page: int = 1,
    per_page: int = 50,
    search: Optional[str] = None,
    dm: Optional[str] = None,
    status_sokongan: Optional[str] = None,
    status_rekod: Optional[str] = None,
    user=Depends(get_current_user)
):
    db = get_db()
    cursor = db.cursor()

    where_parts = []
    params = []

    if search:
        where_parts.append("(no_kp LIKE ? OR nama_penuh LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])

    if dm:
        where_parts.append("dm = ?")
        params.append(dm)

    if status_sokongan:
        where_parts.append("status_sokongan = ?")
        params.append(status_sokongan)

    if status_rekod:
        where_parts.append("status_rekod = ?")
        params.append(status_rekod)

    where = ""
    if where_parts:
        where = "WHERE " + " AND ".join(where_parts)

    # Count total
    cursor.execute(f"SELECT COUNT(*) FROM pengundi {where}", params)
    total = cursor.fetchone()[0]

    # Get page data
    offset = (page - 1) * per_page
    cursor.execute(f"""
        SELECT id, no_kp, nama_penuh, jantina, tahun_lahir, dm, lokaliti,
               no_telefon, status_sokongan, status_fizikal, adalah_pemilik_apps, status_rekod, sumber_pdm
        FROM pengundi {where}
        ORDER BY id
        LIMIT ? OFFSET ?
    """, params + [per_page, offset])

    pengundi = [dict(row) for row in cursor.fetchall()]
    db.close()

    # Log aktiviti: carian atau senarai dilawati
    if search:
        log_activity(request, user, "Carian Pengundi", f"Carian: '{search}' (P: {total} keputusan)", no_kp_terlibat=search)
    else:
        log_activity(request, user, "Lihat Senarai Pengundi", f"Senarai pengundi (dm: {dm or 'Semua'}, ms: {page})")

    return {
        "data": pengundi,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": max(1, (total + per_page - 1) // per_page)
    }


# ===== ENDPOINT IMPORT EXCEL (Admin sahaja) =====

# Muat turun templat Excel kosong
@app.get("/api/pengundi/template")
def download_template(user=Depends(get_current_user)):
    check_peranan(user, ["Admin"])

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Data Pengundi"

    headers = ['NO KP', 'NAMA PENUH', 'JANTINA', 'TAHUN LAHIR', 'DM', 'LOKALITI',
               'NO TELEFON', 'PUTIH', 'ATAS PAGAR', 'HITAM', 'TAK KENAL', 'X DUNIA']
    ws.append(headers)

    # Style header row
    for cell in ws[1]:
        cell.font = openpyxl.styles.Font(bold=True)
        cell.alignment = openpyxl.styles.Alignment(horizontal='center')

    # Set column widths
    widths = [15, 35, 10, 12, 20, 25, 15, 8, 10, 8, 10, 10]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=TEMPLAT_IMPORT_PENGUNDI.xlsx"}
    )


# Import data dari Excel
@app.post("/api/pengundi/import-excel")
def import_excel(request: Request, file: UploadFile = File(...), user=Depends(get_current_user)):
    check_peranan(user, ["Admin"])

    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Sila muat naik fail Excel (.xlsx atau .xls)")

    try:
        contents = file.file.read()
        df = pd.read_excel(BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal membaca fail Excel: {str(e)}")

    # Normalise column names: uppercase, strip whitespace
    df.columns = [str(c).strip().upper() for c in df.columns]

    # Validate required columns
    required_cols = ['NO KP', 'NAMA PENUH', 'JANTINA', 'TAHUN LAHIR', 'DM', 'LOKALITI']
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Lajur wajib tidak dijumpai: {', '.join(missing)}. Lajur mesti termasuk: {', '.join(required_cols)}"
        )

    db = get_db()
    cursor = db.cursor()
    errors = []
    berjaya = 0

    insert_sql = """
        INSERT INTO pengundi
        (no_kp, nama_penuh, jantina, tahun_lahir, dm, lokaliti, no_telefon,
         status_sokongan, status_fizikal, adalah_pemilik_apps, status_rekod, sumber_pdm, dicipta_pada)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    now = datetime.now().isoformat()

    for idx, row in df.iterrows():
        try:
            # Process no_kp
            no_kp = row.get('NO KP')
            if pd.isna(no_kp) or not str(no_kp).strip():
                errors.append(f"Baris {idx+2}: No KP kosong")
                continue
            no_kp_str = str(no_kp).strip()
            # Remove dashes
            no_kp_str = no_kp_str.replace('-', '').replace(' ', '')
            # Take last 12 digits if longer
            digits_only = re.sub(r'\D', '', no_kp_str)
            if len(digits_only) >= 12:
                no_kp_str = digits_only[-12:]
            else:
                no_kp_str = digits_only

            # Process nama
            nama = row.get('NAMA PENUH')
            if pd.isna(nama) or not str(nama).strip():
                errors.append(f"Baris {idx+2}: Nama Penuh kosong")
                continue
            nama_str = str(nama).strip().upper()

            # Process jantina
            jantina_raw = row.get('JANTINA')
            jantina = None
            if pd.notna(jantina_raw):
                j = str(jantina_raw).strip().upper()
                if j in ['L', 'LELAKI', 'Lelaki']:
                    jantina = 'L'
                elif j in ['P', 'PEREMPUAN', 'Perempuan']:
                    jantina = 'P'

            # Process tahun_lahir
            tahun = row.get('TAHUN LAHIR')
            tahun_lahir = None
            if pd.notna(tahun):
                try:
                    tahun_lahir = int(float(str(tahun).strip()))
                except:
                    pass

            # Process DM
            dm = str(row.get('DM', '')).strip().upper() if pd.notna(row.get('DM')) else ''

            # Process lokaliti
            lokaliti = str(row.get('LOKALITI', '')).strip() if pd.notna(row.get('LOKALITI')) else None

            # Process no_telefon
            tel = row.get('NO TELEFON')
            no_telefon = str(tel).strip() if pd.notna(tel) else None

            # Process status sokongan
            status_sokongan = None
            for col_check, val in [('PUTIH', 'Putih'), ('ATAS PAGAR', 'Atas Pagar'),
                                    ('HITAM', 'Hitam'), ('TAK KENAL', 'Tidak Kenal'),
                                    ('P', 'Putih'), ('AP', 'Atas Pagar'), ('H', 'Hitam')]:
                if col_check in df.columns:
                    cell = row.get(col_check)
                    if pd.notna(cell):
                        cell_str = str(cell).strip()
                        if cell_str in ['1', '1.0', '1.00', 'TRUE', 'true', 'Y', 'y']:
                            status_sokongan = val
                            break

            # Process status fizikal
            status_fizikal = 'Hidup'
            for col_check in ['X DUNIA', 'MENINGGAL', 'MATI']:
                if col_check in df.columns:
                    cell = row.get(col_check)
                    if pd.notna(cell):
                        cell_str = str(cell).strip()
                        if cell_str in ['1', '1.0', '1.00', 'TRUE', 'true', 'Y', 'y']:
                            status_fizikal = 'Meninggal Dunia'
                            break

            values = (
                no_kp_str, nama_str, jantina, tahun_lahir,
                dm, lokaliti, no_telefon,
                status_sokongan, status_fizikal, 0,
                'Menunggu_Kelulusan', 'Import Excel', now
            )
            cursor.execute(insert_sql, values)
            berjaya += 1

        except Exception as e:
            errors.append(f"Baris {idx+2}: {str(e)}")

    db.commit()
    db.close()

    log_activity(request, user, "Import Excel",
                 f"Import Excel: {berjaya} berjaya, {len(errors)} gagal | Fail: {file.filename}")

    return {
        "berjaya": berjaya,
        "gagal": len(errors),
        "jumlah": berjaya + len(errors),
        "errors": errors[:20]  # Max 20 errors to avoid huge response
    }


# Dapatkan pengundi by ID
@app.get("/api/pengundi/{pengundi_id}")
def get_pengundi_by_id(request: Request, pengundi_id: int, user=Depends(get_current_user)):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM pengundi WHERE id = ?", (pengundi_id,))
    p = cursor.fetchone()
    db.close()
    if not p:
        raise HTTPException(status_code=404, detail="Pengundi tidak ditemui")
    
    # Log aktiviti: lihat detail pengundi
    log_activity(request, user, "Lihat Detail Pengundi", f"Lihat detail ID {pengundi_id}: {p['nama_penuh']}", no_kp_terlibat=p['no_kp'])
    
    return dict(p)


# Tambah pengundi baru (Petugas Padang - status_rekod = Menunggu_Kelulusan)
@app.post("/api/pengundi")
def create_pengundi(request: Request, data: PengundiCreate, user=Depends(get_current_user)):
    check_peranan(user, ["Admin", "Petugas Padang"])

    status_rekod = "Menunggu_Kelulusan" if user["peranan"] == "Petugas Padang" else "Sah"

    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO pengundi
        (no_kp, nama_penuh, jantina, tahun_lahir, dm, lokaliti, no_telefon,
         status_sokongan, status_fizikal, adalah_pemilik_apps, status_rekod, sumber_pdm, dicipta_pada)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.no_kp, data.nama_penuh, data.jantina, data.tahun_lahir,
        data.dm, data.lokaliti, data.no_telefon,
        data.status_sokongan, data.status_fizikal, 0,
        status_rekod, f"Didaftar oleh {user['username']}", datetime.now().isoformat()
    ))
    db.commit()
    new_id = cursor.lastrowid
    db.close()

    # Log aktiviti
    log_activity(request, user, "Tambah Pengundi", 
                 f"Tambah pengundi baru: {data.nama_penuh} (KP: {data.no_kp}, PDM: {data.dm}, status: {status_rekod})",
                 no_kp_terlibat=data.no_kp)

    return {"message": "Pengundi berjaya didaftarkan", "id": new_id, "status_rekod": status_rekod}


# Kemaskini pengundi
@app.put("/api/pengundi/{pengundi_id}")
def update_pengundi(request: Request, pengundi_id: int, data: PengundiUpdate, user=Depends(get_current_user)):
    check_peranan(user, ["Admin", "Petugas Padang"])

    db = get_db()
    cursor = db.cursor()

    # Get existing
    cursor.execute("SELECT * FROM pengundi WHERE id = ?", (pengundi_id,))
    existing = cursor.fetchone()
    if not existing:
        db.close()
        raise HTTPException(status_code=404, detail="Pengundi tidak ditemui")

    # Build update
    update_fields = {}
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            update_fields[field] = value

    if not update_fields:
        db.close()
        return {"message": "Tiada perubahan dibuat"}

    # If Petugas Padang, set status to Menunggu_Kelulusan
    if user["peranan"] == "Petugas Padang":
        update_fields["status_rekod"] = "Menunggu_Kelulusan"

    set_clause = ", ".join([f"{k} = ?" for k in update_fields.keys()])
    values = list(update_fields.values()) + [pengundi_id]

    cursor.execute(f"UPDATE pengundi SET {set_clause} WHERE id = ?", values)
    db.commit()
    db.close()

    # Log aktiviti
    changed_fields = ', '.join(update_fields.keys())
    log_activity(request, user, "Edit Pengundi",
                 f"Edit pengundi ID {pengundi_id}: {existing['nama_penuh']} - field diubah: {changed_fields}",
                 no_kp_terlibat=existing['no_kp'])

    return {"message": "Pengundi berjaya dikemaskini", "fields_updated": list(update_fields.keys())}


# ===== DELETE PENGUNDI (Admin sahaja) - untuk padam terus rekod =====
@app.delete("/api/pengundi/{pengundi_id}")
def delete_pengundi(request: Request, pengundi_id: int, user=Depends(get_current_user)):
    check_peranan(user, ["Admin"])

    db = get_db()
    cursor = db.cursor()

    # Get data before delete
    cursor.execute("SELECT no_kp, nama_penuh, dm FROM pengundi WHERE id = ?", (pengundi_id,))
    p = cursor.fetchone()
    if not p:
        db.close()
        raise HTTPException(status_code=404, detail="Rekod tidak ditemui")

    no_kp = p["no_kp"]
    nama = p["nama_penuh"]
    dm = p["dm"]

    cursor.execute("DELETE FROM pengundi WHERE id = ?", (pengundi_id,))
    db.commit()
    db.close()

    log_activity(request, user, "Padam Pengundi",
                 f"Padam pengundi ID {pengundi_id}: {nama} (KP: {no_kp}, DM: {dm})",
                 no_kp_terlibat=no_kp)

    return {"message": f"Rekod {nama} berjaya dipadamkan"}


# ===== ENDPOINT APPROVAL QUEUE (Admin sahaja) =====
@app.get("/api/approval-queue")
def get_approval_queue(request: Request, page: int = 1, per_page: int = 50, user=Depends(get_current_user)):
    check_peranan(user, ["Admin"])

    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT COUNT(*) FROM pengundi WHERE status_rekod = 'Menunggu_Kelulusan'")
    total = cursor.fetchone()[0]

    offset = (page - 1) * per_page
    cursor.execute("""
        SELECT id, no_kp, nama_penuh, jantina, tahun_lahir, dm, lokaliti,
               no_telefon, status_sokongan, status_fizikal, status_rekod, sumber_pdm, dicipta_pada
        FROM pengundi
        WHERE status_rekod = 'Menunggu_Kelulusan'
        ORDER BY dicipta_pada DESC
        LIMIT ? OFFSET ?
    """, (per_page, offset))

    queue = [dict(row) for row in cursor.fetchall()]
    db.close()

    log_activity(request, user, "Lihat Approval Queue", f"Lihat queue kelulusan ({total} menunggu)")

    return {
        "data": queue,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": max(1, (total + per_page - 1) // per_page)
    }


# Luluskan rekod (Admin sahaja)
@app.post("/api/approval-queue/{pengundi_id}/lulus")
def approve_record(request: Request, pengundi_id: int, user=Depends(get_current_user)):
    check_peranan(user, ["Admin"])

    db = get_db()
    cursor = db.cursor()
    
    # Get data before approve
    cursor.execute("SELECT no_kp, nama_penuh FROM pengundi WHERE id = ?", (pengundi_id,))
    p = cursor.fetchone()
    if not p:
        db.close()
        raise HTTPException(status_code=404, detail="Rekod tidak ditemui")
    
    cursor.execute("UPDATE pengundi SET status_rekod = 'Sah' WHERE id = ? AND status_rekod = 'Menunggu_Kelulusan'", (pengundi_id,))
    if cursor.rowcount == 0:
        db.close()
        raise HTTPException(status_code=404, detail="Rekod sudah diluluskan")
    db.commit()
    db.close()

    log_activity(request, user, "Lulus Rekod",
                 f"Luluskan rekod ID {pengundi_id}: {p['nama_penuh']}",
                 no_kp_terlibat=p['no_kp'])

    return {"message": "Rekod berjaya diluluskan"}


# Tolak rekod (Admin sahaja)
@app.delete("/api/approval-queue/{pengundi_id}/tolak")
def reject_record(request: Request, pengundi_id: int, user=Depends(get_current_user)):
    check_peranan(user, ["Admin"])

    db = get_db()
    cursor = db.cursor()
    
    # Get data before reject
    cursor.execute("SELECT no_kp, nama_penuh FROM pengundi WHERE id = ? AND status_rekod = 'Menunggu_Kelulusan'", (pengundi_id,))
    p = cursor.fetchone()
    if not p:
        db.close()
        raise HTTPException(status_code=404, detail="Rekod tidak ditemui atau sudah diproses")
    
    no_kp = p['no_kp']
    nama = p['nama_penuh']
    
    cursor.execute("DELETE FROM pengundi WHERE id = ? AND status_rekod = 'Menunggu_Kelulusan'", (pengundi_id,))
    db.commit()
    db.close()

    log_activity(request, user, "Tolak Rekod",
                 f"Tolak rekod ID {pengundi_id}: {nama}",
                 no_kp_terlibat=no_kp)

    return {"message": "Rekod berjaya ditolak dan dipadamkan"}


# ===== APPROVE ALL PENDING (Admin sahaja) =====
@app.post("/api/pengundi/approve-all")
def approve_all_pending(request: Request, user=Depends(get_current_user)):
    check_peranan(user, ["Admin"])

    db = get_db()
    cursor = db.cursor()

    # Count pending records
    cursor.execute("SELECT COUNT(*) FROM pengundi WHERE status_rekod = 'Menunggu_Kelulusan'")
    count = cursor.fetchone()[0]

    if count == 0:
        db.close()
        return {"message": "Tiada rekod yang menunggu kelulusan", "jumlah": 0}

    # Bulk approve all pending
    cursor.execute("UPDATE pengundi SET status_rekod = 'Sah' WHERE status_rekod = 'Menunggu_Kelulusan'")
    db.commit()
    db.close()

    log_activity(request, user, "Luluskan Semua",
                 f"{count} rekod diluluskan secara pukal")

    return {"message": f"{count} rekod berjaya diluluskan", "jumlah": count}


# ===== ENDPOINT AUDIT LOGS (Admin sahaja) =====
@app.get("/api/audit-logs")
def get_audit_logs(
    request: Request,
    page: int = 1,
    per_page: int = 50,
    username: Optional[str] = None,
    tindakan: Optional[str] = None,
    search: Optional[str] = None,
    user=Depends(get_current_user)
):
    check_peranan(user, ["Admin"])

    db = get_db()
    cursor = db.cursor()

    where_parts = []
    params = []

    if username:
        where_parts.append("username = ?")
        params.append(username)
    if tindakan:
        where_parts.append("tindakan = ?")
        params.append(tindakan)
    if search:
        where_parts.append("(penerangan LIKE ? OR no_kp_terlibat LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])

    where = ""
    if where_parts:
        where = "WHERE " + " AND ".join(where_parts)

    cursor.execute(f"SELECT COUNT(*) FROM audit_logs {where}", params)
    total = cursor.fetchone()[0]

    offset = (page - 1) * per_page
    cursor.execute(f"""
        SELECT id, user_id, username, peranan, tindakan, penerangan, no_kp_terlibat, endpoint, ip_address, user_agent, dicipta_pada
        FROM audit_logs {where}
        ORDER BY dicipta_pada DESC
        LIMIT ? OFFSET ?
    """, params + [per_page, offset])

    logs = [dict(row) for row in cursor.fetchall()]
    db.close()

    return {
        "data": logs,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": max(1, (total + per_page - 1) // per_page)
    }


# ===== ENDPOINT PENGURUSAN PENGGUNA (Admin sahaja) =====
@app.get("/api/users")
def get_users(user=Depends(get_current_user)):
    check_peranan(user, ["Admin"])

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, username, nama_penuh, peranan, dm, aktif, dicipta_pada FROM users ORDER BY id")
    users = [dict(row) for row in cursor.fetchall()]
    db.close()
    return users


@app.post("/api/users")
def create_user(request: Request, data: PenggunaCreate, user=Depends(get_current_user)):
    check_peranan(user, ["Admin"])

    db = get_db()
    cursor = db.cursor()

    # Check if username exists
    cursor.execute("SELECT id FROM users WHERE username = ?", (data.username,))
    if cursor.fetchone():
        db.close()
        raise HTTPException(status_code=400, detail="Nama pengguna sudah wujud")

    cursor.execute("""
        INSERT INTO users (username, nama_penuh, kata_laluan, peranan, dm, aktif, dicipta_pada)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data.username, data.nama_penuh, hash_kata_laluan(data.kata_laluan),
        data.peranan, data.dm, 1, datetime.now().isoformat()
    ))
    db.commit()
    db.close()

    log_activity(request, user, "Tambah Pengguna",
                 f"Tambah pengguna baru: {data.username} ({data.peranan})")

    return {"message": f"Pengguna '{data.username}' berjaya dicipta"}


# ===== SURVEY MODELS =====
class SurveyCreate(BaseModel):
    title: str
    description: str = ""
    questions: str  # JSON string of questions array

class SurveySubmit(BaseModel):
    survey_id: int
    answers: str  # JSON string
    respondent_info: str = ""


# ===== SURVEY ENDPOINTS =====

# Mock AI: generate questions based on topic
TEMPLATE_QUESTIONS = {
    "air": [
        {"id": "q1", "type": "short_text", "question": "Adakah anda menghadapi masalah bekalan air bersih?", "required": True},
        {"id": "q2", "type": "multiple_choice", "question": "Berapa kerap masalah air berlaku?", "options": ["Setiap hari", "Beberapa kali seminggu", "Sekali seminggu", "Jarang"], "required": True},
        {"id": "q3", "type": "checkboxes", "question": "Apakah jenis masalah air yang anda hadapi?", "options": ["Air keruh", "Air berbau", "Tekanan rendah", "Bekalan terputus", "Lain-lain"], "required": False},
        {"id": "q4", "type": "short_text", "question": "Apakah cadangan anda untuk menambah baik bekalan air?", "required": False},
    ],
    "jalan": [
        {"id": "q1", "type": "short_text", "question": "Adakah jalan di kawasan anda dalam keadaan baik?", "required": True},
        {"id": "q2", "type": "multiple_choice", "question": "Apakah masalah jalan utama?", "options": ["Jalan berlubang", "Jalan sempit", "Tiada lampu jalan", "Longkang tersumbat"], "required": True},
        {"id": "q3", "type": "short_text", "question": "Lokasi mana yang paling memerlukan perhatian?", "required": True},
    ],
    "sampah": [
        {"id": "q1", "type": "multiple_choice", "question": "Berapa kerap kutipan sampah di kawasan anda?", "options": ["Setiap hari", "2-3 kali seminggu", "Seminggu sekali", "Jarang/Tidak pernah"], "required": True},
        {"id": "q2", "type": "checkboxes", "question": "Apakah isu berkaitan sampah?", "options": ["Kutipan tidak tetap", "Tiada tong sampah", "Pembakaran terbuka", "Longkang tersumbat"], "required": False},
    ],
    "kesihatan": [
        {"id": "q1", "type": "multiple_choice", "question": "Adakah anda berpuas hati dengan perkhidmatan kesihatan?", "options": ["Sangat puas", "Puas", "Kurang puas", "Tidak puas"], "required": True},
        {"id": "q2", "type": "checkboxes", "question": "Apakah kemudahan kesihatan yang diperlukan?", "options": ["Klinik bergerak", "Farmasi", "Ambulans", "Program kesihatan"], "required": False},
    ],
}

DEFAULT_QUESTIONS = [
    {"id": "q1", "type": "short_text", "question": "Apakah pendapat anda tentang isu ini?", "required": True},
    {"id": "q2", "type": "multiple_choice", "question": "Sejauh manakah isu ini memberi kesan kepada anda?", "options": ["Sangat terkesan", "Terkesan", "Kurang terkesan", "Tidak terkesan"], "required": True},
    {"id": "q3", "type": "short_text", "question": "Ada sebarang cadangan?", "required": False},
]


@app.post("/api/surveys/generate")
def generate_survey(prompt_data: dict = Body(...), user=Depends(get_current_user)):
    """Mock AI: generate questions based on topic text"""
    prompt = prompt_data.get("prompt", "").lower()

    # Find matching template or use default
    questions = DEFAULT_QUESTIONS
    for keyword, qs in TEMPLATE_QUESTIONS.items():
        if keyword in prompt:
            questions = qs
            break

    return {
        "title": f"Kajian: {prompt.capitalize() if prompt else 'Tinjauan'}",
        "description": f"Soal selidik berkaitan {prompt if prompt else 'topik'}",
        "questions": questions
    }


@app.get("/api/surveys")
def get_surveys(user=Depends(get_current_user)):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT s.*, COUNT(sr.id) as response_count
        FROM Survey s
        LEFT JOIN SurveyResponse sr ON sr.survey_id = s.id
        GROUP BY s.id
        ORDER BY s.created_at DESC
    """)
    surveys = [dict(row) for row in cursor.fetchall()]
    db.close()
    return surveys


@app.post("/api/surveys")
def create_survey(request: Request, data: SurveyCreate, user=Depends(get_current_user)):
    check_peranan(user, ["Admin"])
    db = get_db()
    cursor = db.cursor()
    now = datetime.now().isoformat()
    cursor.execute(
        "INSERT INTO Survey (title, description, questions, created_by, created_at) VALUES (?, ?, ?, ?, ?)",
        (data.title, data.description, data.questions, user.get("user_id"), now)
    )
    db.commit()
    survey_id = cursor.lastrowid
    db.close()
    log_activity(request, user, "Buat Survey", f"Survey '{data.title}' dicipta")
    return {"id": survey_id, "message": "Survey berjaya dicipta"}


@app.get("/api/surveys/{survey_id}")
def get_survey(survey_id: int, user=Depends(get_current_user)):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM Survey WHERE id = ?", (survey_id,))
    survey = cursor.fetchone()
    if not survey:
        db.close()
        raise HTTPException(status_code=404, detail="Survey tidak ditemui")
    survey = dict(survey)
    # Parse questions JSON
    try:
        survey["questions"] = json.loads(survey["questions"])
    except:
        pass
    db.close()
    return survey


@app.post("/api/surveys/submit")
def submit_survey_response(request: Request, data: SurveySubmit):
    """Public endpoint - no auth required for respondents"""
    db = get_db()
    cursor = db.cursor()
    # Verify survey exists
    cursor.execute("SELECT id FROM Survey WHERE id = ?", (data.survey_id,))
    if not cursor.fetchone():
        db.close()
        raise HTTPException(status_code=404, detail="Survey tidak ditemui")
    now = datetime.now().isoformat()
    cursor.execute(
        "INSERT INTO SurveyResponse (survey_id, answers, respondent_info, submitted_at) VALUES (?, ?, ?, ?)",
        (data.survey_id, data.answers, data.respondent_info, now)
    )
    db.commit()
    db.close()
    return {"message": "Respons berjaya dihantar"}


@app.get("/api/surveys/{survey_id}/responses")
def get_survey_responses(survey_id: int, user=Depends(get_current_user)):
    check_peranan(user, ["Admin"])
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, answers, respondent_info, submitted_at FROM SurveyResponse WHERE survey_id = ? ORDER BY submitted_at DESC", (survey_id,))
    responses = [dict(row) for row in cursor.fetchall()]
    # Parse answers JSON
    for r in responses:
        try:
            r["answers"] = json.loads(r["answers"])
        except:
            pass
    db.close()
    return responses


@app.delete("/api/surveys/{survey_id}")
def delete_survey(request: Request, survey_id: int, user=Depends(get_current_user)):
    check_peranan(user, ["Admin"])
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM SurveyResponse WHERE survey_id = ?", (survey_id,))
    cursor.execute("DELETE FROM Survey WHERE id = ?", (survey_id,))
    db.commit()
    db.close()
    log_activity(request, user, "Padam Survey", f"Survey ID {survey_id} dipadamkan")
    return {"message": "Survey dipadamkan"}


# ===== DIAGNOSTIC DASHBOARD TEST =====
@app.get("/api/dashboard-test")
def dashboard_test(user=Depends(get_current_user)):
    """Test endpoint untuk diagnosis dashboard."""
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT COUNT(*) FROM pengundi WHERE status_fizikal = 'Hidup' AND status_rekod = 'Sah'")
        count = cursor.fetchone()[0]
        cursor.execute("SELECT jantina, COUNT(*) FROM pengundi WHERE status_fizikal = 'Hidup' AND status_rekod = 'Sah' GROUP BY jantina")
        jantina = {r[0] or 'Unknown': r[1] for r in cursor.fetchall()}
        cursor.execute("SELECT status_sokongan, COUNT(*) FROM pengundi WHERE status_fizikal = 'Hidup' AND status_rekod = 'Sah' GROUP BY status_sokongan")
        sokongan = {r[0] or 'Tiada': r[1] for r in cursor.fetchall()}
        db.close()
        return {"success": True, "count": count, "jantina": jantina, "sokongan": sokongan, "msg": "Dashboard test OK"}
    except Exception as e:
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


# ===== ROOT =====
@app.get("/")
def root():
    return {
        "app": "Sistem Pengurusan Pengundi DUN N05 Matunggong",
        "versi": "1.1.0",
        "status": "beroperasi",
        "fitur_baru": "Audit Trail (PDPA), Edit Pengundi"
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
