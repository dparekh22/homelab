from fastapi import FastAPI, HTTPException, Depends, Body
from pydantic import BaseModel
from typing import Annotated, List, Dict, Any
import models
from database import engine, SessionLocal
from sqlalchemy.orm import Session
from fastapi import status
from constants import RANK_THRESHOLDS
from pydantic import parse_obj_as

app = FastAPI()

# Create all models in models.py
models.Base.metadata.create_all(bind=engine)

# Pydantic models
class PlayerBase(BaseModel):
    discord_id: str
    username: str
    rank: str = 'Bronze'
    bounty: int = 0

class MatchBase(BaseModel):
    player1_username: str 
    player2_username: str
    winner_username: str

class LeaderboardItem(BaseModel):
    rank: int
    username: str
    bounty: int
    wins: int
    losses: int
    rank_title: str


def get_db():

    # Instantiate a Session object from pre configures SessionLocal in database.py
    db = SessionLocal()

    # Try to yield db, finally close connection
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

# Check player exists
def get_player_by_discord_id(discord_id: str, db: db_dependency):
    player = db.query(models.Player).filter(models.Player.discord_id == discord_id).first()
    return player

@app.get('/players/{discord_id}')
async def get_player(discord_id: str, db: db_dependency):
    player = get_player_by_discord_id(discord_id, db)
    if not player:
        raise HTTPException(status_code=404, detail='Player not found!')

    return PlayerBase(
        discord_id=player.discord_id,
        username=player.username,
        rank=player.rank,
        bounty=player.bounty
    )

# Register a new player
@app.post('/register_player', status_code=status.HTTP_201_CREATED)
async def register_player(player: PlayerBase, db: db_dependency):
    # Check if player exists first
    existing_player = get_player_by_discord_id(player.discord_id, db)

    if existing_player:
        raise HTTPException(status_code=400, detail="Player already exists")

    # New player object based on SQL Alchemy Player Model
    new_player = models.Player(
        username = player.username,
        discord_id = player.discord_id,
        bounty = player.bounty,
        rank = player.rank
    )

    # Add and commit new_player
    db.add(new_player)
    db.commit()

    # Refresh and store new_player object from DB in new_player for Python (Gets all DB generated items)
    db.refresh(new_player)
    return new_player 

# Report Match
@app.post('/report_match', status_code=status.HTTP_201_CREATED)
async def report_match(match: MatchBase, db: db_dependency):

    player1 = db.query(models.Player).filter(models.Player.username == match.player1_username).first()
    player2 = db.query(models.Player).filter(models.Player.username == match.player2_username).first()

    if not player1 or not player2:
        raise HTTPException(status_code=404, detail="One or both players not found")

    # Determine winner and loser based on username
    if match.winner_username == player1.username:
        winner, loser = player1, player2
    elif match.winner_username == player2.username:
        winner, loser = player2, player1
    else:
        raise HTTPException(status_code=400, detail="Winner must match one of the player usernames")

    # Calculate bounty change
    bounty_change = max(10, 50 - (winner.bounty - loser.bounty) // 10)

    # Update player stats
    winner.bounty += bounty_change
    winner.wins += 1
    loser.bounty = max(0, loser.bounty - bounty_change)
    loser.losses += 1

    # Update Ranks    
    winner.rank = calculate_rank(winner.bounty)
    loser.rank = calculate_rank(loser.bounty)
    
    # Record match
    new_match = models.Match(
        player1_id = player1.id,
        player2_id = player2.id,
        winner_id = winner.id,
        bounty_change = bounty_change
    )
    db.add(new_match)
    db.commit()
    db.refresh(winner)
    db.refresh(loser)

    return {
        "message": f"Match recorded! {winner.username} defeated {loser.username}",
        "match_id": new_match.id,
        "bounty_change": bounty_change,
        "new_bounties": {
            winner.username: winner.bounty,
            loser.username: loser.bounty
        },
        "new_ranks": {
            winner.username: winner.rank,
            loser.username: loser.rank
        }
    }

def calculate_rank(bounty: int) -> str:
    """Determine rank based on bounty"""
    for rank, threshold in RANK_THRESHOLDS.items():
        if bounty >= threshold:
            return rank
    return "Bronze"

@app.get("/player/{discord_id}/rank", response_model=PlayerBase)
async def get_player_rank(discord_id: str, db: Session = Depends(get_db)):
    player = db.query(models.Player).filter(models.Player.discord_id == discord_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    return PlayerBase(
        discord_id = player.discord_id,
        username = player.username,
        rank = player.rank,
        bounty = player.bounty
    )
# Leaderboard

@app.get("/leaderboard/", response_model=List[LeaderboardItem])
async def get_leaderboard(db: db_dependency, limit: int = 10):
    players = db.query(models.Player)\
        .order_by(models.Player.bounty.desc())\
        .limit(limit)\
        .all()

    if not players:
        return []

    leaderboard = [
        LeaderboardItem(
            rank=i + 1,
            username=player.username,
            bounty=player.bounty,
            wins=player.wins,
            losses=player.losses,
            rank_title=player.rank.capitalize()
        )
        for i, player in enumerate(players)
    ]
    
    return leaderboard

@app.get("/players/{discord_id}/stats", response_model=Dict[str, Any])
async def get_player_stats(discord_id: str, db: Session = Depends(get_db)):
    player = db.query(models.Player).filter(models.Player.discord_id == discord_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    total_matches = player.wins + player.losses
    win_rate = round((player.wins / total_matches * 100)) if total_matches > 0 else 0
    
    return {
        "username": player.username,
        "bounty": player.bounty,
        "wins": player.wins,
        "losses": player.losses,
        "rank": player.rank.capitalize(),
        "win_rate": win_rate,
        "matches_played": total_matches,
        "created_at": player.created_at.strftime("%Y-%m-%d")
    }