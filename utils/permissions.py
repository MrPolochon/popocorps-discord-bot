import discord
from discord.ext import commands
import logging
from utils.guild_settings import guild_settings

async def check_raid_mode_permission(ctx):
    """
    Check if a user has permission to use raid mode commands.
    
    Requirements:
    - Must have 'Manage Server' or 'Administrator' permission, or
    - Must have the configured admin role
    """
    return has_raid_mode_permission(ctx.author)

def has_raid_mode_permission(member):
    """
    Check if a guild member has permission to use raid mode commands.
    Requirements:
    - Must have 'Manage Server' or 'Administrator' permission, or
    - Must have the configured admin role
    """
    # Check if member is the server owner
    if member.id == member.guild.owner_id:
        return True
        
    # Check if member has required permissions
    if (member.guild_permissions.manage_guild or 
            member.guild_permissions.administrator):
        return True
        
    # Check if member has the configured admin role
    admin_role_id = guild_settings.get_admin_role(member.guild.id)
    if admin_role_id:
        # Check if member has the admin role
        return any(role.id == admin_role_id for role in member.roles)
            
    return False
