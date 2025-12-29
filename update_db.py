from database import engine, SessionLocal
from sqlalchemy import text

def add_columns():
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN oauth_provider VARCHAR(20) DEFAULT 'dev'"))
            conn.execute(text("ALTER TABLE users ADD COLUMN picture TEXT"))
            conn.commit()
            print("Successfully added columns to users table")
        except Exception as e:
            print(f"Error adding columns (they might already exist): {e}")

if __name__ == "__main__":
    add_columns()
