from fastapi import APIRouter, Depends, HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token
from app.models.identity import OAuthProvider, UserIdentity
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


class GoogleLoginRequest(BaseModel):
    id_token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/google", response_model=TokenResponse)
async def google_login(payload: GoogleLoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        info = google_id_token.verify_oauth2_token(
            payload.id_token,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token")

    provider_user_id = info["sub"]
    email = info.get("email", "")
    display_name = info.get("name", email)

    result = await db.execute(
        select(UserIdentity).where(
            UserIdentity.provider == OAuthProvider.GOOGLE,
            UserIdentity.provider_user_id == provider_user_id,
        )
    )
    identity = result.scalar_one_or_none()

    if identity:
        user = await db.get(User, identity.user_id)
    else:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            user = User(email=email, display_name=display_name)
            db.add(user)
            await db.flush()
        identity = UserIdentity(
            user_id=user.id,
            provider=OAuthProvider.GOOGLE,
            provider_user_id=provider_user_id,
            email=email,
        )
        db.add(identity)
        await db.commit()

    return TokenResponse(access_token=create_access_token(user.id))


class DevLoginRequest(BaseModel):
    email: EmailStr
    display_name: str = "Dev User"


@router.post("/dev", response_model=TokenResponse)
async def dev_login(payload: DevLoginRequest, db: AsyncSession = Depends(get_db)):
    if settings.ENVIRONMENT != "local":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user:
        user = User(email=payload.email, display_name=payload.display_name)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return TokenResponse(access_token=create_access_token(user.id))
