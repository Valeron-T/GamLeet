from database import Base
from sqlalchemy import CHAR, Column, Integer, DateTime, VARCHAR, TEXT
from sqlalchemy.sql import func
import uuid


class Users(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    public_id = Column(
        CHAR(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4())
    )
    zerodha_id = Column(VARCHAR(10), unique=True, nullable=True)
    access_token = Column(TEXT, nullable=True)
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Questions(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, nullable=False)
    slug = Column(VARCHAR(100), nullable=False)
    acc_rate = Column(
        VARCHAR(10), nullable=True
    )  # Using VARCHAR to represent decimal(4,2)
    topics = Column(VARCHAR(255), nullable=True)
    paid_only = Column(Integer, default=0)  # Using Integer to represent tinyint
    title = Column(VARCHAR(100), nullable=False)
    difficulty = Column(VARCHAR(100), nullable=False)
