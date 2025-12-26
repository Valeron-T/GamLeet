from fastapi import Header, HTTPException, status
import redis.asyncio as redis
from contextlib import asynccontextmanager
from fastapi import FastAPI
import os

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
    redis_client = redis.from_url(
        os.getenv("REDIS_CONN_STRING")
    )
    yield
    if redis_client:
        await redis_client.close()

async def get_redis_client():
    return redis_client
