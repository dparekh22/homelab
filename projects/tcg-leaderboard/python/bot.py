import discord
from discord.ext import commands
from discord.ext.commands import cooldown, BucketType
import os
from dotenv import load_dotenv
import aiohttp
from typing import Optional
from setup_rank_roles import setup_rank_roles, RANK_DATA
import logging


load_dotenv()

TOKEN=os.getenv('DISCORD_TOKEN')
if not TOKEN:
    logging.critical("DISCORD_TOKEN is not set in environment variables.")
    exit(1)

API_BASE_URL=os.getenv('API_BASE_URL')
if not API_BASE_URL:
    logging.critical("API_BASE_URL is not set in environment variables.")
    exit(1)

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.reactions= True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),  # Log to file
        logging.StreamHandler()         # Log to console
    ]
)

session: Optional[aiohttp.ClientSession] = None

async def create_session():
    global session
    if session is None:
        session = aiohttp.ClientSession()
        logging.info("Session created")

async def close_session():
    global session
    if session and not session.closed:
        await session.close()
        logging.info("Session closed")

@bot.event
async def on_ready():
    await create_session()
    logging.info(f"Bot is online as {bot.user}")

@bot.event
async def on_disconnect():
    await close_session()

@bot.event
async def on_shutdown():
    await close_session()

async def get_session() -> aiohttp.ClientSession:
    global session
    return session

RANK_EMOJIS = {
    "Bronze": "🥉",
    "Silver": "🥈", 
    "Gold": "🥇",
    "Platinum": "💎",
    "Diamond": "🔷",
    "Captain": "👑",
    "Warlord": "⚔️",
    "Most Wanted": "💰",
    "Yonko": "🏴‍☠️"
}

# Set up Discord Guild ranks
@bot.command(name="setupranks")
@commands.has_permissions(administrator=True)
async def create_ranks(ctx):
    """Command to initialize all rank roles."""
    created = await setup_rank_roles(ctx.guild)
    if created:
        await ctx.send(f"✅ Created roles: {', '.join(created)}")
    else:
        await ctx.send("⚠️ All roles already exist!")


TARGET_MESSAGE_ID = int(os.getenv('TARGET_MESSAGE_ID'))
ROLE_ID = int(os.getenv('ROLE_ID'))
REACTION_EMOJI = '🔥'

# Add Reaction Event
@bot.event
async def on_raw_reaction_add(payload):

    if payload.user_id == bot.user.id:
        return

    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    if not member:
        member = await guild.fetch_member(payload.user_id)

    try:
        if str(payload.emoji) == '🔥' and payload.message_id == TARGET_MESSAGE_ID:
            await handle_reaction_action(payload, action='add')
    except Exception as e:
        logging.error(f"Error handling reaction add: {e}")

# Remove Reaction Event
@bot.event
async def on_raw_reaction_remove(payload):

    if payload.user_id == bot.user.id:
        return
        
    guild = bot.get_guild(payload.guild_id)
    member = await guild.fetch_member(payload.user_id)

    try:
        if str(payload.emoji) == REACTION_EMOJI and payload.message_id == TARGET_MESSAGE_ID:
            await handle_reaction_action(payload, action='remove')
    except Exception as e:
        logging.error(f"Error handling reaction remove: {e}")

 # Handle Reaction Action
async def handle_reaction_action(payload, action):
    try:
        # Get member and role
        guild = bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        if member is None:
            member = await guild.fetch_member(payload.user_id)
        role = guild.get_role(ROLE_ID)

        # If action is add, check player exists, register if they do not exist
        if action == 'add':
            player_exists = await check_player_exists(payload.user_id)
            if not player_exists:
                success = await register_player(member)
                if not success:
                    logging.error(f'Player registration failed | User: {member.id}')
            # Add role
            if role not in member.roles:
                await member.add_roles(role)
        
        # Else remove roles
        elif action == 'remove':
            await member.remove_roles(role)
    except discord.Forbidden as e:
        logging.error(f"Permission denied when managing roles | User: {member.id} | Error: {str(e)}")
    except Exception as e:
        logging.error(f"Permission denied when managing roles | User: {member.id} | Error: {str(e)}")

# Check if player exists
async def check_player_exists(discord_id):
    global session
    try:
        async with session.get(f'{API_BASE_URL}/players/{discord_id}') as resp:
            if resp.status == 200:
                return True
            elif resp.status == 404:
                return False
            else:
                error = await resp.text()
                logging.error(f"API Error: {error}")
                return False
    except Exception as e:
        logging.error(f"Network error: {e}")
        return False

