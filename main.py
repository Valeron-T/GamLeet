from cryptography.fernet import Fernet
from fastapi.responses import RedirectResponse
from database import SessionLocal, Base, engine
from datetime import datetime
from dependencies import verify_admin_access, lifespan, get_current_user
from database import get_db
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from kite import generate_session
import models # Ensure all models are registered for Base.metadata.create_all
from models import User, UserStat  # Models to be created in DB when API starts
from scheduler import (
    is_leetcode_solved_today,
    schedule_daily_check,
    check_dsa_completion,
)
from sqlalchemy.orm import Session
from leetcode.load_questions import leetcode_data_router
from routes import daily, user, leaderboard, auth, problems
from contextlib import asynccontextmanager
import os

load_dotenv()

zerodha_id = os.getenv("ZERODHA_ID")
if not zerodha_id:
    print("Zerodha id not found!")
    exit(-1)

from security import encrypt_token, decrypt_token
# Ensure DB tables are created
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Error creating database tables: {e}")

# Environment Settings
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PROD = ENVIRONMENT == "production"

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Removed redundant get_db definition as it's now imported from database.py


# Schedule the daily check at 11:59 PM with a DB connection
def schedule_daily_check_with_db():
    db = SessionLocal()
    try:
        schedule_daily_check(db)
    finally:
        db.close()


schedule_daily_check_with_db()

@app.get("/")
async def root():
    return {"message": "Welcome to the GamLeet API!"}


@app.get("/auth/callback")
async def zerodha_callback(
    request: Request,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    request_token = request.query_params.get("request_token")
    if not request_token:
        raise HTTPException(400, "Missing request token")
    
    if not user or not user.zerodha_api_key or not user.zerodha_api_secret:
        raise HTTPException(400, "Zerodha credentials not set for user")

    from kite import generate_session
    from security import decrypt_token
    
    api_key = decrypt_token(user.zerodha_api_key)
    api_secret = decrypt_token(user.zerodha_api_secret)
    
    try:
        session = generate_session(api_key, api_secret, request_token)
    except Exception as e:
        print(f"Failed to generate Zerodha session: {e}")
        raise HTTPException(400, f"Zerodha login failed: {str(e)}")

    encrypted_token = encrypt_token(session["access_token"])
    user.access_token = encrypted_token
    user.zerodha_id = session.get("user_id")
    user.last_updated = datetime.utcnow()

    # ✅ Create stats if missing
    stats = db.query(UserStat).filter(UserStat.user_id == user.id).first()

    if not stats:
        stats = UserStat(user_id=user.id)
        db.add(stats)

    db.commit()

    response = RedirectResponse(
        url=f"{FRONTEND_URL}/integrations", # Back to integrations to show success
        status_code=302,
    )

    response.set_cookie(
        key="user_id",
        value=str(user.public_id),
        httponly=True,
        secure=IS_PROD,
        samesite="lax",
        domain=os.getenv("COOKIE_DOMAIN") if IS_PROD else None,
        max_age=60 * 60 * 24,
    )

    return response


@app.get("/test")
async def test(db: Session = Depends(get_db)):
    user = db.query(User).first()
    if user:
        check_dsa_completion(user, db)
    # is_leetcode_solved_today()


app.include_router(leetcode_data_router, prefix="/leetcode")
app.include_router(daily.router)
app.include_router(user.router)
app.include_router(leaderboard.router)
app.include_router(auth.router)
app.include_router(problems.router)
