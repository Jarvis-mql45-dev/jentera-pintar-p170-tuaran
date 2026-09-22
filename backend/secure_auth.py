"""
secure_auth.py — Modul autentikasi terpencil untuk JenteraPintar P170 Tuaran.
FAIL INI TIDAK BOLEH DIUBAH OLEH SEBARANG FUNGSI DASHBOARD ATAU DATA PENGGUNA.
Hanya endpoint login dan fungsi sokongan auth dibenarkan di sini.

🛡️ FASA 4 (Security Hardening — 2026-09-22):
  Fallback pengguna PALSU ("admin/admin123") apabila DB gagal telah DIBUANG.
  DB yang tidak dapat dihubungi kini menghasilkan HTTP 503 — modul ini TIDAK PERNAH
  mereka-reka pengguna atau menerbitkan token tanpa pangkalan data.
"""
import sys
from datetime import datetime, timedelta, timezone
from jose import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from backend.database import get_db
from backend.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# =============================================================================
# MESEJ RALAT PIAWAI (FASA 4)
# =============================================================================
# Satu mesej generik untuk pengguna-tiada DAN kata-laluan-salah → elak
# user enumeration (penyerang tidak boleh mengesahkan kewujudan username).
MESEJ_KREDENSIAL_SALAH = "Nama pengguna atau kata laluan tidak sah"
MESEJ_DB_TIDAK_TERSEDIA = "Pangkalan data tidak dapat dihubungi. Sila cuba sebentar lagi."


class DatabaseUnavailableError(RuntimeError):
    """
    Dilempar apabila pangkalan data TIDAK DAPAT DIHUBUNGI.

    Dibezakan daripada "pengguna tidak dijumpai" (None) supaya pemanggil TIDAK
    boleh tersilap menganggapnya sebagai kegagalan kredensial dan — yang lebih
    penting — supaya login TIDAK boleh berjaya tanpa pangkalan data.
    """
    pass


# =============================================================================
# FUNGSI HASH & SAHKAN KATA LALUAN
# =============================================================================
def hash_kata_laluan(kata_laluan: str) -> str:
    return pwd_context.hash(kata_laluan)


def sahkan_kata_laluan(kata_laluan_plain: str, kata_laluan_hash: str) -> bool:
    return pwd_context.verify(kata_laluan_plain, kata_laluan_hash)


# =============================================================================
# FUNGSI CIPTA JWT TOKEN
# =============================================================================
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# =============================================================================
# FUNGSI DAPATKAN PENGGUNA — TIADA FALLBACK PALSU (FASA 4)
# =============================================================================
def get_pengguna_dari_db(username: str):
    """
    Dapatkan pengguna dari pangkalan data.

    Pulangan:
      - row pengguna → pengguna wujud & aktif
      - None         → DB boleh diakses tetapi tiada pengguna aktif dengan username itu

    Ralat:
      - DatabaseUnavailableError → pangkalan data TIDAK DAPAT DIHUBUNGI

    ⚠️ FASA 4: versi lama memulangkan pengguna 'admin' REKAAN (peranan Admin) apabila
    sambungan DB gagal — membenarkan JWT Admin diterbitkan TANPA pangkalan data
    (insiden pooler Supabase 2026-09-22: 'admin/admin123' berjaya log masuk sementara
    semua pengguna sebenar ditolak). Tingkah laku itu telah DIBUANG.
    """
    try:
        db = get_db()
    except Exception as e:
        # Kegagalan SAMBUNGAN/pool: DB dipause, host salah, TLS, timeout, dsb.
        print(f"❌ DB tidak dapat dihubungi (get_pengguna_dari_db): {type(e).__name__}: {e}",
              file=sys.stderr)
        raise DatabaseUnavailableError(MESEJ_DB_TIDAK_TERSEDIA) from e

    try:
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND aktif = 1", (username,))
        user = cursor.fetchone()
        db.close()
        return user
    except Exception as e:
        # Query gagal (sambungan terputus ketika query, jadual hilang, timeout...) →
        # anggap DB tidak tersedia; JANGAN sesekali memulangkan pengguna palsu.
        print(f"❌ DB query gagal (get_pengguna_dari_db): {type(e).__name__}: {e}", file=sys.stderr)
        try:
            db.close()
        except Exception:
            pass
        raise DatabaseUnavailableError(MESEJ_DB_TIDAK_TERSEDIA) from e


# =============================================================================
# ENDPOINT LOGIN — SATU-SATUNYA FUNGSI YANG BOLEH DIPANGGIL DARI main.py
# =============================================================================
def login_endpoint(username: str, kata_laluan: str):
    """
    Fungsi login tulen — tiada kaitan dengan dashboard, pengundi, atau data lain.

    🛡️ FASA 4:
      - 503 → pangkalan data tidak dapat dihubungi (TIADA token diterbitkan)
      - 401 → SATU mesej generik untuk pengguna-tiada ATAU kata-laluan-salah
    """
    try:
        user = get_pengguna_dari_db(username)
    except DatabaseUnavailableError:
        # 🛡️ FASA 4: DB tidak dapat dihubungi → 503, TIADA token diterbitkan
        raise HTTPException(status_code=503, detail=MESEJ_DB_TIDAK_TERSEDIA)

    if not user:
        # Mesej SAMA seperti kata laluan salah → elak user enumeration
        raise HTTPException(status_code=401, detail=MESEJ_KREDENSIAL_SALAH)
    
    # 🛡️ POKA-YOKE: hash rosak/legasi tidak boleh menyebabkan 500 (bocor stack trace)
    try:
        padan = sahkan_kata_laluan(kata_laluan, user["kata_laluan"] or "")
    except Exception as e:
        print(f"⚠️ Hash kata laluan tidak sah untuk '{username}': {type(e).__name__}: {e}",
              file=sys.stderr)
        padan = False

    if not padan:
        # Mesej SAMA seperti pengguna tiada → elak user enumeration
        raise HTTPException(status_code=401, detail=MESEJ_KREDENSIAL_SALAH)
    
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
            "dm": user.get("dm")
        }
    }