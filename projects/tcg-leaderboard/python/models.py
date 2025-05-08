from sqlalchemy import Column, Boolean, DateTime, Integer, String, ForeignKey, Index
from sqlalchemy.sql import func
from database import Base

# SQL Alchemy

class Player(Base):
    __tablename__ = 'players'

    id = Column(Integer, primary_key=True)
    discord_id = Column(String(50), unique=True, nullable=False)  # Discord snowflake ID
    username = Column(String(75), nullable=False)                 # Discord username (may change)
    
    bounty = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    rank = Column(String, default='Bronze')
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index('ix_player_bounty', 'bounty'),
    )

class Match(Base):
    __tablename__ = 'matches'

    id = Column(Integer, primary_key=True)
    
    player1_id = Column(Integer, ForeignKey('players.id'), nullable=False)
    player2_id = Column(Integer, ForeignKey('players.id'), nullable=False)
    winner_id = Column(Integer, ForeignKey('players.id'), nullable=False)

    bounty_gain = Column(Integer, default=0)
    bounty_loss = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

