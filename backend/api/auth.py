from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.db_models import User
from backend.models.schemas import RegisterRequest, LoginRequest, TokenResponse, UserResponse
from backend.security import hash_password, verify_password, create_access_token
from backend.api.dependencies import require_user
from backend.config import settings

router=APIRouter(prefix="/auth",tags=["auth"])

@router.post("/register",response_model=TokenResponse,status_code=201)
def register(p:RegisterRequest,db:Session=Depends(get_db)):
    email=p.email.lower().strip()
    if db.query(User).filter(User.email==email).first(): raise HTTPException(409,"Email already registered")
    u=User(email=email,password_hash=hash_password(p.password)); db.add(u); db.commit(); db.refresh(u)
    return TokenResponse(access_token=create_access_token(u.id),expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES*60)

@router.post("/login",response_model=TokenResponse)
def login(p:LoginRequest,db:Session=Depends(get_db)):
    u=db.query(User).filter(User.email==p.email.lower().strip()).first()
    if not u or not verify_password(p.password,u.password_hash): raise HTTPException(401,"Incorrect email or password")
    if not u.is_active: raise HTTPException(403,"Account disabled")
    return TokenResponse(access_token=create_access_token(u.id),expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES*60)

@router.get("/me",response_model=UserResponse)
def me(user:User=Depends(require_user)): return user
