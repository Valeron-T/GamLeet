from fastapi import Header, HTTPException, status
import os

def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != os.getenv("X_API_KEY"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