# Register player
async def register_player(member: discord.Member):

    # Create user data payload
    user_data = {
        'discord_id': str(member.id),
        'username': member.name,
        'display_name': member.display_name,
        'rank': 'Bronze'
    }

    global session
    try:
        # Post to players API with payload
        async with session.post(
            f'{API_BASE_URL}/players/register',
            json=user_data
        ) as response: 
            if response.status == 201:
                return True
            logging.error(
                f"API request failed | URL: {API_BASE_URL}/players/register | "
                f"Status: {response.status} | "
                f"Response: {await response.text()}"
            )
            return False
    except Exception as e:
        logging.error(f"Failed to register player: {str(e)} | User: {member.id}")
        return False

# Find member by username or displayname
async def get_member_by_username(ctx, username: str) -> Optional[discord.Member]:
   
    for member in ctx.guild.members:
        if username.lower() in (member.name.lower(), member.display_name.lower()):
            return member
    return None   

#Report match
@bot.command(name='reportmatch')
@cooldown(1, 30, BucketType.user)  # 1 use per 30 seconds per user
async def report_match(ctx, winner: discord.Member, loser: discord.Member):
    try:
        if winner.id == loser.id:
            await ctx.send("❌ A player can't compete against themselves!")
            return

        # Check player existence
        player_exists_winner = await check_player_exists(winner.id)
        player_exists_loser = await check_player_exists(loser.id)

        if not player_exists_winner:
            await ctx.send(f"❌ Could not find player '{winner}'")
            return

        if not player_exists_loser:
            await ctx.send(f"❌ Could not find player '{loser}'")
            return

        # Prepare match data
        match_data = {
            'winner_discord_id': str(winner.id),
            'loser_discord_id': str(loser.id)
        }

        async with session.post(
            f'{API_BASE_URL}/matches/report',
            json=match_data
        ) as response:
            if response.status == 201:
                match_result = await response.json()
                logging.info(f"Match result: {match_result}")

                try:
                    await update_player_rank_role(winner)
                    await update_player_rank_role(loser)

                    winner_rank = match_result['new_ranks'][str(winner.id)]
                    loser_rank = match_result['new_ranks'][str(loser.id)]

                    await ctx.send(
                        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"🏆 **Match Result**\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"**Winner:** `{winner.display_name}`\n"
                        f"**Loser:** `{loser.display_name}`\n"
                        f"\n"
                        f"📊 **Bounty Update**\n"
                        f"`{winner.display_name}` ➕ {match_result['bounty_change']['gain']}฿ → `{match_result['new_bounties'][str(winner.id)]}฿`\n"
                        f"`{loser.display_name}` ➖ {match_result['bounty_change']['loss']}฿ → `{match_result['new_bounties'][str(loser.id)]}฿`\n"
                        f"\n"
                        f"🎖 **Ranks**\n"
                        f"{winner.display_name}: **{winner_rank}**\n"
                        f"{loser.display_name}: **{loser_rank}**\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━"
                    )
                    return True

                except discord.Forbidden:
                    await ctx.send("Match recorded, but I couldn't update roles (missing permissions)")
                except Exception as e:
                    logging.critical(
                        f'Failed to update roles | Winner: {winner.id}, Loser: {loser.id} | Error: {str(e)}'
                    )
                    await ctx.send("Match recorded, but there was an issue updating roles")

            else:
                error = await response.text()
                await ctx.send(f"❌ Failed to report match: {error}")
                return False

    except commands.CommandOnCooldown as error:
        # This block will only be triggered if the command is on cooldown
        await ctx.send(f"Please wait {error.retry_after:.2f} seconds before using this command again.")

    except Exception as e:
        logging.error(f"Match reporting failed | Error: {str(e)}")
        await ctx.send("⚡ An error occurred while reporting the match.")
        return False

