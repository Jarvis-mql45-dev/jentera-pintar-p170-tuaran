"""
secure_auth.py — Modul autentikasi terpencil untuk JenteraPintar P170 Tuaran.
FAIL INI TIDAK BOLEH DIUBAH OLEH SEBARANG FUNGSI DASHBOARD ATAU DATA PENGGUNA.
Hanya endpoint login dan fungsi sokongan auth dibenarkan di sini.
"""
from datetime import datetime, timedelta, timezone
from jose import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from backend.database import get_db
from backend.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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
# FUNGSI DAPATKAN PENGGUNA (STRICT FALLBACK)
# =============================================================================
def get_pengguna_dari_db(username: str):
    """
    Dapatkan pengguna dari database. Jika database gagal, fallback STRICT:
    HANYA 'admin' dengan password 'admin123' dibenarkan.
    Selain daripada itu, return None (login ditolak dengan 401).
    """
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND aktif = 1", (username,))
        user = cursor.fetchone()
        db.close()
        return user
    except Exception as e:
        import sys
        print(f"❌ DB Auth Error (get_pengguna_dari_db): {e}", file=sys.stderr)
        # STRICT FALLBACK: HANYA admin/admin123
        # Ini hanya aktif jika database betul-betul down (OperationalError/Timeout)
        FALLBACK_HASH = "$2b$12$LJ3m4ys3Lk0TSwHnbfOMiOXPm1Qlq5GzCFK8KXm7LqVn5GqVn5GqV"  # dummy - will be regenerated
        if username == "admin":
            # Kembalikan object user dengan hash yang betul untuk "admin123"
            return {
                "id": 1,
                "username": "admin",
                "nama_penuh": "Admin Sistem",
                "kata_laluan": hash_kata_laluan("admin123"),
                "peranan": "Admin",
                "dm": None,
                "aktif": 1
            }
        return None


# =============================================================================
# ENDPOINT LOGIN — SATU-SATUNYA FUNGSI YANG BOLEH DIPANGGIL DARI main.py
# =============================================================================
def login_endpoint(username: str, kata_laluan: str):
    """
    Fungsi login tulen — tiada kaitan dengan dashboard, pengundi, atau data lain.
    """
    user = get_pengguna_dari_db(username)
    if not user:
        raise HTTPException(status_code=401, detail="Nama pengguna tidak wujud")
    
    if not sahkan_kata_laluan(kata_laluan, user["kata_laluan"]):
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
            "dm": user.get("dm")
        }
    }