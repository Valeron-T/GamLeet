from cryptography.fernet import Fernet
from fastapi.responses import RedirectResponse
from database import SessionLocal, Base, engine
from datetime import datetime
from dependencies import verify_api_key, lifespan
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from kite import kite_connect, generate_session
from models import User, UserStat  # Models to be created in DB when API starts
from scheduler import (
    is_leetcode_solved_today,
    schedule_daily_check,
    check_dsa_completion,
)
from sqlalchemy.orm import Session
from leetcode.load_questions import leetcode_data_router
from routes import daily, user
from contextlib import asynccontextmanager
import os

load_dotenv()

zerodha_id = os.getenv("ZERODHA_ID")
if not zerodha_id:
    print("Zerodha id not found!")
    exit(-1)

# Generate a key and store it securely (do this once and reuse the key)
encryption_key = os.getenv("ENCRYPTION_KEY")
if not encryption_key:
    print("Encryption key not found!")
    exit(-1)

cipher = Fernet(encryption_key)
# Ensure DB tables are created
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Error creating database tables: {e}")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency for DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Schedule the daily check at 11:59 PM with a DB connection
def schedule_daily_check_with_db():
    db = SessionLocal()
    try:
        schedule_daily_check(db)
    finally:
        db.close()


schedule_daily_check_with_db()

secure_router = APIRouter(
    prefix="/auth",
    dependencies=[Depends(verify_api_key)],
    tags=["Auth"],
)


@secure_router.get("/")
async def root():
    return {"message": "Welcome to the DSA Enforcer App!"}


@secure_router.get("/login")
def start_zerodha_login():
    return {
        "status": "AUTH_REQUIRED",
        "url": kite_connect.login_url(),
    }


@app.get("/auth/callback")
async def zerodha_callback(
    request: Request,
    db: Session = Depends(get_db),
):
    request_token = request.query_params.get("request_token")
    if not request_token:
        raise HTTPException(400, "Missing request token")

    session = generate_session(request_token)
    encrypted_token = cipher.encrypt(session["access_token"].encode())

    # Single-tenant: only one user
    user = db.query(User).first()

    if not user:
        user = User(
            zerodha_id=session["user_id"],
            access_token=encrypted_token,
        )
        db.add(user)
        db.flush()  # ensures user.id is available
    else:
        user.access_token = encrypted_token

    user.last_updated = datetime.utcnow()

    # ✅ Create stats if missing
    stats = db.query(UserStat).filter(UserStat.user_id == user.id).first()

    if not stats:
        stats = UserStat(user_id=user.id)
        db.add(stats)

    db.commit()

    response = RedirectResponse(
        "http://localhost:5173/dashboard",
        status_code=302,
    )

    response.set_cookie(
        key="user_id",
        value=str(user.public_id),
        httponly=True,
        secure=False,  # True in prod
        samesite="lax",
        max_age=60 * 60 * 24,
    )

    return response


@secure_router.get("/test")
async def test(db: Session = Depends(get_db)):
    check_dsa_completion(db)
    # is_leetcode_solved_today()


app.include_router(secure_router)
app.include_router(leetcode_data_router, prefix="/leetcode")
app.include_router(daily.router)
app.include_router(user.router)
