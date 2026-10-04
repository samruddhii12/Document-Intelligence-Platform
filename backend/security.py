from datetime import datetime, timedelta, timezone
from uuid import UUID
import bcrypt, jwt
from backend.config import settings

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False

def create_access_token(user_id: UUID) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub":str(user_id),"iat":now,"exp":now+timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)},
                      settings.JWT_SECRET_KEY, algorithm="HS256")

def decode_access_token(token: str) -> UUID | None:
    try:
        return UUID(jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"], options={"require":["sub","exp"]})["sub"])
    except Exception:
        return None
