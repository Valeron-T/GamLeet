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
    name = Column(VARCHAR(255), unique=True, nullable=True)
    email = Column(VARCHAR(100), unique=True, nullable=True)
    oauth_provider = Column(VARCHAR(20), default="dev") # "google" or "dev"
    picture = Column(TEXT, nullable=True)
    
    # Zerodha Credentials (Stored Encrypted)
    zerodha_api_key = Column(TEXT, nullable=True)
    zerodha_api_secret = Column(TEXT, nullable=True)
    
    # LeetCode Stats
    leetcode_username = Column(VARCHAR(100), nullable=True)
    leetcode_session = Column(TEXT, nullable=True)
    allow_paid = Column(Integer, default=0) # 0 = No, 1 = Yes


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

    current_streak = Column(Integer, default=0, nullable=False)
    max_streak = Column(Integer, default=0, nullable=False)

    problems_solved = Column(Integer, default=0, nullable=False)
    problems_since_last_life = Column(Integer, default=0, nullable=False)
    lives = Column(Integer, default=3, nullable=False)
    difficulty_mode = Column(VARCHAR(20), default="normal", nullable=False)
    powerups_used_today = Column(Integer, default=0, nullable=False)
    gamcoins = Column(Integer, default=0, nullable=False)
    total_xp = Column(Integer, default=0, nullable=False)

    # Problem Set Preferences
    problem_set_type = Column(VARCHAR(20), default="default", nullable=False)  # "default", "topics", "sheet"
    problem_set_topics = Column(TEXT, nullable=True)  # JSON array of topics e.g., '["Array", "Dynamic Programming"]'
    problem_set_sheet = Column(VARCHAR(50), nullable=True)  # e.g., "neetcode150"

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

class UserInventory(Base):
    __tablename__ = "user_inventory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    item_id = Column(VARCHAR(50), nullable=False)  # e.g., "streak-freeze", "penalty-shield"
    quantity = Column(Integer, default=1, nullable=False)
    acquired_at = Column(DateTime, server_default=func.current_timestamp())


class UserAchievement(Base):
    __tablename__ = "user_achievements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    achievement_id = Column(VARCHAR(50), nullable=False)  # e.g., "first-blood", "week-warrior"
    unlocked_at = Column(DateTime, server_default=func.current_timestamp())


class QuestionCompletion(Base):
    __tablename__ = "question_completions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    question_id = Column(Integer, nullable=False, index=True)
    rewarded_at = Column(DateTime, server_default=func.current_timestamp())


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    session_token = Column(CHAR(64), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    expires_at = Column(DateTime, nullable=False)

