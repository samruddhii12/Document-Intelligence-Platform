from datetime import datetime, timedelta, timezone
from uuid import UUID
import bcrypt, jwt
import hashlib
from backend.config import settings

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False

def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def create_access_token(user_id: UUID, session_id: UUID | None = None) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub":str(user_id),"sid":str(session_id) if session_id else None,"iat":now,"exp":now+timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)},
                      settings.JWT_SECRET_KEY, algorithm="HS256")

def decode_access_token(token: str) -> UUID | None:
    try:
        return UUID(jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"], options={"require":["sub","exp"]})["sub"])
    except Exception:
        return None

def decode_session_token(token):
    try:
        payload=jwt.decode(token,settings.JWT_SECRET_KEY,algorithms=["HS256"],options={"require":["sub","sid","exp"]})
        return UUID(payload["sub"]),UUID(payload["sid"])
    except (jwt.PyJWTError,ValueError,TypeError,KeyError):
        return None
