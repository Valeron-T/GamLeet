from database import Base
from sqlalchemy import CHAR, DECIMAL, Column, Date, Integer, DateTime, VARCHAR, TEXT
from sqlalchemy.sql import func
import uuid


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    public_id = Column(
        CHAR(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4())
    )
    zerodha_id = Column(VARCHAR(10), unique=True, nullable=True)
    access_token = Column(TEXT, nullable=True)
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Question(Base):
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


class UserStat(Base):
    __tablename__ = "user_stats"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True, nullable=False, index=True)

    lifetime_loss = Column(DECIMAL(12, 2), default=0.00, nullable=False)
    available_balance = Column(DECIMAL(12, 2), default=0.00, nullable=False)

    current_streak = Column(Integer, default=0, nullable=False)
    max_streak = Column(Integer, default=0, nullable=False)

    problems_solved = Column(Integer, default=0, nullable=False)
    gamcoins = Column(Integer, default=0, nullable=False)
    total_xp = Column(Integer, default=0, nullable=False)



    last_activity_date = Column(Date, nullable=True)

    created_at = Column(
        DateTime,
        server_default=func.current_timestamp()
    )
    updated_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )