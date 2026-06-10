from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.auth import UserSignup, UserLogin, UserResponse
from app.services import auth_service
from app.utils.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])

@router.post("/signup")
def signup(data: UserSignup, db: Session = Depends(get_db)):
    return auth_service.signup_tenant_admin(data, db)

@router.post("/login")
def login(data: UserLogin, db: Session = Depends(get_db)):
    return auth_service.login_user(data, db)

@router.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)):
    return user
