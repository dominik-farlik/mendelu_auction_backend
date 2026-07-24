import os
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError

SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@localhost:5432/mendelu_auction"
)

engine = None
while engine is None:
    try:
        test_engine = create_engine(SQLALCHEMY_DATABASE_URL)
        with test_engine.connect():
            pass
        engine = test_engine
        print("Úspěšně připojeno k databázi!")
    except OperationalError:
        print("Databáze ještě není připravená, zkouším to znovu za 2 sekundy...")
        time.sleep(2)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()