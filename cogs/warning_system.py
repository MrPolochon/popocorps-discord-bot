import discord
from discord.ext import commands
from discord import app_commands
import logging
import re
from datetime import datetime, timezone
from typing import Optional
from models import Warning, get_db_session, create_tables
from utils.permissions import has_raid_mode_permission
from utils.translations import get_text, create_embed
from sqlalchemy import desc

class WarningSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        create_tables()  # Ensure tables exist
        
        # Bot patterns for detecting warnings from other bots
        self.bot_patterns = {
            'draftbot': {
                'name_patterns': ['draftbot', 'draft bot'],
                'warning_patterns': [
                    r'⚠️.*warned.*<@!?(\d+)>.*reason:?\s*(.+)',
                    r'<@!?(\d+)>.*has been warned.*reason:?\s*(.+)',
                    r'warned\s+<@!?(\d+)>.*for:?\s*(.+)',
                    r'⚠️.*<@!?(\d+)>.*warned.*(.+)'
                ]
            },
            'carl-bot': {
                'name_patterns': ['carl-bot', 'carl bot', 'carlbot'],
                'warning_patterns': [
                    r'⚠️.*<@!?(\d+)>.*warned.*reason:?\s*(.+)',
                    r'warned\s+<@!?(\d+)>.*(.+)'
                ]
            },
            'dyno': {
                'name_patterns': ['dyno', 'dyno bot'],
                'warning_patterns': [
                    r'⚠️.*<@!?(\d+)>.*warned.*(.+)',
                    r'warned\s+<@!?(\d+)>.*(.+)'
                ]
            },
            'mee6': {
                'name_patterns': ['mee6', 'mee 6'],
                'warning_patterns': [
                    r'⚠️.*<@!?(\d+)>.*warned.*(.+)',
                    r'<@!?(\d+)>.*has been warned.*(.+)'
                ]
            },
            'general': {
                'name_patterns': [],
                'warning_patterns': [
                    r'⚠️.*warned.*<@!?(\d+)>.*(.+)',
                    r'<@!?(\d+)>.*warned.*(.+)',
                    r'warning.*<@!?(\d+)>.*(.+)',
                    r'⚠️.*<@!?(\d+)>.*(.+)'
                ]
            }
        }

    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for warning messages from other bots"""
        if message.author.bot and message.guild:
            await self.detect_warning(message)

    async def detect_warning(self, message):
        """Detect and store warnings from other bots"""
        try:
            content = message.content.lower()
            embed_text = ""
            
            # Check embeds for warning content
            if message.embeds:
                for embed in message.embeds:
                    if embed.title:
                        embed_text += embed.title + " "
                    if embed.description:
                        embed_text += embed.description + " "
                    for field in embed.fields:
                        embed_text += field.name + " " + field.value + " "
            
            full_text = (content + " " + embed_text).lower()
            
            # Detect which bot sent the warning
            bot_source = "unknown"
            for bot_name, bot_config in self.bot_patterns.items():
                if bot_name == 'general':
                    continue
                    
                if message.author and message.author.display_name:
                    author_name = message.author.display_name.lower()
                    for pattern in bot_config['name_patterns']:
                        if pattern in author_name:
                            bot_source = bot_name
                            break
                            
                    if bot_source != "unknown":
                        break
            
            # Try to extract warning information
            user_id = None
            reason = None
            
            # Try patterns for the detected bot first, then general patterns
            patterns_to_try = []
            if bot_source in self.bot_patterns:
                patterns_to_try.extend(self.bot_patterns[bot_source]['warning_patterns'])
            patterns_to_try.extend(self.bot_patterns['general']['warning_patterns'])
            
            for pattern in patterns_to_try:
                match = re.search(pattern, full_text, re.IGNORECASE | re.DOTALL)
                if match:
                    try:
                        user_id = int(match.group(1))
                        reason = match.group(2).strip() if len(match.groups()) > 1 else "No reason provided"
                        break
                    except (ValueError, IndexError):
                        continue
            
            if user_id:
                await self.store_warning(
                    guild_id=message.guild.id,
                    user_id=user_id,
                    moderator_id=message.author.id,
                    reason=reason,
                    bot_source=bot_source,
                    message_id=message.id,
                    channel_id=message.channel.id
                )
                
                logging.info(f"Stored warning from {bot_source} for user {user_id} in guild {message.guild.id}")
                
        except Exception as e:
            logging.error(f"Error detecting warning: {e}")

    async def store_warning(self, guild_id, user_id, moderator_id, reason, bot_source, message_id=None, channel_id=None):
        """Store a warning in the database with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            db = None
            try:
                db = get_db_session()
                warning = Warning(
                    guild_id=guild_id,
                    user_id=user_id,
                    moderator_id=moderator_id,
                    reason=reason,
                    bot_source=bot_source,
                    message_id=message_id,
                    channel_id=channel_id,
                    timestamp=datetime.now(timezone.utc)
                )
                db.add(warning)
                db.commit()
                return  # Success, exit function
            except Exception as e:
                if db:
                    db.rollback()
                logging.error(f"Error storing warning (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    logging.error(f"Failed to store warning after {max_retries} attempts")
                else:
                    # Wait before retry
                    import asyncio
                    await asyncio.sleep(0.5)
            finally:
                if db:
                    db.close()

    @app_commands.command(name="warn", description="Issue a warning to a user")
    @app_commands.describe(
        user="The user to warn",
        reason="The reason for the warning"
    )
    async def warn_user(self, interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided"):
        """Issue a warning to a user"""
        if not has_raid_mode_permission(interaction.user):
            await interaction.response.send_message(
                get_text(interaction.guild.id, 'no_permission'),
                ephemeral=True
            )
            return
            
        try:
            # Store the warning
            await self.store_warning(
                guild_id=interaction.guild.id,
                user_id=user.id,
                moderator_id=interaction.user.id,
                reason=reason,
                bot_source="popocorp"  # Our bot name
            )
            
            # Create warning embed
            embed = create_embed(
                interaction.guild.id,
                'warning_issued',
                color=discord.Color.orange()
            )
            embed.description = f"{user.mention} {get_text(interaction.guild.id, 'warning_recorded')}"
            embed.add_field(name=get_text(interaction.guild.id, 'reason'), value=reason, inline=False)
            embed.add_field(name=get_text(interaction.guild.id, 'moderator'), value=interaction.user.mention, inline=True)
            embed.set_footer(text=f"User ID: {user.id}")
            embed.timestamp = datetime.now(timezone.utc)
            
            await interaction.response.send_message(embed=embed)
            
            # Try to DM the user
            try:
                dm_embed = create_embed(
                    interaction.guild.id,
                    'warning_issued',
                    color=discord.Color.orange()
                )
                dm_embed.description = f"You have been warned in **{interaction.guild.name}**"
                dm_embed.add_field(name=get_text(interaction.guild.id, 'reason'), value=reason, inline=False)
                dm_embed.add_field(name=get_text(interaction.guild.id, 'moderator'), value=interaction.user.display_name, inline=True)
                dm_embed.timestamp = datetime.now(timezone.utc)
                
                await user.send(embed=dm_embed)
            except discord.Forbidden:
                pass  # User has DMs disabled
                
        except Exception as e:
            logging.error(f"Error issuing warning: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while issuing the warning.",
                ephemeral=True
            )

    @app_commands.command(name="warnlist", description="Show warnings for a user or all server warnings")
    @app_commands.describe(user="The user to check warnings for (leave empty to see all server warnings)")
    async def warn_list(self, interaction: discord.Interaction, user: discord.Member = None):
        """Display warnings for a user or all server warnings"""
        if not has_raid_mode_permission(interaction.user):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command.",
                ephemeral=True
            )
            return
        
        max_retries = 3
        for attempt in range(max_retries):
            db = None
            try:
                db = get_db_session()
                
                if user:
                    # Show warnings for specific user
                    warnings = db.query(Warning).filter(
                        Warning.guild_id == interaction.guild.id,
                        Warning.user_id == user.id
                    ).order_by(desc(Warning.timestamp)).all()
                    
                    if not warnings:
                        embed = discord.Embed(
                            title="📋 Warning List",
                            description=f"{user.mention} has no warnings.",
                            color=discord.Color.green()
                        )
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                        return
                else:
                    # Show ALL server warnings
                    warnings = db.query(Warning).filter(
                        Warning.guild_id == interaction.guild.id
                    ).order_by(desc(Warning.timestamp)).limit(50).all()  # Limit to 50 most recent
                    
                    if not warnings:
                        embed = discord.Embed(
                            title="📋 Server Warning List",
                            description="No warnings found in this server.",
                            color=discord.Color.green()
                        )
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                        return
                
                # Success - break out of retry loop
                break
                
            except Exception as e:
                logging.error(f"Error fetching warnings (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    await interaction.response.send_message(
                        "❌ Database connection error. Please try again later.",
                        ephemeral=True
                    )
                    return
                else:
                    # Wait before retry
                    import asyncio
                    await asyncio.sleep(0.5)
            finally:
                if db:
                    db.close()
        
        try:
            if user:
                # Single user warning display
                embed = discord.Embed(
                    title="📋 Warning List",
                    description=f"Warnings for {user.mention} ({len(warnings)} total)",
                    color=discord.Color.orange()
                )
                
                for i, warning in enumerate(warnings[:15]):  # Show last 15 warnings for individual user
                    moderator = self.bot.get_user(warning.moderator_id) if warning.moderator_id else None
                    moderator_name = moderator.display_name if moderator else "Unknown"
                    
                    bot_emoji = {
                        'draftbot': '🤖',
                        'carl-bot': '🦾',
                        'dyno': '⚡',
                        'mee6': '🎵',
                        'popocorp': '🛡️',
                        'unknown': '❓'
                    }.get(warning.bot_source or 'unknown', '❓')
                    
                    timestamp_str = warning.timestamp.strftime("%d/%m/%Y %H:%M")
                    bot_source_name = (warning.bot_source or 'unknown').title()
                    
                    embed.add_field(
                        name=f"{bot_emoji} Warning #{i+1} - {bot_source_name}",
                        value=f"**Date:** {timestamp_str}\n"
                              f"**Moderator:** {moderator_name} (ID: {warning.moderator_id})\n" 
                              f"**Reason:** {warning.reason or 'No reason provided'}",
                        inline=False
                    )
            else:
                # All server warnings display
                embed = discord.Embed(
                    title="📋 Server Warning List",
                    description=f"All server warnings ({len(warnings)} total - showing 25 most recent)",
                    color=discord.Color.red()
                )
                
                for i, warning in enumerate(warnings[:25]):  # Show 25 most recent warnings
                    # Try multiple methods to get user info
                    warned_user = self.bot.get_user(warning.user_id)
                    if not warned_user:
                        # Try getting from guild members
                        warned_user = interaction.guild.get_member(warning.user_id)
                    
                    if warned_user:
                        warned_user_name = warned_user.display_name
                    else:
                        # Fallback: try to fetch user by ID
                        try:
                            warned_user = await self.bot.fetch_user(warning.user_id)
                            warned_user_name = warned_user.display_name
                        except:
                            warned_user_name = f"User ID: {warning.user_id}"
                    
                    # Same for moderator
                    moderator = self.bot.get_user(warning.moderator_id) if warning.moderator_id else None
                    if not moderator and warning.moderator_id:
                        moderator = interaction.guild.get_member(warning.moderator_id)
                    if not moderator and warning.moderator_id:
                        try:
                            moderator = await self.bot.fetch_user(warning.moderator_id)
                        except:
                            pass
                    
                    moderator_name = moderator.display_name if moderator else f"Moderator ID: {warning.moderator_id}" if warning.moderator_id else "Unknown"
                    
                    bot_emoji = {
                        'draftbot': '🤖',
                        'carl-bot': '🦾',
                        'dyno': '⚡',
                        'mee6': '🎵',
                        'popocorp': '🛡️',
                        'unknown': '❓'
                    }.get(warning.bot_source or 'unknown', '❓')
                    
                    timestamp_str = warning.timestamp.strftime("%d/%m/%Y %H:%M")
                    bot_source_name = (warning.bot_source or 'unknown').title()
                    
                    embed.add_field(
                        name=f"{bot_emoji} Warning #{i+1} - {bot_source_name}",
                        value=f"**User:** {warned_user_name} (ID: {warning.user_id})\n"
                              f"**Date:** {timestamp_str}\n"
                              f"**Moderator:** {moderator_name} (ID: {warning.moderator_id})\n"
                              f"**Reason:** {warning.reason or 'No reason provided'}",
                        inline=True
                    )
            
            if user and len(warnings) > 15:
                embed.add_field(
                    name="📄 Note",
                    value=f"Showing latest 15 warnings. Total: {len(warnings)}",
                    inline=False
                )
            elif not user and len(warnings) > 25:
                embed.add_field(
                    name="📄 Note", 
                    value=f"Showing latest 25 warnings. Total: {len(warnings)}",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logging.error(f"Error creating warning embed: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while displaying warnings.",
                ephemeral=True
            )

    @app_commands.command(name="banlist", description="Show all server bans with details")
    async def ban_list(self, interaction: discord.Interaction):
        """Display all server bans with complete details"""
        if not has_raid_mode_permission(interaction.user):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get ban list from Discord
            banned_users = []
            async for ban_entry in interaction.guild.bans(limit=None):
                banned_users.append(ban_entry)
            
            if not banned_users:
                embed = discord.Embed(
                    title="🔨 Server Ban List",
                    description="No banned users found in this server.",
                    color=discord.Color.green()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Create ban list embed
            embed = discord.Embed(
                title="🔨 Server Ban List",
                description=f"All server bans ({len(banned_users)} total)",
                color=discord.Color.dark_red()
            )
            
            # Show up to 25 most recent bans (Discord API doesn't guarantee order but we'll show what we get)
            for i, ban_entry in enumerate(banned_users[:25]):
                user = ban_entry.user
                reason = ban_entry.reason or "No reason provided"
                
                # Try to get ban details from audit logs
                ban_moderator = "Unknown"
                ban_date = "Unknown"
                is_permanent = "Yes (Default)"
                
                try:
                    # Look through recent audit log entries for ban actions
                    async for entry in interaction.guild.audit_logs(action=discord.AuditLogAction.ban, limit=100):
                        if entry.target and entry.target.id == user.id:
                            ban_moderator = entry.user.display_name if entry.user else "Unknown"
                            ban_date = entry.created_at.strftime("%d/%m/%Y %H:%M")
                            is_permanent = "Yes (Manual Ban)"
                            break
                except discord.Forbidden:
                    # No access to audit logs
                    pass
                
                embed.add_field(
                    name=f"🔨 Ban #{i+1}",
                    value=f"**User:** {user.display_name} (ID: {user.id})\n"
                          f"**Banned by:** {ban_moderator}\n"
                          f"**Date:** {ban_date}\n"
                          f"**Permanent:** {is_permanent}\n"
                          f"**Reason:** {reason}",
                    inline=True
                )
            
            if len(banned_users) > 25:
                embed.add_field(
                    name="📄 Note",
                    value=f"Showing latest 25 bans. Total: {len(banned_users)}",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logging.error(f"Error fetching ban list: {e}")
            await interaction.followup.send(
                "❌ An error occurred while fetching the ban list.", 
                ephemeral=True
            )

    @app_commands.command(name="userinfo", description="Get detailed information about a user")
    @app_commands.describe(user="The user to get information about (ID or mention)")
    async def user_info(self, interaction: discord.Interaction, user: discord.Member = None):
        """Display detailed information about a user"""
        if not has_raid_mode_permission(interaction.user):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command.",
                ephemeral=True
            )
            return
        
        target_user = user
        user_id = None
        
        # If no user provided, check if user typed an ID
        if not target_user:
            await interaction.response.send_message(
                "❌ Please mention a user or provide their ID.",
                ephemeral=True
            )
            return
            
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Try to get user info from various sources
            if not target_user:
                # Try to fetch by ID if it's a valid snowflake
                try:
                    target_user = await self.bot.fetch_user(user_id)
                    guild_member = interaction.guild.get_member(user_id)
                except:
                    await interaction.followup.send("❌ User not found.", ephemeral=True)
                    return
            else:
                guild_member = target_user
            
            # Create comprehensive user info embed
            embed = discord.Embed(
                title=f"👤 User Information",
                color=discord.Color.blue(),
                timestamp=datetime.now(timezone.utc)
            )
            
            # Set user avatar as thumbnail
            embed.set_thumbnail(url=target_user.display_avatar.url)
            
            # Basic user information
            embed.add_field(
                name="📋 Basic Info",
                value=f"**Username:** {target_user.name}\n"
                      f"**Display Name:** {target_user.display_name}\n"
                      f"**User ID:** {target_user.id}\n"
                      f"**Bot:** {'Yes' if target_user.bot else 'No'}",
                inline=True
            )
            
            # Account creation date
            created_at = target_user.created_at
            created_timestamp = int(created_at.timestamp())
            # Ensure both datetimes are timezone-aware for comparison
            now_utc = datetime.now(timezone.utc)
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            account_age_days = (now_utc - created_at).days
            
            embed.add_field(
                name="📅 Account Created",
                value=f"<t:{created_timestamp}:F>\n"
                      f"<t:{created_timestamp}:R>\n"
                      f"**Age:** {account_age_days} days",
                inline=True
            )
            
            # Server-specific information if user is in the server
            if guild_member and isinstance(guild_member, discord.Member):
                # Join date
                joined_at = guild_member.joined_at
                if joined_at:
                    joined_timestamp = int(joined_at.timestamp())
                    # Ensure both datetimes are timezone-aware for comparison
                    if joined_at.tzinfo is None:
                        joined_at = joined_at.replace(tzinfo=timezone.utc)
                    server_age_days = (now_utc - joined_at).days
                    
                    embed.add_field(
                        name="🏠 Joined Server",
                        value=f"<t:{joined_timestamp}:F>\n"
                              f"<t:{joined_timestamp}:R>\n"
                              f"**Member for:** {server_age_days} days",
                        inline=True
                    )
                
                # Roles (excluding @everyone)
                roles = [role for role in guild_member.roles if role.name != "@everyone"]
                if roles:
                    role_list = ", ".join([role.mention for role in roles[:10]])  # Limit to 10 roles
                    if len(roles) > 10:
                        role_list += f" and {len(roles) - 10} more..."
                    
                    embed.add_field(
                        name=f"🎭 Roles ({len(roles)})",
                        value=role_list,
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="🎭 Roles",
                        value="No roles assigned",
                        inline=False
                    )
                
                # Key permissions
                permissions = guild_member.guild_permissions
                key_perms = []
                
                perm_checks = [
                    ("Administrator", permissions.administrator),
                    ("Manage Server", permissions.manage_guild),
                    ("Manage Channels", permissions.manage_channels),
                    ("Manage Roles", permissions.manage_roles),
                    ("Manage Messages", permissions.manage_messages),
                    ("Kick Members", permissions.kick_members),
                    ("Ban Members", permissions.ban_members),
                    ("Moderate Members", permissions.moderate_members),
                    ("Manage Nicknames", permissions.manage_nicknames),
                    ("View Audit Log", permissions.view_audit_log)
                ]
                
                for perm_name, has_perm in perm_checks:
                    if has_perm:
                        key_perms.append(f"✅ {perm_name}")
                
                if key_perms:
                    embed.add_field(
                        name="🔑 Key Permissions",
                        value="\n".join(key_perms[:8]),  # Limit to 8 permissions
                        inline=True
                    )
                else:
                    embed.add_field(
                        name="🔑 Key Permissions",
                        value="No special permissions",
                        inline=True
                    )
                
                # User status
                status_info = []
                if hasattr(guild_member, 'status'):
                    status_emoji = {
                        discord.Status.online: "🟢 Online",
                        discord.Status.idle: "🟡 Idle", 
                        discord.Status.dnd: "🔴 Do Not Disturb",
                        discord.Status.offline: "⚫ Offline"
                    }
                    status_info.append(status_emoji.get(guild_member.status, "❓ Unknown"))
                
                if hasattr(guild_member, 'premium_since') and guild_member.premium_since:
                    boost_since = int(guild_member.premium_since.timestamp())
                    status_info.append(f"💎 Boosting since <t:{boost_since}:R>")
                
                if status_info:
                    embed.add_field(
                        name="📡 Status",
                        value="\n".join(status_info),
                        inline=True
                    )
            else:
                embed.add_field(
                    name="🏠 Server Status", 
                    value="Not a member of this server",
                    inline=True
                )
            
            # Get warning count for this user
            try:
                db = get_db_session()
                warning_count = db.query(Warning).filter(
                    Warning.guild_id == interaction.guild.id,
                    Warning.user_id == target_user.id
                ).count()
                db.close()
                
                embed.add_field(
                    name="⚠️ Warnings",
                    value=f"{warning_count} warnings on record",
                    inline=True
                )
            except Exception as e:
                logging.error(f"Error getting warning count: {e}")
            
            embed.set_footer(text=f"Requested by {interaction.user.display_name}")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logging.error(f"Error in userinfo command: {e}")
            await interaction.followup.send(
                "❌ An error occurred while fetching user information.",
                ephemeral=True
            )

    @app_commands.command(name="dashboard", description="Get the web dashboard link for bot management")
    async def dashboard(self, interaction: discord.Interaction):
        """Get the web dashboard link"""
        if not has_raid_mode_permission(interaction.user):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command.",
                ephemeral=True
            )
            return

        # Get the current host URL - use the actual Replit app URL
        import os
        replit_url = os.environ.get('REPLIT_DOMAINS', '')
        if replit_url:
            # Use the first domain from REPLIT_DOMAINS
            dashboard_url = f"https://{replit_url.split(',')[0]}"
        else:
            # Fallback URL
            dashboard_url = "https://f4660cf1-89a0-4e13-82c5-797dc2ec9aff-00-wb99purtdhd3.riker.replit.dev"
        
        embed = discord.Embed(
            title="🌐 Web Dashboard",
            description="Access the online dashboard to monitor and manage your bot",
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(
            name="Dashboard URL",
            value=f"[Click here to access the dashboard]({dashboard_url})",
            inline=False
        )
        
        embed.add_field(
            name="Features",
            value="• Real-time bot statistics\n"
                  "• Warning management and analytics\n"
                  "• Server configuration overview\n"
                  "• Cross-bot warning tracking\n"
                  "• Auto-refreshing data",
            inline=False
        )
        
        embed.add_field(
            name="Pages Available",
            value="• `/` - Main dashboard with statistics\n"
                  "• `/warnings` - Warning management\n"
                  "• `/guilds` - Server management",
            inline=False
        )
        
        embed.set_footer(text="Dashboard updates automatically every 30 seconds")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="lock", description="Lock a channel to prevent regular members from sending messages")
    @app_commands.describe(
        channel="The channel to lock (defaults to current channel)",
        reason="Reason for locking the channel"
    )
    async def lock_channel(self, interaction: discord.Interaction, channel: discord.TextChannel = None, reason: str = "No reason provided"):
        """Lock a channel to prevent regular members from sending messages"""
        if not has_raid_mode_permission(interaction.user):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command.",
                ephemeral=True
            )
            return

        target_channel = channel or interaction.channel
        
        try:
            await interaction.response.defer()
            
            # Get the @everyone role
            everyone_role = interaction.guild.default_role
            
            # Check current permissions
            current_perms = target_channel.overwrites_for(everyone_role)
            
            if current_perms.send_messages is False:
                embed = discord.Embed(
                    title="🔒 Channel Already Locked",
                    description=f"{target_channel.mention} is already locked.",
                    color=discord.Color.orange()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Store current permissions for potential unlock
            perm_data = {
                'send_messages': current_perms.send_messages,
                'add_reactions': current_perms.add_reactions,
                'create_public_threads': current_perms.create_public_threads,
                'create_private_threads': current_perms.create_private_threads,
                'send_messages_in_threads': current_perms.send_messages_in_threads
            }
            
            # Lock the channel
            await target_channel.set_permissions(
                everyone_role,
                send_messages=False,
                add_reactions=False,
                create_public_threads=False,
                create_private_threads=False,
                send_messages_in_threads=False,
                reason=f"Channel locked by {interaction.user} - {reason}"
            )
            
            # Create lock embed
            embed = discord.Embed(
                title="🔒 Channel Locked",
                description=f"{target_channel.mention} has been locked.",
                color=discord.Color.red(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=True)
            embed.set_footer(text="Use /unlock to restore channel permissions")
            
            await interaction.followup.send(embed=embed)
            
            # Send notification to the locked channel
            lock_notice = discord.Embed(
                title="🔒 This channel has been locked",
                description=f"**Reason:** {reason}\n**Moderator:** {interaction.user.mention}",
                color=discord.Color.red()
            )
            lock_notice.set_footer(text="Only staff members can send messages")
            
            await target_channel.send(embed=lock_notice)
            
            # Log the action
            logging.info(f"Channel {target_channel.name} ({target_channel.id}) locked by {interaction.user} in guild {interaction.guild.id}")
            
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ I don't have permission to modify channel permissions.",
                ephemeral=True
            )
        except Exception as e:
            logging.error(f"Error locking channel: {e}")
            await interaction.followup.send(
                "❌ An error occurred while locking the channel.",
                ephemeral=True
            )

    @app_commands.command(name="unlock", description="Unlock a channel to restore normal permissions")
    @app_commands.describe(
        channel="The channel to unlock (defaults to current channel)",
        reason="Reason for unlocking the channel"
    )
    async def unlock_channel(self, interaction: discord.Interaction, channel: discord.TextChannel = None, reason: str = "No reason provided"):
        """Unlock a channel to restore normal permissions"""
        if not has_raid_mode_permission(interaction.user):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command.",
                ephemeral=True
            )
            return

        target_channel = channel or interaction.channel
        
        try:
            await interaction.response.defer()
            
            # Get the @everyone role
            everyone_role = interaction.guild.default_role
            
            # Check if channel is actually locked
            current_perms = target_channel.overwrites_for(everyone_role)
            
            if current_perms.send_messages is not False:
                embed = discord.Embed(
                    title="🔓 Channel Not Locked",
                    description=f"{target_channel.mention} is not currently locked.",
                    color=discord.Color.orange()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Unlock the channel by removing the overwrite or restoring default permissions
            await target_channel.set_permissions(
                everyone_role,
                send_messages=None,  # Reset to default
                add_reactions=None,
                create_public_threads=None,
                create_private_threads=None,
                send_messages_in_threads=None,
                reason=f"Channel unlocked by {interaction.user} - {reason}"
            )
            
            # Create unlock embed
            embed = discord.Embed(
                title="🔓 Channel Unlocked",
                description=f"{target_channel.mention} has been unlocked.",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=True)
            
            await interaction.followup.send(embed=embed)
            
            # Send notification to the unlocked channel
            unlock_notice = discord.Embed(
                title="🔓 This channel has been unlocked",
                description=f"**Reason:** {reason}\n**Moderator:** {interaction.user.mention}",
                color=discord.Color.green()
            )
            unlock_notice.set_footer(text="Normal permissions have been restored")
            
            await target_channel.send(embed=unlock_notice)
            
            # Log the action
            logging.info(f"Channel {target_channel.name} ({target_channel.id}) unlocked by {interaction.user} in guild {interaction.guild.id}")
            
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ I don't have permission to modify channel permissions.",
                ephemeral=True
            )
        except Exception as e:
            logging.error(f"Error unlocking channel: {e}")
            await interaction.followup.send(
                "❌ An error occurred while unlocking the channel.",
                ephemeral=True
            )

    @app_commands.command(name="clear", description="Delete a specified number of messages from the channel")
    @app_commands.describe(
        amount="Number of messages to delete (1-100)",
        user="Optional: Only delete messages from this specific user"
    )
    async def clear_messages(self, interaction: discord.Interaction, amount: int, user: discord.Member = None):
        """Delete a specified number of messages from the channel"""
        if not has_raid_mode_permission(interaction.user):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command.",
                ephemeral=True
            )
            return

        if amount < 1 or amount > 100:
            await interaction.response.send_message(
                "❌ Amount must be between 1 and 100 messages.",
                ephemeral=True
            )
            return

        try:
            await interaction.response.defer()
            
            def check_message(message):
                if user:
                    return message.author == user
                return True

            deleted = await interaction.channel.purge(limit=amount, check=check_message)
            
            embed = discord.Embed(
                title="🗑️ Messages Cleared",
                description=f"Successfully deleted {len(deleted)} message(s)",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            if user:
                embed.add_field(name="Target User", value=user.mention, inline=True)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Log the action
            logging.info(f"Cleared {len(deleted)} messages in {interaction.channel.name} by {interaction.user}")
            
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ I don't have permission to delete messages in this channel.",
                ephemeral=True
            )
        except Exception as e:
            logging.error(f"Error clearing messages: {e}")
            await interaction.followup.send(
                "❌ An error occurred while clearing messages.",
                ephemeral=True
            )

    @app_commands.command(name="ban", description="Ban a user from the server")
    @app_commands.describe(
        user="The user to ban",
        reason="Reason for the ban",
        delete_messages="Delete the user's messages from the last 7 days"
    )
    async def ban_user(self, interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided", delete_messages: bool = False):
        """Ban a user from the server"""
        if not has_raid_mode_permission(interaction.user):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command.",
                ephemeral=True
            )
            return

        if user.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            await interaction.response.send_message(
                "❌ You cannot ban a user with equal or higher role than you.",
                ephemeral=True
            )
            return

        if user == interaction.user:
            await interaction.response.send_message(
                "❌ You cannot ban yourself.",
                ephemeral=True
            )
            return

        try:
            await interaction.response.defer()
            
            # Send DM to user before banning
            try:
                dm_embed = discord.Embed(
                    title="You have been banned",
                    description=f"You have been banned from **{interaction.guild.name}**",
                    color=discord.Color.red(),
                    timestamp=datetime.now(timezone.utc)
                )
                dm_embed.add_field(name="Reason", value=reason, inline=False)
                dm_embed.add_field(name="Moderator", value=str(interaction.user), inline=True)
                await user.send(embed=dm_embed)
            except:
                pass  # User has DMs disabled
            
            # Ban the user
            delete_days = 7 if delete_messages else 0
            await user.ban(reason=f"Banned by {interaction.user} - {reason}", delete_message_days=delete_days)
            
            embed = discord.Embed(
                title="🔨 User Banned",
                description=f"{user.mention} has been banned from the server",
                color=discord.Color.red(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="User", value=f"{user} ({user.id})", inline=True)
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Messages Deleted", value="Yes (7 days)" if delete_messages else "No", inline=True)
            
            await interaction.followup.send(embed=embed)
            
            # Log the action
            logging.info(f"User {user} ({user.id}) banned by {interaction.user} in guild {interaction.guild.id}")
            
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ I don't have permission to ban this user.",
                ephemeral=True
            )
        except Exception as e:
            logging.error(f"Error banning user: {e}")
            await interaction.followup.send(
                "❌ An error occurred while banning the user.",
                ephemeral=True
            )

    @app_commands.command(name="kick", description="Kick a user from the server")
    @app_commands.describe(
        user="The user to kick",
        reason="Reason for the kick"
    )
    async def kick_user(self, interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided"):
        """Kick a user from the server"""
        if not has_raid_mode_permission(interaction.user):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command.",
                ephemeral=True
            )
            return

        if user.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            await interaction.response.send_message(
                "❌ You cannot kick a user with equal or higher role than you.",
                ephemeral=True
            )
            return

        if user == interaction.user:
            await interaction.response.send_message(
                "❌ You cannot kick yourself.",
                ephemeral=True
            )
            return

        try:
            await interaction.response.defer()
            
            # Send DM to user before kicking
            try:
                dm_embed = discord.Embed(
                    title="You have been kicked",
                    description=f"You have been kicked from **{interaction.guild.name}**",
                    color=discord.Color.orange(),
                    timestamp=datetime.now(timezone.utc)
                )
                dm_embed.add_field(name="Reason", value=reason, inline=False)
                dm_embed.add_field(name="Moderator", value=str(interaction.user), inline=True)
                await user.send(embed=dm_embed)
            except:
                pass  # User has DMs disabled
            
            # Kick the user
            await user.kick(reason=f"Kicked by {interaction.user} - {reason}")
            
            embed = discord.Embed(
                title="👢 User Kicked",
                description=f"{user.mention} has been kicked from the server",
                color=discord.Color.orange(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="User", value=f"{user} ({user.id})", inline=True)
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            
            await interaction.followup.send(embed=embed)
            
            # Log the action
            logging.info(f"User {user} ({user.id}) kicked by {interaction.user} in guild {interaction.guild.id}")
            
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ I don't have permission to kick this user.",
                ephemeral=True
            )
        except Exception as e:
            logging.error(f"Error kicking user: {e}")
            await interaction.followup.send(
                "❌ An error occurred while kicking the user.",
                ephemeral=True
            )

    @app_commands.command(name="mute", description="Temporarily mute a user using Discord's timeout feature")
    @app_commands.describe(
        user="The user to mute",
        duration="Duration in minutes (1-40320, which is 28 days max)",
        reason="Reason for the mute"
    )
    async def mute_user(self, interaction: discord.Interaction, user: discord.Member, duration: int, reason: str = "No reason provided"):
        """Mute a user using Discord's timeout feature"""
        if not has_raid_mode_permission(interaction.user):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command.",
                ephemeral=True
            )
            return

        if user.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            await interaction.response.send_message(
                "❌ You cannot mute a user with equal or higher role than you.",
                ephemeral=True
            )
            return

        if user == interaction.user:
            await interaction.response.send_message(
                "❌ You cannot mute yourself.",
                ephemeral=True
            )
            return

        if duration < 1 or duration > 40320:
            await interaction.response.send_message(
                "❌ Duration must be between 1 minute and 40320 minutes (28 days).",
                ephemeral=True
            )
            return

        try:
            await interaction.response.defer()
            
            # Calculate timeout until
            import datetime as dt
            timeout_until = datetime.now(timezone.utc) + dt.timedelta(minutes=duration)
            
            # Send DM to user before muting
            try:
                dm_embed = discord.Embed(
                    title="You have been muted",
                    description=f"You have been muted in **{interaction.guild.name}**",
                    color=discord.Color.yellow(),
                    timestamp=datetime.now(timezone.utc)
                )
                dm_embed.add_field(name="Duration", value=f"{duration} minute(s)", inline=True)
                dm_embed.add_field(name="Reason", value=reason, inline=False)
                dm_embed.add_field(name="Moderator", value=str(interaction.user), inline=True)
                await user.send(embed=dm_embed)
            except:
                pass  # User has DMs disabled
            
            # Mute the user using Discord's timeout
            await user.timeout(timeout_until, reason=f"Muted by {interaction.user} - {reason}")
            
            embed = discord.Embed(
                title="🔇 User Muted",
                description=f"{user.mention} has been muted",
                color=discord.Color.yellow(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="User", value=f"{user} ({user.id})", inline=True)
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            embed.add_field(name="Duration", value=f"{duration} minute(s)", inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Expires", value=f"<t:{int(timeout_until.timestamp())}:R>", inline=True)
            
            await interaction.followup.send(embed=embed)
            
            # Log the action
            logging.info(f"User {user} ({user.id}) muted for {duration} minutes by {interaction.user} in guild {interaction.guild.id}")
            
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ I don't have permission to timeout this user.",
                ephemeral=True
            )
        except Exception as e:
            logging.error(f"Error muting user: {e}")
            await interaction.followup.send(
                "❌ An error occurred while muting the user.",
                ephemeral=True
            )

    @app_commands.command(name="unmute", description="Remove timeout from a muted user")
    @app_commands.describe(
        user="The user to unmute",
        reason="Reason for removing the mute"
    )
    async def unmute_user(self, interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided"):
        """Remove timeout from a muted user"""
        if not has_raid_mode_permission(interaction.user):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command.",
                ephemeral=True
            )
            return

        if not user.is_timed_out():
            await interaction.response.send_message(
                "❌ This user is not currently muted.",
                ephemeral=True
            )
            return

        try:
            await interaction.response.defer()
            
            # Unmute the user
            await user.timeout(None, reason=f"Unmuted by {interaction.user} - {reason}")
            
            embed = discord.Embed(
                title="🔊 User Unmuted",
                description=f"{user.mention} has been unmuted",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="User", value=f"{user} ({user.id})", inline=True)
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            
            await interaction.followup.send(embed=embed)
            
            # Log the action
            logging.info(f"User {user} ({user.id}) unmuted by {interaction.user} in guild {interaction.guild.id}")
            
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ I don't have permission to remove timeout from this user.",
                ephemeral=True
            )
        except Exception as e:
            logging.error(f"Error unmuting user: {e}")
            await interaction.followup.send(
                "❌ An error occurred while unmuting the user.",
                ephemeral=True
            )

    @app_commands.command(name="clearwarns", description="Clear all warnings for a user")
    @app_commands.describe(user="The user to clear warnings for")
    async def clear_warnings(self, interaction: discord.Interaction, user: discord.Member):
        """Clear all warnings for a user"""
        if not has_raid_mode_permission(interaction.user):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command.",
                ephemeral=True
            )
            return
            
        max_retries = 3
        for attempt in range(max_retries):
            db = None
            try:
                db = get_db_session()
                warnings_count = db.query(Warning).filter(
                    Warning.guild_id == interaction.guild.id,
                    Warning.user_id == user.id
                ).count()
                
                if warnings_count == 0:
                    await interaction.response.send_message(
                        f"{user.mention} has no warnings to clear.",
                        ephemeral=True
                    )
                    return
                
                db.query(Warning).filter(
                    Warning.guild_id == interaction.guild.id,
                    Warning.user_id == user.id
                ).delete()
                db.commit()
                
                embed = discord.Embed(
                    title="🗑️ Warnings Cleared",
                    description=f"Cleared {warnings_count} warning(s) for {user.mention}",
                    color=discord.Color.green(),
                    timestamp=datetime.now(timezone.utc)
                )
                embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
                
                await interaction.response.send_message(embed=embed)
                return  # Success
                
            except Exception as e:
                if db:
                    db.rollback()
                logging.error(f"Error clearing warnings (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    await interaction.response.send_message(
                        "❌ Database connection error. Please try again later.",
                        ephemeral=True
                    )
                else:
                    # Wait before retry
                    import asyncio
                    await asyncio.sleep(0.5)
            finally:
                if db:
                    db.close()

async def setup(bot):
    await bot.add_cog(WarningSystem(bot))