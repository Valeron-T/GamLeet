from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

if os.getenv("ENVIRONMENT") != "production":
    from dotenv import load_dotenv
    load_dotenv()


# Replace with your actual MySQL credentials
SQLALCHEMY_DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency for DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()