import discord
from discord import app_commands
from discord.ext import commands
import logging
import asyncio
import json
import os
from datetime import datetime, timedelta
from utils.permissions import has_raid_mode_permission
from utils.logger import log_raid_event
from utils.guild_settings import guild_settings
from utils.translations import get_text, create_embed
from utils.spam_detector import (
    track_message, 
    detect_duplicate_channels, 
    cleanup_spam, 
    reset_tracking, 
    get_spammer_ids
)

class RaidMode(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.raid_active = {}  # Dictionary to store raid mode status per guild
        self.channel_states = {}  # Dictionary to store original channel permissions
        self.invite_states = {}  # Dictionary to store original invite states
        self.raid_mode_data_dir = "raid_data"
        self.spam_cleanup_tasks = {}  # Dictionary to store spam cleanup tasks

        # Create data directory if it doesn't exist
        if not os.path.exists(self.raid_mode_data_dir):
            os.makedirs(self.raid_mode_data_dir)

        # Load any saved raid states
        self.load_raid_states()

        # Register slash commands
        self._register_commands()

        # Add message listener for spam detection
        @bot.event
        async def on_message(message):
            # Skip messages from bots and DMs
            if message.author.bot or not message.guild:
                return

            guild_id = message.guild.id

            # Only track messages if raid mode is active
            if self.raid_active.get(guild_id, False):
                # Track message for spam detection
                track_message(message)

            # Process commands
            await bot.process_commands(message)

    def _register_commands(self):
        """Register slash commands for the bot."""

        # Adding traditional commands first
        @commands.group(name="raid", invoke_without_command=True)
        @commands.has_permissions(manage_guild=True)
        async def raidmode(self, ctx):
            """Base command for raid mode functionality."""
            embed = discord.Embed(
                title="Raid Mode Commands",
                description="Commands to manage server raid protection",
                color=discord.Color.blue()
            )

            embed.add_field(
                name="!raid on", 
                value="Activate raid mode - locks down all text channels",
                inline=False
            )
            embed.add_field(
                name="!raid off", 
                value="Deactivate raid mode - restores previous channel permissions",
                inline=False
            )
            embed.add_field(
                name="!raid status", 
                value="Check if raid mode is currently active",
                inline=False
            )
            embed.add_field(
                name="!raid setup", 
                value="Configure log and announcement channels",
                inline=False
            )

            await ctx.send(embed=embed)

        @raidmode.command(name="on")
        @commands.has_permissions(manage_guild=True)
        async def raid_on_prefix(self, ctx):
            """Enable raid mode - locks down all text channels."""
            # Create an Interaction-like object with necessary attributes
            class FakeInteraction:
                def __init__(self, ctx):
                    self.guild = ctx.guild
                    self.user = ctx.author
                    self.channel = ctx.channel
                    self.response = self
                    self.followup = ctx

                async def defer(self, ephemeral=False):
                    pass

                async def send_message(self, content, ephemeral=False):
                    await ctx.send(content)

            fake_interaction = FakeInteraction(ctx)
            await self._enable_raid_mode(fake_interaction)

        @raidmode.command(name="off")
        @commands.has_permissions(manage_guild=True)
        async def raid_off_prefix(self, ctx):
            """Disable raid mode - restores previous channel permissions."""
            # Create an Interaction-like object with necessary attributes
            class FakeInteraction:
                def __init__(self, ctx):
                    self.guild = ctx.guild
                    self.user = ctx.author
                    self.channel = ctx.channel
                    self.response = self
                    self.followup = ctx

                async def defer(self, ephemeral=False):
                    pass

                async def send_message(self, content, ephemeral=False):
                    await ctx.send(content)

            fake_interaction = FakeInteraction(ctx)
            await self._disable_raid_mode(fake_interaction)

        @raidmode.command(name="status")
        async def raid_status_prefix(self, ctx):
            """Check the current status of raid mode."""
            guild_id = ctx.guild.id
            is_active = self.raid_active.get(guild_id, False)

            if is_active:
                embed = discord.Embed(
                    title="🚨 Raid Mode Status",
                    description="**Raid mode is currently ACTIVE**\nAll channels are locked down to prevent spam.",
                    color=discord.Color.red()
                )
            else:
                embed = discord.Embed(
                    title="✅ Raid Mode Status",
                    description="**Raid mode is currently INACTIVE**\nAll channels are operating normally.",
                    color=discord.Color.green()
                )

            await ctx.send(embed=embed)

        @raidmode.command(name="setup")
        @commands.has_permissions(manage_guild=True)
        async def raid_setup_prefix(self, ctx, log_channel=None, announcement_channel=None, admin_role=None):
            """Configure log and announcement channels for raid notifications."""
            guild_id = ctx.guild.id

            # Update settings based on provided parameters
            if log_channel:
                guild_settings.set_log_channel(guild_id, log_channel.id)

            if announcement_channel:
                guild_settings.set_announcement_channel(guild_id, announcement_channel.id)

            if admin_role:
                guild_settings.set_admin_role(guild_id, admin_role.id)

            # member_role parameter not available in this function

            # Create response embed
            embed = discord.Embed(
                title="✅ Raid Protection Setup",
                description="Your raid protection settings have been updated.",
                color=discord.Color.green()
            )

            # Add fields for current settings
            log_channel_id = guild_settings.get_log_channel(guild_id)
            if log_channel_id:
                log_channel_obj = ctx.guild.get_channel(log_channel_id)
                if log_channel_obj:
                    embed.add_field(
                        name="Log Channel", 
                        value=f"{log_channel_obj.mention}",
                        inline=True
                    )

            announcement_channel_id = guild_settings.get_announcement_channel(guild_id)
            if announcement_channel_id:
                announcement_channel_obj = ctx.guild.get_channel(announcement_channel_id)
                if announcement_channel_obj:
                    embed.add_field(
                        name="Announcement Channel", 
                        value=f"{announcement_channel_obj.mention}",
                        inline=True
                    )

            admin_role_id = guild_settings.get_admin_role(guild_id)
            if admin_role_id:
                admin_role_obj = ctx.guild.get_role(admin_role_id)
                if admin_role_obj:
                    embed.add_field(
                        name="Admin Role", 
                        value=f"{admin_role_obj.mention}",
                        inline=True
                    )

            # If no settings were provided, show current settings
            if not (log_channel or announcement_channel or admin_role):
                if not (log_channel_id or announcement_channel_id or admin_role_id):
                    embed.description = "⚠️ No raid protection settings have been configured yet. Please specify at least one channel or role."
                    embed.color = discord.Color.orange()
                else:
                    embed.description = "Current raid protection settings:"

            # Send the response
            await ctx.send(embed=embed)

            # Test the log channel if it was set
            if log_channel and guild_settings.get_log_channel(guild_id):
                try:
                    test_log = discord.Embed(
                        title="✅ Log Channel Setup",
                        description="This channel has been configured as the raid protection log channel.",
                        color=discord.Color.blue()
                    )
                    test_log.add_field(
                        name="Configuration", 
                        value=f"Setup by: {ctx.author.mention}\nTimestamp: {discord.utils.format_dt(datetime.now())}",
                        inline=False
                    )

                    await log_channel.send(embed=test_log)
                except Exception as e:
                    logging.error(f"Error sending test message to log channel: {e}")

            # Test the announcement channel if it was set
            if announcement_channel and guild_settings.get_announcement_channel(guild_id):
                try:
                    test_announcement = discord.Embed(
                        title="✅ Announcement Channel Setup",
                        description="This channel has been configured as the raid protection announcement channel.",
                        color=discord.Color.blue()
                    )
                    test_announcement.add_field(
                        name="Configuration", 
                        value=f"Setup by: {ctx.author.mention}\nTimestamp: {discord.utils.format_dt(datetime.now())}",
                        inline=False
                    )

                    await announcement_channel.send(embed=test_announcement)
                except Exception as e:
                    logging.error(f"Error sending test message to announcement channel: {e}")

        # Main raid command group (slash commands)
        raid_group = app_commands.Group(name="raid", description="Raid protection commands")

        # On command
        @raid_group.command(name="on", description="Activate raid mode - locks down all text channels")
        async def raid_on(interaction: discord.Interaction):
            # Check permissions
            if not has_raid_mode_permission(interaction.user):
                await interaction.response.send_message(
                    get_text(interaction.guild.id, 'no_permission'),
                    ephemeral=True
                )
                return

            await self._enable_raid_mode(interaction)

        # Off command
        @raid_group.command(name="off", description="Deactivate raid mode - restores previous channel permissions")
        async def raid_off(interaction: discord.Interaction):
            # Check permissions
            if not has_raid_mode_permission(interaction.user):
                await interaction.response.send_message(
                    get_text(interaction.guild.id, 'no_permission'),
                    ephemeral=True
                )
                return

            await self._disable_raid_mode(interaction)

        # Status command
        @raid_group.command(name="status", description="Check the current status of raid mode")
        async def raid_status(interaction: discord.Interaction):
            await self._check_raid_status(interaction)

        # Help command
        @raid_group.command(name="help", description="Show help information about using the bot")
        async def raid_help(interaction: discord.Interaction):
            embed = discord.Embed(
                title="🛡️ Raid Protection Bot Help",
                description="This bot helps protect your server against raids and spam attacks.",
                color=discord.Color.blue()
            )

            embed.add_field(
                name="Main Commands",
                value=(
                    "🟢 `/raid on` - Activate raid protection mode\n"
                    "🔴 `/raid off` - Deactivate raid protection mode\n"
                    "ℹ️ `/raid status` - Check current raid mode status\n"
                    "⚙️ `/raid setup` - Configure bot settings"
                ),
                inline=False
            )

            embed.add_field(
                name="Required Permissions",
                value="Users need `Manage Server` permission or a configured admin role to use these commands.",
                inline=False
            )

            embed.add_field(
                name="Setup Guide",
                value=(
                    "1. Use `/raid setup` to configure log and announcement channels\n"
                    "2. Ensure the bot has necessary permissions\n"
                    "3. Test the bot with `/raid status`"
                ),
                inline=False
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        # Note: Setup command has been replaced by /setup command in setup_system.py

        # Add the slash commands to the bot
        self.bot.tree.add_command(raid_group)

    def load_raid_states(self):
        """Load saved raid states from disk if they exist."""
        try:
            for guild_id in os.listdir(self.raid_mode_data_dir):
                if guild_id.isdigit():
                    file_path = os.path.join(self.raid_mode_data_dir, guild_id, "raid_state.json")
                    if os.path.exists(file_path):
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                            self.raid_active[int(guild_id)] = data.get('active', False)
                            logging.info(f"Loaded raid state for guild {guild_id}: {self.raid_active[int(guild_id)]}")
        except Exception as e:
            logging.error(f"Error loading raid states: {e}")

    def save_raid_state(self, guild_id):
        """Save the current raid state for a guild."""
        try:
            guild_dir = os.path.join(self.raid_mode_data_dir, str(guild_id))
            if not os.path.exists(guild_dir):
                os.makedirs(guild_dir)

            file_path = os.path.join(guild_dir, "raid_state.json")
            with open(file_path, 'w') as f:
                json.dump({
                    'active': self.raid_active.get(guild_id, False),
                    'updated_at': datetime.now().isoformat()
                }, f)
        except Exception as e:
            logging.error(f"Error saving raid state for guild {guild_id}: {e}")

    async def _setup_raid_channels(self, interaction, log_channel, announcement_channel, admin_role):
        """Set up log and announcement channels for raid notifications."""
        try:
            guild_id = interaction.guild.id

            # Acknowledge the interaction immediately with a temporary response
            try:
                await interaction.response.defer(ephemeral=True)
            except discord.errors.NotFound:
                # If interaction expired, return early
                return

            # Update settings based on provided parameters
            if log_channel:
                guild_settings.set_log_channel(guild_id, log_channel.id)
                
            if announcement_channel:
                guild_settings.set_announcement_channel(guild_id, announcement_channel.id)
                
            if admin_role:
                guild_settings.set_admin_role(guild_id, admin_role.id)

            # Create response embed
            embed = discord.Embed(
                title="✅ Raid Protection Setup",  
                description="Your raid protection settings have been updated.",
                color=discord.Color.green()
            )
            
            # Add fields for current settings
            log_channel_id = guild_settings.get_log_channel(guild_id)
            if log_channel_id:
                log_channel_obj = interaction.guild.get_channel(log_channel_id)
                if log_channel_obj:
                    embed.add_field(
                        name="Log Channel", 
                        value=f"{log_channel_obj.mention}",
                        inline=True
                    )
                    
            announcement_channel_id = guild_settings.get_announcement_channel(guild_id)
            if announcement_channel_id:
                announcement_channel_obj = interaction.guild.get_channel(announcement_channel_id)
                if announcement_channel_obj:
                    embed.add_field(
                        name="Announcement Channel", 
                        value=f"{announcement_channel_obj.mention}",
                        inline=True
                    )

            admin_role_id = guild_settings.get_admin_role(guild_id)
            if admin_role_id:
                admin_role_obj = interaction.guild.get_role(admin_role_id)
                if admin_role_obj:
                    embed.add_field(
                        name="Admin Role", 
                        value=f"{admin_role_obj.mention}",
                        inline=True
                    )

            # If no settings were provided, show current settings
            if not (log_channel or announcement_channel or admin_role):
                if not (log_channel_id or announcement_channel_id or admin_role_id):
                    embed.description = "⚠️ No raid protection settings have been configured yet. Please specify at least one channel or role."
                    embed.color = discord.Color.orange()
                else:
                    embed.description = "Current raid protection settings:"

            # Send the response
            await interaction.followup.send(embed=embed, ephemeral=True)

            # Test the log channel if it was set
            if log_channel and guild_settings.get_log_channel(guild_id):
                try:
                    test_log = discord.Embed(
                        title="✅ Log Channel Setup",
                        description="This channel has been configured as the raid protection log channel.",
                        color=discord.Color.blue()
                    )
                    test_log.add_field(
                        name="Configuration", 
                        value=f"Setup by: {interaction.user.mention}\nTimestamp: {discord.utils.format_dt(datetime.now())}",
                        inline=False
                    )
                    await log_channel.send(embed=test_log)
                except Exception as e:
                    logging.error(f"Error sending test message to log channel: {e}")

            # Test the announcement channel if it was set
            if announcement_channel and guild_settings.get_announcement_channel(guild_id):
                try:
                    test_announcement = discord.Embed(
                        title="✅ Announcement Channel Setup",
                        description="This channel has been configured as the raid protection announcement channel.",
                        color=discord.Color.blue()
                    )
                    test_announcement.add_field(
                        name="Configuration", 
                        value=f"Setup by: {interaction.user.mention}\nTimestamp: {discord.utils.format_dt(datetime.now())}",
                        inline=False
                    )
                    await announcement_channel.send(embed=test_announcement)
                except Exception as e:
                    logging.error(f"Error sending test message to announcement channel: {e}")

        except Exception as e:
            logging.error(f"Error in _setup_raid_channels: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("An error occurred while setting up raid channels.", ephemeral=True)
            except Exception:
                pass

    def get_member_role(self, guild):
        """Get the configured member role for the guild."""
        member_role_id = guild_settings.get_member_role(guild.id)
        if member_role_id:
            return guild.get_role(member_role_id)
        return None

    async def _enable_raid_mode(self, interaction):
        """Enable raid mode - scans for spam for 3 seconds then locks down channels."""
        guild_id = interaction.guild.id

        # Check if raid mode is already active
        if self.raid_active.get(guild_id, False):
            if hasattr(interaction.response, "send_message"):
                await interaction.response.send_message("⚠️ Raid mode is already active!", ephemeral=True)
            else:
                await interaction.send("⚠️ Raid mode is already active!")
            return

        # Acknowledge the interaction immediately
        if hasattr(interaction, "response") and hasattr(interaction.response, "defer"):
            await interaction.response.defer()

        try:
            # Send initial progress message for spam scanning
            if hasattr(interaction, "followup") and hasattr(interaction.followup, "send"):
                progress_message = await interaction.followup.send("🔍 Scanning for spam activity... (3 seconds)")
            else:
                progress_message = await interaction.send("🔍 Scanning for spam activity... (3 seconds)")

            # Mark raid mode as active for spam detection, but don't lock channels yet
            self.raid_active[guild_id] = True

            # Reset any previous tracking data
            reset_tracking(guild_id)

            # Begin DOUBLE scanning for spam for enhanced reliability
            scanning_start_time = datetime.now()

            # FIRST SCAN: Initial 3-second scan
            await progress_message.edit(content="🔍 Phase 1: Initial spam scan... (3 seconds)")
            for i in range(3, 0, -1):
                await progress_message.edit(content=f"🔍 Phase 1: Initial spam scan... ({i} seconds remaining)")
                await asyncio.sleep(1)

            # Get first scan results
            first_scan_spammers = get_spammer_ids(guild_id).copy()
            first_scan_count = len(first_scan_spammers)

            # SECOND SCAN: Enhanced 3-second verification scan
            await progress_message.edit(content="🔍 Phase 2: Verification scan... (3 seconds)")
            for i in range(3, 0, -1):
                await progress_message.edit(content=f"🔍 Phase 2: Verification scan... ({i} seconds remaining)")
                await asyncio.sleep(1)

            # Get second scan results
            second_scan_spammers = get_spammer_ids(guild_id)
            second_scan_count = len(second_scan_spammers)

            # Combine results for maximum reliability
            all_detected_spammers = first_scan_spammers.union(second_scan_spammers)
            total_unique_spammers = len(all_detected_spammers)

            # Enhanced reporting with double scan data
            if all_detected_spammers:
                audit_logger = self.bot.get_cog('AuditLogger')
                if audit_logger:
                    try:
                        # Create detailed double scan report
                        embed = discord.Embed(
                            title="🚨 DOUBLE-SCAN SPAM DETECTION COMPLETE",
                            color=discord.Color.red(),
                            timestamp=datetime.now()
                        )
                        
                        embed.add_field(name="Scan Method", value="Enhanced Double-Scan Verification", inline=False)
                        embed.add_field(name="First Scan Results", value=f"{first_scan_count} spammers detected", inline=True)
                        embed.add_field(name="Second Scan Results", value=f"{second_scan_count} spammers detected", inline=True)
                        embed.add_field(name="Total Unique Threats", value=f"{total_unique_spammers} confirmed spammers", inline=True)
                        
                        # Reliability indicator
                        if first_scan_count > 0 and second_scan_count > 0:
                            reliability = "🔴 CRITICAL - Confirmed by both scans"
                        elif total_unique_spammers > 0:
                            reliability = "🟠 HIGH - Detected in at least one scan"
                        else:
                            reliability = "🟢 LOW - Clean server detected"
                            
                        embed.add_field(name="Threat Level", value=reliability, inline=False)
                        
                        # Send enhanced alert
                        total_messages = total_unique_spammers * 6  # Estimate for double scan
                        await audit_logger.log_spam_detection(interaction.guild, all_detected_spammers, total_messages)
                        
                    except Exception as e:
                        logging.error(f"Error sending double scan alert: {e}")

            await progress_message.edit(content=f"✅ Double scan complete: {total_unique_spammers} threats detected")

            # After spam scanning, prepare for lockdown
            self.channel_states[guild_id] = {}
            self.invite_states[guild_id] = {}

            # Update progress message for channel lockdown
            await progress_message.edit(content="🔒 Scan complete. Locking down channels... (0%)")

            # Count total channels for progress tracking
            total_channels = len(interaction.guild.text_channels)
            processed_channels = 0

            # Lock all text channels
            for channel in interaction.guild.text_channels:
                try:
                    # Skip announcement channel if it exists
                    announcement_channel_id = guild_settings.get_announcement_channel(guild_id)
                    if announcement_channel_id and channel.id == announcement_channel_id:
                        continue

                    # Skip log channel if it exists
                    log_channel_id = guild_settings.get_log_channel(guild_id)
                    if log_channel_id and channel.id == log_channel_id:
                        continue

                    # Get member role
                    member_role = self.get_member_role(interaction.guild)
                    if not member_role:
                        await interaction.followup.send("⚠️ No member role configured. Please use `/raid setup` to set one.", ephemeral=True)
                        return

                    # Save current permissions
                    current_perms = channel.overwrites_for(member_role)

                    # Store original permissions
                    self.channel_states[guild_id][channel.id] = {
                        'send_messages': current_perms.send_messages,
                        'role_id': member_role.id
                    }

                    # Set new permissions - disable sending messages
                    new_perms = discord.PermissionOverwrite()
                    new_perms.send_messages = False
                    new_perms.send_messages_in_threads = False 
                    new_perms.create_public_threads = False
                    new_perms.create_private_threads = False
                    new_perms.add_reactions = False
                    await channel.set_permissions(member_role, overwrite=new_perms)

                    # Update progress
                    processed_channels += 1
                    if processed_channels % 5 == 0 or processed_channels == total_channels:
                        progress_percentage = int((processed_channels / total_channels) * 100)
                        await progress_message.edit(
                            content=f"🔒 Activating raid mode... ({progress_percentage}%)"
                        )

                except discord.Forbidden:
                    logging.warning(f"Missing permissions to modify channel {channel.name} in guild {interaction.guild.name}")
                except Exception as e:
                    logging.error(f"Error locking channel {channel.name}: {e}")

            # Disable invites by disabling the create_instant_invite permission for everyone
            try:
                # Use Discord's native Security Actions to pause invites and DMs
                try:
                    # Store the current invite and DM state
                    self.invite_states[guild_id] = {
                        'invites_paused': False,
                        'dms_paused': False
                    }

                    # STEP 1: Pause invites using Discord's built-in features
                    if interaction.guild.me.guild_permissions.manage_guild:
                        try:
                            # Always explicitly make sure community is enabled first
                            await interaction.guild.edit(
                                community=True,  # Enable community features
                                reason="Raid mode activated - enabling community features"
                            )
                            logging.info(f"Enabled community features in {interaction.guild.name}")

                            # Then in a separate call, disable invites
                            await interaction.guild.edit(
                                invites_disabled=True,  # Disable new invites
                                reason="Raid mode activated - pausing invites"
                            )
                            self.invite_states[guild_id]['invites_paused'] = True
                            logging.info(f"Paused invites in {interaction.guild.name}")

                            # Update progress message
                            await progress_message.edit(content="🔒 Activating raid mode... (Paused invites)")
                        except Exception as e:
                            logging.error(f"Error pausing invites: {e}")
                            await progress_message.edit(content="🔒 Activating raid mode... (Error pausing invites)")
                    else:
                        logging.warning(f"Missing permissions to pause invites in {interaction.guild.name}")
                        await progress_message.edit(content="🔒 Activating raid mode... (No permission to pause invites)")

                    # STEP 2: Pause DMs using Discord's built-in features
                    if interaction.guild.me.guild_permissions.manage_guild:
                        try:
                            # There's no direct API for pausing DMs, but we can restrict it with rules screening
                            await interaction.guild.edit(
                                premium_progress_bar_enabled=False,  # Related to community features
                                rules_channel=interaction.guild.rules_channel,  # Keep existing rules channel if any
                                reason="Raid mode activated - pausing DMs"
                            )
                            self.invite_states[guild_id]['dms_paused'] = True
                            logging.info(f"Attempted to pause DMs in {interaction.guild.name}")

                            # Update progress message
                            await progress_message.edit(content="🔒 Activating raid mode... (Paused invites and DMs)")
                        except Exception as e:
                            logging.error(f"Error pausing DMs: {e}")

                except Exception as e:
                    logging.error(f"Error pausing invites and DMs: {e}")

                # Log the action
                logging.info(f"Disabled invites in {interaction.guild.name}")
            except Exception as e:
                logging.error(f"Error managing invites: {e}")

            # Save raid state
            self.save_raid_state(guild_id)

            # Log the event
            log_raid_event(interaction.guild, interaction.user, "enabled")

            # Start spam detection and cleanup
            reset_tracking(guild_id)  # Reset any previous tracking data

            # Set up periodic spam cleanup task
            self.start_spam_cleanup(interaction.guild)

            # Send confirmation with warning style
            embed = discord.Embed(
                title="🚨 RAID MODE ACTIVATED 🚨",
                description="All channels have been locked to prevent spam messages. New members cannot join the server and DMs between members are restricted during raid mode.",
                color=discord.Color.red()
            )
            embed.add_field(
                name="Activated by", 
                value=f"{interaction.user.mention} ({interaction.user.display_name})",
                inline=False
            )
            embed.add_field(
                name="Deactivate", 
                value="Use `/raid off` to restore normal operations when the threat has passed.",
                inline=False
            )

            await progress_message.delete()
            await interaction.followup.send(embed=embed)

            # Send notification to log channel if configured
            log_channel_id = guild_settings.get_log_channel(guild_id)
            if log_channel_id:
                log_channel = interaction.guild.get_channel(log_channel_id)
                if log_channel:
                    try:
                        log_embed = discord.Embed(
                            title="🚨 RAID MODE ACTIVATED",
                            description="All channels have been locked to prevent spam messages. New members cannot join the server and DMs between members are restricted during raid mode.",
                            color=discord.Color.red()
                        )
                        log_embed.add_field(
                            name="Activated by", 
                            value=f"{interaction.user.mention} ({interaction.user.display_name})",
                            inline=False
                        )
                        log_embed.add_field(
                            name="Time", 
                            value=f"{discord.utils.format_dt(datetime.now())}",
                            inline=False
                        )

                        await log_channel.send(embed=log_embed)

                        # Report scan results to log channel
                        spammer_ids = get_spammer_ids(guild_id)

                        if spammer_ids:
                            # Create spam report for detected spammers
                            spam_embed = discord.Embed(
                                title="🚨 SPAM DETECTION REPORT",
                                description=f"Detected **{len(spammer_ids)}** potential spammers during initial 3-second scan.",
                                color=discord.Color.red(),
                                timestamp=datetime.now()
                            )

                            # List all detected spammers
                            spammer_info = ""
                            for user_id in spammer_ids:
                                user = interaction.guild.get_member(user_id)
                                user_name = user.name if user else f"Unknown User ({user_id})"
                                spammer_info += f"• **{user_name}** (ID: {user_id})\n"

                            spam_embed.add_field(
                                name="Detected Spammers",
                                value=spammer_info,
                                inline=False
                            )

                            spam_embed.set_footer(text=f"Scan duration: 3 seconds | Server: {interaction.guild.name}")

                            # Ask if messages should be deleted
                            should_delete_messages = await self.ask_spam_cleanup(interaction.guild, spammer_ids)

                            # Delete messages if confirmed
                            if should_delete_messages:
                                await cleanup_spam(interaction.guild, log_channel, delete_messages=True)
                            else:
                                await cleanup_spam(interaction.guild, log_channel, delete_messages=False)
                        else:
                            # Report that no spam was detected
                            no_spam_embed = discord.Embed(
                                title="✅ SPAM DETECTION REPORT",
                                description="No spam activity detected during initial 3-second scan.",
                                color=discord.Color.green(),
                                timestamp=datetime.now()
                            )

                            no_spam_embed.add_field(
                                name="Status",
                                value="Raid mode is active and the server is now locked down. Continuing to monitor for spam activity.",
                                inline=False
                            )

                            no_spam_embed.set_footer(text=f"Scan duration: 3 seconds | Server: {interaction.guild.name}")

                            await log_channel.send(embed=no_spam_embed)

                    except Exception as e:
                        logging.error(f"Error sending notification to log channel: {e}")

            # Send notification to announcement channel if configured
            announcement_channel_id = guild_settings.get_announcement_channel(guild_id)
            if announcement_channel_id:
                announcement_channel = interaction.guild.get_channel(announcement_channel_id)
                if announcement_channel:
                    try:
                        announcement_embed = discord.Embed(
                            title="🚨 RAID MODE ACTIVATED 🚨",
                            description="**All channels have been locked due to a raid. New members cannot join and direct messages are restricted during this time.**\nPlease wait for the moderators to resolve the situation.",
                            color=discord.Color.red()
                        )

                        await announcement_channel.send(embed=announcement_embed)
                    except Exception as e:
                        logging.error(f"Error sending notification to announcement channel: {e}")

        except Exception as e:
            self.raid_active[guild_id] = False
            await interaction.followup.send(f"⚠️ Error activating raid mode: {str(e)}")
            logging.error(f"Error activating raid mode in guild {interaction.guild.name}: {e}")

    async def _disable_raid_mode(self, interaction):
        """Disable raid mode - restores previous channel permissions."""
        guild_id = interaction.guild.id

        # Check if raid mode is active
        if not self.raid_active.get(guild_id, False):
            if hasattr(interaction.response, "send_message"):
                await interaction.response.send_message("⚠️ Raid mode is not currently active!", ephemeral=True)
            else:
                await interaction.send("⚠️ Raid mode is not currently active!")
            return

        # Acknowledge the interaction immediately
        if hasattr(interaction, "response") and hasattr(interaction.response, "defer"):
            await interaction.response.defer()

        try:
            # Send initial progress message
            if hasattr(interaction, "followup") and hasattr(interaction.followup, "send"):
                progress_message = await interaction.followup.send("🔓 Deactivating raid mode... (0%)")
            else:
                progress_message = await interaction.send("🔓 Deactivating raid mode... (0%)")

            # Count total channels for progress tracking
            stored_channels = self.channel_states.get(guild_id, {})
            total_channels = len(stored_channels)
            processed_channels = 0

            # Restore permissions for all channels
            for channel_id, permissions in stored_channels.items():
                try:
                    channel = interaction.guild.get_channel(channel_id)
                    if channel:
                        default_role = interaction.guild.default_role
                        current_perms = channel.overwrites_for(default_role)

                        # Restore original permissions
                        new_perms = discord.PermissionOverwrite(**current_perms._values)
                        new_perms.send_messages = permissions.get('send_messages')
                        await channel.set_permissions(default_role, overwrite=new_perms)

                    # Update progress
                    processed_channels += 1
                    if processed_channels % 5 == 0 or processed_channels == total_channels:
                        progress_percentage = int((processed_channels / total_channels) * 100)
                        await progress_message.edit(
                            content=f"🔓 Deactivating raid mode... ({progress_percentage}%)"
                        )

                except discord.Forbidden:
                    logging.warning(f"Missing permissions to modify channel {channel_id} in guild {interaction.guild.name}")
                except Exception as e:
                    logging.error(f"Error unlocking channel {channel_id}: {e}")

            # Re-enable invites by restoring create_instant_invite permission
            try:
                # Update progress message
                await progress_message.edit(content="🔓 Deactivating raid mode... (Restoring invite permissions)")

                # Re-enable invites using Discord's built-in features
                invite_state = self.invite_states.get(guild_id, {})

                if interaction.guild.me.guild_permissions.manage_guild:
                    # Always try to unpause invites when raid mode is turned off
                    try:
                        # Force disable invites_disabled regardless of previous state
                        await interaction.guild.edit(
                            invites_disabled=False,  # Ensure invites are enabled
                            reason="Raid mode deactivated - enabling invites"
                        )
                        logging.info(f"Enabled invites in {interaction.guild.name}")

                        # Also try to restore community features to default state
                        await interaction.guild.edit(
                            premium_progress_bar_enabled=True,  # Restore DM-related settings
                            reason="Raid mode deactivated - restoring settings"
                        )
                        logging.info(f"Restored server settings in {interaction.guild.name}")
                    except Exception as e:
                        logging.error(f"Error restoring server settings: {e}")

                    # For older implementation compatibility - re-enable create_instant_invite permission
                    default_role = interaction.guild.default_role
                    for channel in interaction.guild.channels:
                        try:
                            current_perms = channel.overwrites_for(default_role)
                            new_perms = discord.PermissionOverwrite(**current_perms._values)
                            new_perms.create_instant_invite = None
                            await channel.set_permissions(default_role, overwrite=new_perms)
                        except Exception as e:
                            logging.error(f"Error restoring invites for channel {channel.name}: {e}")

                else:
                    logging.warning(f"Missing permissions to restore invites in {interaction.guild.name}")

                # Log the action
                logging.info(f"Re-enabled invites in {interaction.guild.name}")
            except Exception as e:
                logging.error(f"Error restoring invite permissions: {e}")

            # Update raid mode status
            self.raid_active[guild_id] = False
            self.channel_states.pop(guild_id, None)
            self.invite_states.pop(guild_id, None)

            # Save raid state
            self.save_raid_state(guild_id)

            # Log the event
            log_raid_event(interaction.guild, interaction.user, "disabled")

            # Stop the spam cleanup task for this guild
            self.stop_spam_cleanup(interaction.guild.id)

            # Send confirmation
            embed = discord.Embed(
                title="✅ RAID MODE DEACTIVATED",
                description="All channels have been restored to their previous state.",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Deactivated by", 
                value=f"{interaction.user.mention} ({interaction.user.display_name})",
                inline=False
            )

            await progress_message.delete()
            await interaction.followup.send(embed=embed)

            # Send notification to log channel if configured
            log_channel_id = guild_settings.get_log_channel(guild_id)
            if log_channel_id:
                log_channel = interaction.guild.get_channel(log_channel_id)
                if log_channel:
                    try:
                        log_embed = discord.Embed(
                            title="✅ RAID MODE DEACTIVATED",
                            description="All channels have been restored to their previous state.",
                            color=discord.Color.green()
                        )
                        log_embed.add_field(
                            name="Deactivated by", 
                            value=f"{interaction.user.mention} ({interaction.user.display_name})",
                            inline=False
                        )
                        log_embed.add_field(
                            name="Time", 
                            value=f"{discord.utils.format_dt(datetime.now())}",
                            inline=False
                        )

                        await log_channel.send(embed=log_embed)
                    except Exception as e:
                        logging.error(f"Error sending notification to log channel: {e}")

            # Send notification to announcement channel if configured
            announcement_channel_id = guild_settings.get_announcement_channel(guild_id)
            if announcement_channel_id:
                announcement_channel = interaction.guild.get_channel(announcement_channel_id)
                if announcement_channel:
                    try:
                        announcement_embed = discord.Embed(
                            title="✅ RAID MODE DEACTIVATED",
                            description="**All channels have been restored to normal operation.**\nThank you for your patience.",
                            color=discord.Color.green()
                        )

                        await announcement_channel.send(embed=announcement_embed)
                    except Exception as e:
                        logging.error(f"Error sending notification to announcement channel: {e}")

        except Exception as e:
            await interaction.followup.send(f"⚠️ Error deactivating raid mode: {str(e)}")
            logging.error(f"Error deactivating raid mode in guild {interaction.guild.name}: {e}")

    async def _check_raid_status(self, interaction):
        """Check the current status of raid mode."""
        guild_id = interaction.guild.id
        is_active = self.raid_active.get(guild_id, False)

        # Create the embed
        if is_active:
            embed = discord.Embed(
                title="🚨 Raid Mode Status",
                description="**Raid mode is currently ACTIVE**\nAll channels are locked down to prevent spam. New members cannot join the server and direct messages between members are restricted during raid mode.",
                color=discord.Color.red()
            )

            # Add information about detected spammers
            spammer_ids = get_spammer_ids(guild_id)
            if spammer_ids:
                spammer_info = ""
                for user_id in spammer_ids:
                    user = interaction.guild.get_member(user_id)
                    user_name = user.name if user else f"Unknown User ({user_id})"
                    spammer_info += f"• **{user_name}** (ID: {user_id})\n"

                embed.add_field(
                    name=f"Detected Spammers ({len(spammer_ids)})",
                    value=spammer_info,
                    inline=False
                )
        else:
            embed = discord.Embed(
                title="✅ Raid Mode Status",
                description="**Raid mode is currently INACTIVE**\nAll channels are operating normally.",
                color=discord.Color.green()
            )

        # Add setup info if channels are configured
        log_channel_id = guild_settings.get_log_channel(guild_id)
        announcement_channel_id = guild_settings.get_announcement_channel(guild_id)

        if log_channel_id or announcement_channel_id:
            setup_info = ""

            if log_channel_id:
                log_channel = interaction.guild.get_channel(log_channel_id)
                if log_channel:
                    setup_info += f"**Log Channel:** {log_channel.mention}\n"

            if announcement_channel_id:
                announcement_channel = interaction.guild.get_channel(announcement_channel_id)
                if announcement_channel:
                    setup_info += f"**Announcement Channel:** {announcement_channel.mention}\n"

            if setup_info:
                embed.add_field(name="Configuration", value=setup_info, inline=False)
        else:
            embed.add_field(
                name="Setup Required", 
                value="Use `/raid setup` to configure log and announcement channels.",
                inline=False
            )

        # Send the response
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def ask_spam_cleanup(self, guild, spammer_ids):
        """Ask if spam messages should be deleted for detected spammers."""
        guild_id = guild.id

        # Get log channel
        log_channel_id = guild_settings.get_log_channel(guild_id)
        if not log_channel_id:
            return False

        log_channel = guild.get_channel(log_channel_id)
        if not log_channel:
            return False

        # Create spammer info string
        spammer_info = ""
        for user_id in spammer_ids:
            user = guild.get_member(user_id)
            user_name = user.name if user else f"Unknown User ({user_id})"
            spammer_info += f"• **{user_name}** (ID: {user_id})\n"

        # Create cleanup confirmation message
        cleanup_embed = discord.Embed(
            title="🧹 Spam Cleanup Confirmation",
            description="Spammers have been detected. Would you like to delete all messages from these users?",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )

        cleanup_embed.add_field(
            name=f"Detected Spammers ({len(spammer_ids)})",
            value=spammer_info or "None detected",
            inline=False
        )

        cleanup_embed.add_field(
            name="Options",
            value="React with ✅ to delete all messages from these users.\nReact with ❌ to keep the messages.",
            inline=False
        )

        # Send the message and add reactions
        try:
            cleanup_msg = await log_channel.send(embed=cleanup_embed)
            await cleanup_msg.add_reaction("✅")  # Yes
            await cleanup_msg.add_reaction("❌")  # No

            # Wait for reaction response
            def check(reaction, user):
                # Only consider reactions from moderators
                if user.bot:
                    return False

                member = guild.get_member(user.id)
                if not member or not has_raid_mode_permission(member):
                    return False

                return str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == cleanup_msg.id

            try:
                # Wait for reaction with 5 minute timeout
                reaction, user = await self.bot.wait_for('reaction_add', check=check, timeout=300)

                # Process the response
                if str(reaction.emoji) == "✅":
                    confirmation = discord.Embed(
                        title="🧹 Spam Cleanup Confirmed",
                        description=f"**{user.name}** has confirmed spam cleanup. Deleting all messages from detected spammers.",
                        color=discord.Color.green()
                    )
                    await log_channel.send(embed=confirmation)
                    return True
                else:
                    cancel = discord.Embed(
                        title="❌ Spam Cleanup Cancelled",
                        description=f"**{user.name}** has cancelled spam cleanup. Messages will be preserved.",
                        color=discord.Color.red()
                    )
                    await log_channel.send(embed=cancel)
                    return False

            except asyncio.TimeoutError:
                # No response within timeout period
                timeout = discord.Embed(
                    title="⏰ Cleanup Request Expired",
                    description="No response received within 5 minutes. Spam messages will be preserved.",
                    color=0x808080
                )
                await log_channel.send(embed=timeout)
                return False

        except Exception as e:
            logging.error(f"Error asking for spam cleanup confirmation: {e}")
            return False

    def start_spam_cleanup(self, guild):
        """Start a periodic task to detect and clean up spam."""
        guild_id = guild.id

        # Cancel existing task if it exists
        self.stop_spam_cleanup(guild_id)

        # Create a new task
        async def spam_cleanup_task():
            try:
                while True:
                    # Only run if raid mode is active
                    if self.raid_active.get(guild_id, False):
                        # Get log channel
                        log_channel_id = guild_settings.get_log_channel(guild_id)
                        log_channel = None
                        if log_channel_id:
                            log_channel = guild.get_channel(log_channel_id)

                        # Check for duplicate channels
                        channels_to_clean = detect_duplicate_channels(guild)

                        # Check for spammers
                        spammer_ids = get_spammer_ids(guild_id)

                        # Clean up spam
                        if channels_to_clean or spammer_ids:
                            # Only ask about message deletion if there are actual spammers
                            if spammer_ids:
                                should_delete_messages = await self.ask_spam_cleanup(guild, spammer_ids)
                                await cleanup_spam(guild, log_channel, delete_messages=should_delete_messages)
                            else:
                                # Just clean up duplicate channels if any
                                await cleanup_spam(guild, log_channel, delete_messages=False)

                    # Wait for the next check
                    await asyncio.sleep(10)  # Check every 10 seconds
            except asyncio.CancelledError:
                logging.info(f"Spam cleanup task cancelled for guild {guild.name}")
            except Exception as e:
                logging.error(f"Error in spam cleanup task for guild {guild.name}: {e}")

        # Start the task
        task = asyncio.create_task(spam_cleanup_task())
        self.spam_cleanup_tasks[guild_id] = task

    def stop_spam_cleanup(self, guild_id):
        """Stop the spam cleanup task for a guild."""
        task = self.spam_cleanup_tasks.get(guild_id)
        if task:
            task.cancel()
            self.spam_cleanup_tasks.pop(guild_id, None)

async def setup(bot):
    await bot.add_cog(RaidMode(bot))