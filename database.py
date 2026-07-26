import logging
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError

from config import get_settings


logger = logging.getLogger(__name__)

settings = get_settings()


engine = None
while engine is None:
    try:
        test_engine = create_engine(settings.DATABASE_URL)
        with test_engine.connect():
            pass
        engine = test_engine
        logger.info("Successfully connected to database!")
    except OperationalError:
        logger.warning("Database connection failed, retrying in 2 seconds...")
        time.sleep(2)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()