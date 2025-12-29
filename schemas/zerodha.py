from pydantic import BaseModel

class ZerodhaCredentialsUpdate(BaseModel):
    api_key: str
    api_secret: str
