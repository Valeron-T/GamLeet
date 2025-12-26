from fastapi import Header, HTTPException, status, Cookie, Depends
import redis.asyncio as redis
from contextlib import asynccontextmanager
from fastapi import FastAPI
import os
from sqlalchemy.orm import Session
from database import get_db
from models import User


def get_current_user(
    user_id: str | None = Cookie(None),
    db: Session = Depends(get_db),
):
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = db.query(User).filter(User.public_id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid user")
    print(user.public_id)
    return user


def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != os.getenv("X_API_KEY"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
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
