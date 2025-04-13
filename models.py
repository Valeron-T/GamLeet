from sqlalchemy import Column, Integer, DateTime, VARCHAR, TEXT
from database import Base
from sqlalchemy.sql import func

class Users(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    zerodha_id = Column(VARCHAR(10), unique=True, nullable=True)
    access_token = Column(TEXT, nullable=True)
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())