async def update_player_rank_role(member: discord.Member):
    """Update a member's rank role only if their rank changed"""
    global session
    try:
        # Get current rank from API
        async with session.get(f'{API_BASE_URL}/players/{member.id}/rank') as response:
            if response.status == 200:
                player_data = await response.json()
                new_rank = player_data['rank']
                new_role_name = f"OPTCG {new_rank.capitalize()}"
                
                # Check if member already has the correct role
                current_role = next(
                    (role for role in member.roles 
                     if role.name.startswith("OPTCG ") and role.name in RANK_DATA),
                    None
                )
                    
                # Only update if needed
                if current_role and current_role.name == new_role_name:
                    logging.debug(f"{member.display_name} rank unchanged: {new_role_name}")
                    return
                
                # Remove all existing rank roles
                for rank_role in RANK_DATA:
                    role = discord.utils.get(member.guild.roles, name=rank_role)
                    if role and role in member.roles:
                        await member.remove_roles(role)
                    
                # Add new role
                new_role = discord.utils.get(member.guild.roles, name=new_role_name)
                if new_role:
                    await member.add_roles(new_role)
                    logging.info(f"Updated {member.display_name}'s role from "
                            f"{current_role.name if current_role else 'no rank'} to {new_role_name}")
                else:
                    logging.warning(f"Role {new_role_name} not found")
                        
    except Exception as e:
        logging.error(
            f"Rank update failed | User: {member.id} | "
            f"Current Rank: {current_role.name if current_role else 'None'} | "
            f"New Rank: {new_rank} | Error: {str(e)}"
        )
        raise

@bot.command(name='leaderboard')
async def show_leaderboard(ctx, limit: int = 10):
    try:
        session = await get_session()
        async with session.get(
            f'{API_BASE_URL}/leaderboard/?limit={limit}'
        ) as response:
            if response.status == 200:
                leaderboard = await response.json()
                
                # Create embed
                embed = discord.Embed(
                    title="🏴‍☠️ One Piece Bounty Leaderboard",
                    color=discord.Color.gold()
                )
                    
                # Add leaderboard entries
                for entry in leaderboard:
                    embed.add_field(
                        name=f"{RANK_EMOJIS.get(entry['rank_title'], '')} {entry['rank']}. {entry['username']} ({entry['rank_title']})",
                        value=f"฿{entry['bounty']:,} | W: {entry['wins']} L: {entry['losses']}",
                        inline=False
                    )
                    
                embed.set_footer(text=f"Top {len(leaderboard)} players")
                await ctx.send(embed=embed)
                    
            else:
                error = await response.json()
                await ctx.send(f"❌ Error: {error.get('detail', 'Failed to fetch leaderboard')}")
    
    except Exception as e:
        logging.error(f"Leaderboard fetch failed: {str(e)} | Guild: {ctx.guild.id} | Limit: {limit}")
        await ctx.send("⚡ An error occurred while fetching the leaderboard")

@bot.command(name='profile')
async def show_profile(ctx, member: Optional[discord.Member] = None):
    try:
        # Get the raw input for error messages
        input_name = ' '.join(ctx.message.content.split()[1:]) if len(ctx.message.content.split()) > 1 else None
        
        # Determine target member
        target_member = member or ctx.author
        discord_id = str(target_member.id)
        
        # If user provided an argument but couldn't be resolved to a member
        if input_name and not member and target_member == ctx.author:
            await ctx.send(f"❌ User '{input_name}' not found")
            return

        session = await get_session()
        async with session.get(f'{API_BASE_URL}/players/{discord_id}/stats') as resp:
            if resp.status == 200:
                stats = await resp.json()
                    
                # Check if the response actually contains valid data
                if not stats.get('username'):
                    await ctx.send(f"❌ No stats found for {target_member.display_name}")
                    logging.warning(f"No stats found for {target_member.display_name} ({target_member.id})")
                    return
                    
                # Create embed
                embed = discord.Embed(
                    title=f"🏴‍☠️ {target_member.display_name}'s Pirate Profile",
                    color=discord.Color.gold()
                )
                    
                # Profile fields
                fields = [
                    ("Username", stats['username'], True),
                    ("Rank", f"{RANK_EMOJIS.get(stats['rank'], '')} {stats['rank']}", True),
                    ("Bounty", f"฿{stats['bounty']:,}", True),
                    ("Win Rate", f"{stats['win_rate']}%", True),
                    ("Wins", stats['wins'], True),
                    ("Losses", stats['losses'], True),
                    ("Matches Played", stats['matches_played'], False)
                ]
                    
                for name, value, inline in fields:
                    embed.add_field(name=name, value=value, inline=inline)
                    
                # Set footer and thumbnail
                embed.set_footer(text=f"Pirate since {stats['created_at']}")
                embed.set_thumbnail(url=target_member.display_avatar.url)
                
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"❌ No stats found for {target_member.display_name}")
    
    except Exception as e:
        logging.error(f"Profile fetch failed: {str(e)} | Target: {target_member.id} | Guild: {ctx.guild.id}")
        await ctx.send("⚡ An error occurred while fetching profile")

bot.run(TOKEN)


