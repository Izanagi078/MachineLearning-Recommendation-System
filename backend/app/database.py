import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Ensure backend/data/ exists for the db file
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
os.makedirs(DB_DIR, exist_ok=True)
DEFAULT_DB_URL = f"sqlite:///{os.path.join(DB_DIR, 'live_ratings.db')}"

DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_DB_URL)

# ── Connection Pooling Configuration ──────────────────────────────────────────
connect_args = {}
engine_kwargs = {
    "pool_pre_ping": True,
}

if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
else:
    # Configure production pool size/overflow options for external databases
    engine_kwargs.update({
        "pool_size": int(os.environ.get("DB_POOL_SIZE", 10)),
        "max_overflow": int(os.environ.get("DB_MAX_OVERFLOW", 20)),
        "pool_recycle": int(os.environ.get("DB_POOL_RECYCLE", 1800)),
    })

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    **engine_kwargs
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
