from fastapi import Header, HTTPException, status, Cookie, Depends
import redis.asyncio as redis
from contextlib import asynccontextmanager
from fastapi import FastAPI
import os
from sqlalchemy.orm import Session
from database import get_db
from models import User


from datetime import datetime
from models import User, UserSession

def get_current_user(
    session_token: str | None = Cookie(None),
    db: Session = Depends(get_db),
):
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Verify session in database
    session = db.query(UserSession).filter(
        UserSession.session_token == session_token,
        UserSession.expires_at > datetime.now()
    ).first()

    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    user = db.query(User).filter(User.id == session.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
        
    return user



def verify_admin_access(x_api_key: str = Header(None)):
    if x_api_key != os.getenv("X_API_KEY"):
         raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Admin API key",
        )


redis_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client
    redis_client = redis.from_url(os.getenv("REDIS_CONN_STRING"))
    yield
    if redis_client:
        await redis_client.close()


async def get_redis_client():
    return redis_client
