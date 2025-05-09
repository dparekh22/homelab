from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Annotated, List, Dict, Any
import models
from database import engine, SessionLocal
from sqlalchemy.orm import Session
from fastapi import status
from constants import RANK_THRESHOLDS, CLOUD_BOT_ID

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
    winner_discord_id: str
    loser_discord_id: str

class LeaderboardItem(BaseModel):
    rank: int
    username: str
    bounty: int
    wins: int
    losses: int
    rank_title: str

class MatchReportResponse(BaseModel):
    message: str
    match_id: int
    bounty_change: Dict[str, int]
    new_bounties: Dict[str, int]
    new_ranks: Dict[str, str]


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
@app.post('/players/register', status_code=status.HTTP_201_CREATED)
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
    return PlayerBase(
    discord_id=new_player.discord_id,
    username=new_player.username,
    rank=new_player.rank,
    bounty=new_player.bounty
    )

@app.post('/matches/report', response_model=MatchReportResponse, status_code=status.HTTP_201_CREATED)
async def report_match(match: MatchBase, db: db_dependency):
    BASE_CHANGE = 25

    # Fetch players from DB using discord_id
    player1 = db.query(models.Player).filter(models.Player.discord_id == match.winner_discord_id).first()
    player2 = db.query(models.Player).filter(models.Player.discord_id == match.loser_discord_id).first()

    if match.winner_discord_id == CLOUD_BOT_ID or match.loser_discord_id == CLOUD_BOT_ID:
        return handle_cloudbot_match(match, player1, player2, db, BASE_CHANGE)

    # Check if both players exist
    if not player1 or not player2:
        raise HTTPException(status_code=404, detail="One or both players not found")

    # Calculate the match results (bounty changes, etc.)
    bounty_gain, bounty_loss = calculate_bounty_changes(player1.bounty, player2.bounty)

    # Update stats
    player1.bounty += bounty_gain
    player1.wins += 1
    player2.bounty -= bounty_loss
    player2.losses += 1

    # Update ranks
    player1.rank = calculate_rank(player1.bounty)
    player2.rank = calculate_rank(player2.bounty)

    # Create a new match record
    match_record = models.Match(
        winner_discord_id=player1.discord_id,  # Assuming player1 is the winner
        loser_discord_id=player2.discord_id,
        winner_bounty_gain=bounty_gain,
        loser_bounty_loss=bounty_loss
    )

    db.add(match_record)
    db.commit()
    db.refresh(player1)
    db.refresh(player2)

    return {
        "message": f"Match recorded! {player1.username} defeated {player2.username}",
        "match_id": match_record.id,
        "bounty_change": {
            "gain": bounty_gain,
            "loss": bounty_loss
        },
        "new_bounties": {
            player1.discord_id: player1.bounty,
            player2.discord_id: player2.bounty
        },
        "new_ranks": {
            player1.discord_id: player1.rank,
            player2.discord_id: player2.rank
        }
    }

def handle_cloudbot_match(match: MatchBase, player1, player2, db: db_dependency, base_change: int):
    # Determine cloud bot and human player
    if match.winner_discord_id == CLOUD_BOT_ID:
        cloudbot_player = player1 if player1.discord_id == CLOUD_BOT_ID else player2
        human_player = player2 if player1.discord_id == CLOUD_BOT_ID else player1
        human_won = False
    else:
        human_player = player1 if player1.discord_id == match.winner_discord_id else player2
        cloudbot_player = player1 if player1.discord_id == CLOUD_BOT_ID else player2
        human_won = True

    if not human_player:
        raise HTTPException(status_code=400, detail="No registered human player found")

    bounty_gain = base_change if human_won else 0
    bounty_loss = 0 if human_won else base_change

    # Update human stats
    human_player.bounty = max(0, human_player.bounty + (bounty_gain if human_won else -bounty_loss))
    if human_won:
        human_player.wins += 1
    else:
        human_player.losses += 1
    human_player.rank = calculate_rank(human_player.bounty)

    # Record match
    match_record = models.Match(
        winner_discord_id=match.winner_discord_id,
        loser_discord_id=match.loser_discord_id,
        winner_bounty_gain=bounty_gain,
        loser_bounty_loss=bounty_loss
    )

    db.add(match_record)
    db.commit()
    db.refresh(human_player)

    return {
        "message": f"Match recorded! {'You' if human_won else 'Cloud-Bot'} won.",
        "match_id": match_record.id,
        "bounty_change": {
            "gain": bounty_gain,
            "loss": bounty_loss
        },
        "new_bounties": {
            human_player.discord_id: human_player.bounty,
            CLOUD_BOT_ID: 0,
        },
        "new_ranks": {
            human_player.discord_id: human_player.rank,
            CLOUD_BOT_ID: "N/A"
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

def calculate_rank(bounty: int) -> str:
    for rank, threshold in sorted(RANK_THRESHOLDS.items(), key=lambda item: item[1], reverse=True):
        if bounty >= threshold:
            return rank
    return "Bronze"

@app.get("/players/{discord_id}/rank", response_model=PlayerBase)
async def get_player_rank(discord_id: str, db: db_dependency):
    player = db.query(models.Player).filter(models.Player.discord_id == discord_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    return PlayerBase(
        discord_id=player.discord_id,
        username=player.username,
        rank=player.rank,
        bounty=player.bounty
    )
# Leaderboard

@app.get("/leaderboard/", response_model=List[LeaderboardItem])
async def get_leaderboard(db: db_dependency, limit: int = 10):
    players = db.query(models.Player)\
        .filter(models.Player.discord_id != CLOUD_BOT_ID)\
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
async def get_player_stats(discord_id: str, db: db_dependency):
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