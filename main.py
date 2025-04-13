from database import SessionLocal, Base, engine
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.responses import RedirectResponse
from kite import kite_connect, generate_session
from scheduler import is_leetcode_solved_today, schedule_daily_check, check_dsa_completion
from sqlalchemy.orm import Session
from models import Users # Models to be created in DB when API starts
import os
from cryptography.fernet import Fernet

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

app = FastAPI()


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

@app.get("/")
async def root():
    return {"message": "Welcome to the DSA Enforcer App!"}

@app.get("/login")
async def login():
    login_url = kite_connect.login_url()
    return RedirectResponse(login_url)

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
            new_user = Users(zerodha_id=zerodha_id, access_token=access_token)
            db.add(new_user)
        db.commit()
        return {"message": "Login successful!"}
    return {"message": "Login failed. No request token found."}


@app.get("/test")
async def test(db: Session = Depends(get_db)):
    check_dsa_completion(db)
    # is_leetcode_solved_today()
