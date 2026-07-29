import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated

from app.models.user import User
from app.models.organization import Organization
from app.models.refresh_token import RefreshToken
from app.schemas.auth import UserCreate, UserResponse, TokenResponse
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token
from app.api.deps import CurrentUserDep
from app.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

@router.post("/signup", response_model=TokenResponse)
async def signup(user_in: UserCreate, response: Response):
    """Register a new user and create their personal organization."""
    existing_user = await User.find_one({"email": user_in.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create Personal Organization
    org_name = user_in.organization_name or f"{user_in.full_name}'s Personal Workspace"
    org = Organization(name=org_name)
    await org.insert()

    # Create User
    user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=get_password_hash(user_in.password),
        organization_id=str(org.id),
        role="Administrator" # The owner of the personal org is an admin of it
    )
    await user.insert()

    # Assign owner id back to org now that user exists
    org.owner_id = str(user.id)
    await org.save()

    # Generate Tokens
    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))

    # Save Refresh Token to DB
    await RefreshToken(
        user_id=str(user.id),
        token=refresh_token,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    ).insert()

    # Set HttpOnly Cookie for Refresh Token
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False, # Set True in production with HTTPS
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login", response_model=TokenResponse)
async def login(
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
):
    """Authenticate user and return tokens."""
    user = await User.find_one({"email": form_data.username})
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
        
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    # Generate Tokens
    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))

    # Save Refresh Token to DB
    await RefreshToken(
        user_id=str(user.id),
        token=refresh_token,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    ).insert()

    # Set HttpOnly Cookie for Refresh Token
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )
    
    # Update last login
    user.last_login = datetime.now(timezone.utc)
    await user.save()

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/guest", response_model=TokenResponse)
async def guest_login(response: Response):
    """Create a temporary guest session."""
    
    # Find or create a global guest organization
    org = await Organization.find_one({"name": "Guest Users Organization"})
    if not org:
        org = Organization(name="Guest Users Organization")
        await org.insert()
        
    # Generate random guest details
    guest_id = str(uuid.uuid4())[:8]
    
    user = User(
        email=f"guest_{guest_id}@buildknowledge.ai",
        full_name=f"Guest {guest_id}",
        hashed_password=get_password_hash(str(uuid.uuid4())), # Random password
        organization_id=str(org.id),
        role="Guest",
        is_guest=True
    )
    await user.insert()
    
    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))
    
    await RefreshToken(
        user_id=str(user.id),
        token=refresh_token,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    ).insert()
    
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/refresh-token", response_model=TokenResponse)
async def refresh_token(request: Request, response: Response):
    """Refresh the access token using the HttpOnly cookie."""
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")
        
    # Find token in DB to ensure it's not revoked
    token_record = await RefreshToken.find_one({"token": refresh_token})
    if not token_record or token_record.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
        
    user = await User.get(token_record.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid user")
        
    # Rotate tokens (revoke old, issue new)
    await token_record.delete()
    
    new_access_token = create_access_token(subject=str(user.id))
    new_refresh_token = create_refresh_token(subject=str(user.id))
    
    await RefreshToken(
        user_id=str(user.id),
        token=new_refresh_token,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    ).insert()
    
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )
    
    return {"access_token": new_access_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(request: Request, response: Response):
    """Log out and revoke refresh token."""
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        await RefreshToken.find_one({"token": refresh_token}).delete()
        
    response.delete_cookie("refresh_token")
    return {"detail": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUserDep):
    """Get current user profile."""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "organization_id": current_user.organization_id,
        "is_guest": current_user.is_guest,
        "avatar": current_user.avatar
    }
