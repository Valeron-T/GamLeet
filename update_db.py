from database import engine, SessionLocal
from sqlalchemy import text

def add_columns():
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN oauth_provider VARCHAR(20) DEFAULT 'dev'"))
        except Exception: 
            pass
        
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN picture TEXT"))
        except Exception: 
            pass

        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN email_notifications INTEGER DEFAULT 1"))
        except Exception: 
            pass
        
        conn.commit()
        print("Finished updating DB columns")

if __name__ == "__main__":
    add_columns()
