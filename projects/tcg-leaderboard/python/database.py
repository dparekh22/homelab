# Import sqlalchemy 
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv
import os

load_dotenv()
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')

# Create DB URL string
DB_URL = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/tcg_leaderboard'

# Create engine with DB_URL
engine = create_engine(DB_URL)

# Create preconfigured session class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base
Base = declarative_base()

