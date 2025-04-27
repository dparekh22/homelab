import discord
from discord.ext import commands

# Define rank colors (One Piece TCG theme)
RANK_DATA = {
    "OPTCG Bronze": discord.Color.from_str("#CD7F32"),
    "OPTCG Silver": discord.Color.from_str("#C0C0C0"),
    "OPTCG Gold": discord.Color.from_str("#FFD700"),
    "OPTCG Platinum": discord.Color.from_str("#008080"),
    "OPTCG Diamond": discord.Color.from_str("#0CC0FF"),
    "OPTCG Captain": discord.Color.from_str("#800080"),
    "OPTCG Warlord": discord.Color.from_str("#B8860B"),
    "OPTCG Most Wanted": discord.Color.from_str("#8B0000"),
    "OPTCG Yonko": discord.Color.from_str("#4B0082"),
}

async def setup_rank_roles(guild: discord.Guild):
    # Create rank roles for Discord Guild if they do not exist"
    created_roles = []
    for role_name, color in RANK_DATA.items():
        if not discord.utils.get(guild.roles, name=role_name):
            role = await guild.create_role(
                name=role_name,
                color=color,
                hoist=True,
                mentionable=False
            )
            created_roles.append(role.name)
    return created_roles