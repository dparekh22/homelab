from sqlalchemy import Column, DateTime, Integer, String, ForeignKey, Index
from sqlalchemy.sql import func
from database import Base
from datetime import datetime

# SQLAlchemy Models

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

    # Optional: Index for bounty to improve query performance
    __table_args__ = (
        Index('ix_player_bounty', 'bounty'),
    )

    def __repr__(self):
        return f"<Player(discord_id={self.discord_id}, username={self.username}, bounty={self.bounty}, rank={self.rank})>"

class Match(Base):
    __tablename__ = 'matches'

    id = Column(Integer, primary_key=True)  # autoincrement is default, so no need to specify it
    
    winner_discord_id = Column(String(50), ForeignKey('players.discord_id'), nullable=False)
    loser_discord_id = Column(String(50), ForeignKey('players.discord_id'), nullable=False)

    winner_bounty_gain = Column(Integer, default=0)
    loser_bounty_loss = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Match(winner={self.winner_discord_id}, loser={self.loser_discord_id}, bounty_gain={self.winner_bounty_gain}, bounty_loss={self.loser_bounty_loss})>"

    # Optional: Indexes for foreign keys (to speed up queries with joins)
    __table_args__ = (
        Index('ix_match_player1', 'winner_discord_id'),
        Index('ix_match_player2', 'loser_discord_id')
    )