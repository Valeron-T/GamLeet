from cryptography.fernet import Fernet
from fastapi.responses import RedirectResponse
from database import SessionLocal, Base, engine
from datetime import datetime
from dependencies import verify_api_key, lifespan
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from kite import kite_connect, generate_session
from models import Users # Models to be created in DB when API starts
from scheduler import is_leetcode_solved_today, schedule_daily_check, check_dsa_completion
from sqlalchemy.orm import Session
from leetcode.load_questions import leetcode_data_router
from routes import daily
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

secure_router = APIRouter(dependencies=[Depends(verify_api_key)])


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

@secure_router.get("/")
async def root():
    return {"message": "Welcome to the DSA Enforcer App!"}

@secure_router.get("/login")
async def login(db: Session = Depends(get_db)):
    """Intiate Zerodha Login flow

    Args:
        db (Session, optional): _description_. Defaults to Depends(get_db).

    Returns:
        _type_: _description_
    """
    user = db.query(Users).filter(Users.zerodha_id == zerodha_id).first()
    # If login was not done today, prompt relogin else use access token from DB.
    if user.last_updated.date() < datetime.now().date():
        login_url = kite_connect.login_url()
        return {"url": login_url, "status": "AUTH_REQUIRED"}
    else:
        return {"status": "LOGGED_IN"}

@app.get("/login/callback")
async def login_callback(request: Request, db: Session = Depends(get_db)):
    data = request.query_params
    request_token = data.get("request_token")
    if request_token:        
        access_token = generate_session(request_token)
        encrypted_token = cipher.encrypt(access_token.encode())
        user = db.query(Users).filter(Users.zerodha_id == zerodha_id).first()
        if user:
            user.access_token = encrypted_token
        else:
            new_user = Users(zerodha_id=zerodha_id, access_token=encrypted_token)
            db.add(new_user)
        db.commit()
        return RedirectResponse("http://localhost:5173/dashboard")
    return {"message": "Login failed. No request token found."}


@secure_router.get("/test")
async def test(db: Session = Depends(get_db)):
    check_dsa_completion(db)
    # is_leetcode_solved_today()


app.include_router(secure_router)
app.include_router(leetcode_data_router, prefix="/leetcode")
app.include_router(daily.router)