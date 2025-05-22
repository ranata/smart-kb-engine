from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
from config.constants import GLOBAL_DATABASE_NAME
import configparser
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "../config/config.ini")

config = configparser.ConfigParser()
config.read(CONFIG_PATH)

DB_HOST = config.get("Postgres", "host")
DB_PORT = config.get("Postgres", "port")
DB_NAME = config.get("Postgres", "db")
DB_USER = config.get("Postgres", "username")
DB_PASSWORD = config.get("Postgres", "password")

# Use connection pooling to reduce the overhead of creating new global connections
engine_pool = create_engine(
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{GLOBAL_DATABASE_NAME}",
    pool_size=10,  # Number of connections to maintain
    max_overflow=20,  # Additional connections beyond pool_size
    pool_timeout=5,  # Timeout before erroring
    pool_recycle=1800,  # Recycle connections after 30 minutes
    echo=False,
)

# Created a session for the engine
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_pool)


# Get the global session
def get_db_engine():
    db = SessionLocal()
    try:
        return db, engine_pool
    finally:
        db.close()


# Load All global connection tables
def load_all_tables():
    metadataCollection = MetaData()
    metadataCollection.reflect(bind=engine_pool)
    return metadataCollection


def get_engine(db_name=None):
    database = db_name if db_name else DB_NAME
    database_url = (
        f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{database}"
    )
    return create_engine(database_url, echo=False)


def get_connection():
    try:
        db = SessionLocal()
        return db, engine_pool
    except Exception as e:
        print(f"Error connecting to PostgreSQL database {DB_NAME}: {e}")
        return None


def get_session(db_name=None):
    try:
        engine = get_engine(db_name)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        return db, engine
    except Exception as e:
        print(f"Error connecting to PostgreSQL database {db_name}: {e}")
        return None, None


def close_connection(db, engine):
    if db:
        db.close()
        print("Session closed")
    if engine:
        engine.dispose()
        print("Engine disposed")
