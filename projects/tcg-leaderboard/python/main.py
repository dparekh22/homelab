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

@app.post('/report_match', status_code=status.HTTP_201_CREATED)
async def report_match(match: MatchBase, db: db_dependency):
    BASE_CHANGE = 25

    # Fetch players from DB
    player1 = db.query(models.Player).filter(models.Player.username == match.player1_username).first()
    player2 = db.query(models.Player).filter(models.Player.username == match.player2_username).first()

    # Determine if this is a Cloud-Bot match
    is_vs_cloudbot = match.player1_username == "Cloud-Bot" or match.player2_username == "Cloud-Bot"

    if is_vs_cloudbot:
        return handle_cloudbot_match(match, player1, player2, db, BASE_CHANGE)

    # --- Normal Match ---
    if not player1 or not player2:
        raise HTTPException(status_code=404, detail="One or both players not found")

    if match.winner_username not in [player1.username, player2.username]:
        raise HTTPException(status_code=400, detail="Winner must match one of the player usernames")

    winner, loser = (player1, player2) if match.winner_username == player1.username else (player2, player1)

    # Calculate bounty change
    #bounty_change = max(10, 50 - (winner.bounty - loser.bounty) // 10)

    bounty_gain, bounty_loss = calculate_bounty_changes(winner.bounty, loser.bounty)

    # Update stats
    winner.bounty += bounty_gain
    winner.wins += 1
    loser.bounty -= bounty_loss
    loser.losses += 1

    # Update ranks
    winner.rank = calculate_rank(winner.bounty)
    loser.rank = calculate_rank(loser.bounty)

    # Record match
    match_record = models.Match(
        player1_id=player1.id,
        player2_id=player2.id,
        winner_id=winner.id,
        bounty_gain=bounty_gain,
        bounty_loss=bounty_loss
    )

    db.add(match_record)
    db.commit()
    db.refresh(winner)
    db.refresh(loser)

    return {
        "message": f"Match recorded! {winner.username} defeated {loser.username}",
        "match_id": match_record.id,
        "bounty_change": {
            "gain": bounty_gain,
            "loss": bounty_loss
        }
        "new_bounties": {
            winner.username: winner.bounty,
            loser.username: loser.bounty
        },
        "new_ranks": {
            winner.username: winner.rank,
            loser.username: loser.rank
        }
    }

def calculate_bounty_changes(winner_bounty, loser_bounty):
    diff = winner_bounty - loser_bounty

    if winner_bounty >= loser_bounty:
        # Expected win
        bounty_gain = max(10, 30 - diff // 40)
        bounty_loss = max(10, 20 + diff // 30)
    else:
        # Upset win
        bounty_gain = min(100, 30 + abs(diff) // 10)
        bounty_loss = max(20, 10 + abs(diff) // 20)

    return bounty_gain, bounty_loss

def handle_cloudbot_match(match, player1, player2, db, base_change):
    # Determine if Cloud-Bot is player1 or player2
    if match.player1_username == "Cloud-Bot":
        cloudbot_player = player1
        human_player = player2
    else:
        cloudbot_player = player2
        human_player = player1

    human_username = human_player.username if human_player else None

    # If there is no registered human player, raise an error
    if not human_player:
        raise HTTPException(status_code=400, detail="No registered human player found")

    human_won = match.winner_username == human_username
    bounty_change = base_change if human_won else -base_change

    # Update human player's stats
    human_player.bounty = max(0, human_player.bounty + bounty_change)
    if human_won:
        human_player.wins += 1
    else:
        human_player.losses += 1
    human_player.rank = calculate_rank(human_player.bounty)

    # Build match record
    match_record = models.Match(
        player1_id=player1.id if player1.username != "Cloud-Bot" else cloudbot_player.id,
        player2_id=player2.id if player2.username != "Cloud-Bot" else cloudbot_player.id,
        winner_id=human_player.id if human_won else cloudbot_player.id,
        bounty_change=bounty_change
    )

    db.add(match_record)
    db.commit()
    db.refresh(human_player)

    bot_name = match.player1_username if match.player1_username == "Cloud-Bot" else match.player2_username
    return {
        "message": f"Match recorded! {match.winner_username} defeated {bot_name if not human_won else human_username}",
        "match_id": match_record.id,
        "bounty_change": bounty_change,
        "new_bounties": {human_username: human_player.bounty},
        "new_ranks": {human_username: human_player.rank}
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
        .filter(models.Player.username != "Cloud-Bot")\
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