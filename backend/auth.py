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
        # Database tidak boleh diakses — tolak semua log masuk
        # Jangan guna fallback statik demi keselamatan
        return None
