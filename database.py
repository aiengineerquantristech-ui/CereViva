
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Get DATABASE_URL from environment
DATABASE_URL = os.environ.get("postgresql://neondb_owner:npg_jsRW4LlVTkF7@ep-lucky-unit-amf04e11-pooler.c-5.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")

# Raise clear error if missing
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Fix postgres:// → postgresql:// for compatibility
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()