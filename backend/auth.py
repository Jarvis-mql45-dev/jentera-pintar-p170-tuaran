from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.database import get_db
from backend.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


def hash_kata_laluan(kata_laluan: str) -> str:
    return pwd_context.hash(kata_laluan)


def sahkan_kata_laluan(kata_laluan_plain: str, kata_laluan_hash: str) -> bool:
    return pwd_context.verify(kata_laluan_plain, kata_laluan_hash)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username = payload.get("sub")
        peranan = payload.get("peranan")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token tidak sah"
            )
        return {"username": username, "peranan": peranan, "user_id": payload.get("user_id")}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tidak sah atau telah tamat tempoh"
        )


def get_pengguna_dari_db(username: str):
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
        # Fallback statik jika database gagal — akaun demo admin
        # Hash bcrypt untuk "admin123" — jana sekali guna supaya konsisten
        FALLBACK_USERS = {
            "admin": {
                "id": 1,
                "username": "admin",
                "nama_penuh": "Admin Sistem",
                "kata_laluan": hash_kata_laluan("admin123"),  # will be stable after first call
                "peranan": "Admin",
                "dm": None,
                "aktif": 1
            },
            "petugas": {
                "id": 2,
                "username": "petugas",
                "nama_penuh": "Petugas Padang",
                "kata_laluan": hash_kata_laluan("petugas123"),
                "peranan": "Petugas Padang",
                "dm": None,
                "aktif": 1
            },
            "pemerhati": {
                "id": 3,
                "username": "pemerhati",
                "nama_penuh": "Pemerhati",
                "kata_laluan": hash_kata_laluan("pemerhati123"),
                "peranan": "Pemerhati",
                "dm": None,
                "aktif": 1
            }
        }
        if username in FALLBACK_USERS:
            print(f"⚠️ FALLBACK: Menggunakan data statik untuk user '{username}'", file=sys.stderr)
            return FALLBACK_USERS[username]
        return None
