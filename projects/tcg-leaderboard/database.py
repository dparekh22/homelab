# Import sqlalchemy 
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Create DB URL string
DB_URL = 'postgresql://luffy:mugiwara@localhost:5432/tcg_leaderboard'

# Create engine with DB_URL
engine = create_engine(DB_URL)

# Create preconfigured session class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base
Base = declarative_base()

