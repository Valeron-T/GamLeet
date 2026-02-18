from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests
import os
import uuid
import uuid as uuid_pkg

import secrets
from datetime import datetime, timedelta
from database import get_db
from models import User, UserStat, UserInventory, UserSession
from dependencies import get_current_user
from schemas.user_stats import UserStatsResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

def initialize_user_data(db: Session, user: User):
    """
    Initializes default stats and inventory for a new user.
    """
    # Create UserStat
    stats = UserStat(user_id=user.id)
    db.add(stats)
    
    # Optional: Initial inventory (Starter Pack)
    # 1 Streak Freeze, 1 Penalty Shield
    starter_items = [
        UserInventory(user_id=user.id, item_id="streak-freeze", quantity=1),
        UserInventory(user_id=user.id, item_id="penalty-shield", quantity=1)
    ]
    for item in starter_items:
        db.add(item)
    
    db.commit()

IS_PROD = os.getenv("ENVIRONMENT") == "production"

@router.post("/google")
async def google_login(request: Request, response: Response, db: Session = Depends(get_db)):
    """
    Verifies Google ID token and creates/retrieves user.
    """
    body = await request.json()
    token = body.get("token")
    
    if not token:
        raise HTTPException(status_code=400, detail="Missing ID token")
        
    try:
        # Verify the token
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), GOOGLE_CLIENT_ID)
        
        # ID token is valid. Get the user's Google Account ID information.
        userid = idinfo['sub']
        email = idinfo['email']
        name = idinfo.get('name', 'Unknown')
        picture = idinfo.get('picture', '')
        
        # Check if user exists
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            # Create new user
            user = User(
                public_id=str(uuid_pkg.uuid4()),
                email=email,
                name=name,
                picture=picture,
                oauth_provider="google"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
            # Initialize Stats and Inventory
            initialize_user_data(db, user)
        else:
            # Update info if changed
            if user.picture != picture:
                user.picture = picture
                db.commit()
        
        # Create Secure Session
        session_token = secrets.token_hex(32)
        expires_at = datetime.now() + timedelta(days=30)
        
        new_session = UserSession(
            user_id=user.id,
            session_token=session_token,
            expires_at=expires_at
        )
        db.add(new_session)
        db.commit()

        # Set Session Cookie
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=IS_PROD,
            samesite="lax",
            domain=os.getenv("COOKIE_DOMAIN") if IS_PROD else None,
            max_age=60 * 60 * 24 * 30, # 30 days
        )
        
        return {"message": "Login successful", "user": {"email": user.email, "name": user.name}}
        
    except ValueError:
        # Invalid token
        raise HTTPException(status_code=401, detail="Invalid Google Token")

@router.post("/dev-login")
async def dev_login(request: Request, response: Response, db: Session = Depends(get_db)):
    """
    Simple login for Development/Self-Hosted mode.
    Only active if GOOGLE_CLIENT_ID is NOT set.
    """
    if GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=403, detail="Dev login disabled in production")
        
    body = await request.json()
    email = body.get("email")
    
    if not email:
        raise HTTPException(status_code=400, detail="Missing email")
        
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        # Auto-create user for dev convenience
        user = User(
            public_id=str(uuid_pkg.uuid4()),
            email=email,
            name=email.split("@")[0],
            oauth_provider="dev"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Initialize Stats and Inventory
        initialize_user_data(db, user)
        
    # Create Secure Session
    session_token = secrets.token_hex(32)
    expires_at = datetime.now() + timedelta(days=30)
    
    new_session = UserSession(
        user_id=user.id,
        session_token=session_token,
        expires_at=expires_at
    )
    db.add(new_session)
    db.commit()

    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=IS_PROD,
        samesite="lax",
        domain=os.getenv("COOKIE_DOMAIN") if IS_PROD else None,
        max_age=60 * 60 * 24 * 30,
    )
    return {"message": "Dev Login successful", "user": {"email": user.email, "name": user.name}}

@router.post("/logout")
async def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    session_token = request.cookies.get("session_token")
    if session_token:
        db.query(UserSession).filter(UserSession.session_token == session_token).delete()
        db.commit()

    response.delete_cookie("session_token")
    return {"message": "Logged out successfully"}

@router.get("/me")
async def get_current_user_info(user: User = Depends(get_current_user)):
    return {
        "id": user.public_id,
        "email": user.email,
        "name": user.name,
        "picture": user.picture,
        "provider": user.oauth_provider,
        "has_completed_walkthrough": user.has_completed_walkthrough
    }

