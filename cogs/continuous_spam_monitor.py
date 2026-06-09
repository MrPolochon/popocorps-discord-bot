import discord
from discord.ext import commands, tasks
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from collections import defaultdict, deque
from utils.spam_detector import track_message, get_spammer_ids, reset_tracking
from utils.guild_settings import guild_settings

class ContinuousSpamMonitor(commands.Cog):
    """24/7 spam detection and monitoring system"""
    
    def __init__(self, bot):
        self.bot = bot
        self.guild_settings = guild_settings
        
        # 24/7 monitoring data structures
        self.message_tracking = defaultdict(lambda: deque(maxlen=100))  # Recent messages per guild
        self.user_message_counts = defaultdict(lambda: defaultdict(int))  # Message counts per user per guild
        self.user_last_message = defaultdict(lambda: defaultdict(lambda: datetime.now(timezone.utc)))  # Last message time per user
        self.spam_warnings = defaultdict(set)  # Users who have been warned for potential spam
        
        # Monitoring configuration
        self.SPAM_THRESHOLD = 10  # Messages within time window
        self.TIME_WINDOW = 1  # Seconds - 10 messages in 1 second triggers spam
        self.DUPLICATE_THRESHOLD = 3  # Identical messages threshold
        self.RAPID_JOIN_THRESHOLD = 5  # New members joining quickly
        
        # Start the continuous monitoring task
        self.continuous_spam_check.start()
        self.reset_daily_counters.start()
        
    async def cog_unload(self):
        """Clean up when cog is unloaded"""
        self.continuous_spam_check.cancel()
        self.reset_daily_counters.cancel()

    @commands.Cog.listener()
    async def on_message(self, message):
        """Monitor all messages for spam patterns"""
        # Skip bots and DMs
        if message.author.bot or not message.guild:
            return
            
        guild_id = message.guild.id
        user_id = message.author.id
        current_time = datetime.now(timezone.utc)
        
        # Track message for 24/7 monitoring
        self.message_tracking[guild_id].append({
            'user_id': user_id,
            'content': message.content,
            'timestamp': current_time,
            'channel_id': message.channel.id,
            'message_id': message.id
        })
        
        # Update user message counts
        self.user_message_counts[guild_id][user_id] += 1
        self.user_last_message[guild_id][user_id] = current_time
        
        # Check for immediate spam patterns
        await self.check_immediate_spam(message)

    async def check_immediate_spam(self, message):
        """Check for immediate spam patterns in real-time"""
        guild_id = message.guild.id
        user_id = message.author.id
        current_time = datetime.now(timezone.utc)
        
        # Get recent messages from this user
        recent_messages = [
            msg for msg in self.message_tracking[guild_id]
            if msg['user_id'] == user_id and 
            (current_time - msg['timestamp']).total_seconds() <= self.TIME_WINDOW
        ]
        
        # Check for rapid messaging
        if len(recent_messages) >= self.SPAM_THRESHOLD:
            await self.handle_potential_spam(message, "rapid_messaging", len(recent_messages))
            
        # Check for duplicate messages
        content_counts = defaultdict(int)
        for msg in recent_messages:
            if msg['content'].strip():  # Only count non-empty messages
                content_counts[msg['content'].lower()] += 1
                
        for content, count in content_counts.items():
            if count >= self.DUPLICATE_THRESHOLD:
                await self.handle_potential_spam(message, "duplicate_content", count)
                break

    async def handle_potential_spam(self, message, spam_type, severity):
        """Handle detected spam with graduated response"""
        guild_id = message.guild.id
        user_id = message.author.id
        
        # Skip if already warned recently
        if user_id in self.spam_warnings[guild_id]:
            return
            
        # Add to warned users
        self.spam_warnings[guild_id].add(user_id)
        
        # Issue automatic warning for spam
        await self.issue_spam_warning(message, spam_type, severity)
        
        # Get audit logger for alerts
        audit_logger = self.bot.get_cog('AuditLogger')
        
        # Create spam detection report
        embed = discord.Embed(
            title="⚠️ 24/7 Spam Detection Alert",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="User", value=f"{message.author.mention} ({message.author.id})", inline=True)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        embed.add_field(name="Detection Type", value=spam_type.replace("_", " ").title(), inline=True)
        embed.add_field(name="Severity", value=f"{severity} occurrences", inline=True)
        embed.add_field(name="Time", value=f"<t:{int(datetime.now().timestamp())}:R>", inline=True)
        
        # Add recommended action based on severity
        if severity >= 8:
            embed.add_field(
                name="Recommended Action",
                value="🚨 **HIGH RISK** - Consider immediate timeout or ban",
                inline=False
            )
            # Send critical alert
            if audit_logger:
                alert_reason = f"HIGH-SEVERITY SPAM DETECTED: User {message.author.mention} triggered {spam_type} with {severity} occurrences. This indicates aggressive spam behavior requiring immediate moderation action."
                try:
                    await audit_logger.send_critical_alert(message.guild, message.channel, alert_reason)
                except Exception as e:
                    logging.error(f"Error sending critical spam alert: {e}")
        elif severity >= 5:
            embed.add_field(
                name="Recommended Action",
                value="⚠️ **MODERATE RISK** - Monitor closely, consider timeout",
                inline=False
            )
        else:
            embed.add_field(
                name="Recommended Action",
                value="ℹ️ **LOW RISK** - Continue monitoring",
                inline=False
            )
        
        # Send to log channel
        log_channel_id = self.guild_settings.get_log_channel(guild_id)
        if log_channel_id:
            log_channel = message.guild.get_channel(log_channel_id)
            if log_channel:
                try:
                    await log_channel.send(embed=embed)
                except Exception as e:
                    logging.error(f"Error sending spam detection alert: {e}")

    async def issue_spam_warning(self, message, spam_type, severity):
        """Issue automatic warning for detected spam"""
        try:
            # Get the warning system
            warning_system = self.bot.get_cog('WarningSystem')
            if not warning_system:
                logging.error("Warning system not available for spam warning")
                return
            
            # Create detailed spam reason
            spam_reasons = {
                "rapid_messaging": f"Spam détecté: {severity} messages en {self.TIME_WINDOW} seconde(s)",
                "duplicate_content": f"Spam détecté: {severity} messages identiques répétés"
            }
            
            reason = spam_reasons.get(spam_type, f"Spam détecté: {spam_type}")
            
            # Store the warning in database
            await warning_system.store_warning(
                guild_id=message.guild.id,
                user_id=message.author.id,
                moderator_id=self.bot.user.id,  # Bot as moderator
                reason=reason,
                bot_source="popocorp",
                message_id=message.id,
                channel_id=message.channel.id
            )
            
            # Send warning notification to user (if possible)
            try:
                warning_embed = discord.Embed(
                    title="⚠️ Avertissement Automatique",
                    description=f"Vous avez reçu un avertissement pour spam.",
                    color=discord.Color.orange()
                )
                warning_embed.add_field(name="Raison", value=reason, inline=False)
                warning_embed.add_field(name="Serveur", value=message.guild.name, inline=False)
                warning_embed.set_footer(text="Détection automatique de spam - PopoCorps Bot")
                
                await message.author.send(embed=warning_embed)
            except discord.Forbidden:
                # User has DMs disabled, continue without sending DM
                pass
                
            logging.info(f"Automatic spam warning issued to user {message.author.id} in guild {message.guild.id}")
            
        except Exception as e:
            logging.error(f"Error issuing spam warning: {e}")

    @tasks.loop(seconds=30)
    async def continuous_spam_check(self):
        """Continuous background spam analysis every 30 seconds"""
        try:
            for guild in self.bot.guilds:
                await self.analyze_guild_patterns(guild)
        except Exception as e:
            logging.error(f"Error in continuous spam check: {e}")

    async def analyze_guild_patterns(self, guild):
        """Analyze patterns for a specific guild"""
        guild_id = guild.id
        current_time = datetime.now(timezone.utc)
        
        # Skip if no recent activity
        if not self.message_tracking[guild_id]:
            return
            
        # Analyze recent message patterns
        recent_messages = [
            msg for msg in self.message_tracking[guild_id]
            if (current_time - msg['timestamp']).total_seconds() <= 300  # Last 5 minutes
        ]
        
        if not recent_messages:
            return
            
        # Detect coordinated spam (multiple users, similar content)
        await self.detect_coordinated_spam(guild, recent_messages)
        
        # Detect raid patterns (mass joining + immediate messaging)
        await self.detect_raid_patterns(guild, recent_messages)

    async def detect_coordinated_spam(self, guild, recent_messages):
        """Detect coordinated spam attacks"""
        # Group messages by similar content
        content_groups = defaultdict(list)
        for msg in recent_messages:
            if msg['content'].strip():
                # Simple similarity check (could be enhanced)
                normalized_content = msg['content'].lower().strip()
                content_groups[normalized_content].append(msg)
        
        # Check for coordinated spam (same content from multiple users)
        for content, messages in content_groups.items():
            unique_users = set(msg['user_id'] for msg in messages)
            if len(unique_users) >= 3 and len(messages) >= 6:  # 3+ users, 6+ messages
                await self.report_coordinated_spam(guild, content, unique_users, len(messages))

    async def report_coordinated_spam(self, guild, content, user_ids, message_count):
        """Report coordinated spam to staff"""
        embed = discord.Embed(
            title="🚨 COORDINATED SPAM ATTACK DETECTED",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="Attack Type", value="Coordinated Multi-User Spam", inline=False)
        embed.add_field(name="Users Involved", value=str(len(user_ids)), inline=True)
        embed.add_field(name="Messages Sent", value=str(message_count), inline=True)
        embed.add_field(name="Content Preview", value=f"```{content[:100]}...```", inline=False)
        
        user_mentions = []
        for user_id in list(user_ids)[:5]:  # Limit to first 5
            user = guild.get_member(user_id)
            if user:
                user_mentions.append(f"• {user.mention} ({user.id})")
        
        if len(user_ids) > 5:
            user_mentions.append(f"• ... and {len(user_ids) - 5} more")
            
        embed.add_field(name="Involved Users", value="\n".join(user_mentions), inline=False)
        embed.add_field(
            name="Immediate Actions Recommended",
            value="• Enable raid mode immediately\n• Ban or timeout all involved users\n• Review recent joins for additional accounts\n• Check for bot accounts",
            inline=False
        )
        
        # Send critical alert
        audit_logger = self.bot.get_cog('AuditLogger')
        if audit_logger:
            alert_reason = f"COORDINATED SPAM ATTACK: {len(user_ids)} users are sending identical spam messages. This is a serious attack requiring immediate action to prevent server disruption."
            log_channel_id = self.guild_settings.get_log_channel(guild.id)
            if log_channel_id:
                log_channel = guild.get_channel(log_channel_id)
                if log_channel:
                    try:
                        await log_channel.send(embed=embed)
                        await audit_logger.send_critical_alert(guild, log_channel, alert_reason)
                    except Exception as e:
                        logging.error(f"Error sending coordinated spam alert: {e}")

    async def detect_raid_patterns(self, guild, recent_messages):
        """Detect raid patterns (new members immediately sending messages)"""
        # Get members who joined recently (last 10 minutes)
        current_time = datetime.now(timezone.utc)
        recent_joins = [
            member for member in guild.members
            if member.joined_at and (current_time - member.joined_at).total_seconds() <= 600
        ]
        
        if len(recent_joins) < 3:  # Not enough new members for raid pattern
            return
            
        # Check if recent joiners are messaging immediately
        messaging_new_members = []
        for member in recent_joins:
            member_messages = [
                msg for msg in recent_messages
                if msg['user_id'] == member.id
            ]
            if member_messages:
                messaging_new_members.append(member)
        
        # If 3+ new members are messaging, it's likely a raid
        if len(messaging_new_members) >= 3:
            await self.report_raid_pattern(guild, messaging_new_members, len(recent_joins))

    async def report_raid_pattern(self, guild, messaging_members, total_new_joins):
        """Report detected raid pattern"""
        embed = discord.Embed(
            title="🚨 RAID PATTERN DETECTED",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="Pattern Type", value="Mass Join + Immediate Messaging", inline=False)
        embed.add_field(name="New Members (10 min)", value=str(total_new_joins), inline=True)
        embed.add_field(name="Messaging Immediately", value=str(len(messaging_members)), inline=True)
        
        member_list = []
        for member in messaging_members[:5]:
            join_time = int(member.joined_at.timestamp()) if member.joined_at else 0
            member_list.append(f"• {member.mention} (joined <t:{join_time}:R>)")
        
        if len(messaging_members) > 5:
            member_list.append(f"• ... and {len(messaging_members) - 5} more")
            
        embed.add_field(name="Suspicious Members", value="\n".join(member_list), inline=False)
        embed.add_field(
            name="Immediate Actions Recommended",
            value="• **ENABLE RAID MODE NOW**\n• Set verification level to highest\n• Temporarily disable invites\n• Review and ban suspicious accounts",
            inline=False
        )
        
        # Send critical alert
        audit_logger = self.bot.get_cog('AuditLogger')
        if audit_logger:
            alert_reason = f"RAID PATTERN DETECTED: {len(messaging_members)} new members joined and immediately started messaging. This indicates a coordinated raid attack. Enable raid mode immediately."
            log_channel_id = self.guild_settings.get_log_channel(guild.id)
            if log_channel_id:
                log_channel = guild.get_channel(log_channel_id)
                if log_channel:
                    try:
                        await log_channel.send(embed=embed)
                        await audit_logger.send_critical_alert(guild, log_channel, alert_reason)
                    except Exception as e:
                        logging.error(f"Error sending raid pattern alert: {e}")

    @tasks.loop(hours=24)
    async def reset_daily_counters(self):
        """Reset daily counters and clean up old data"""
        current_time = datetime.now(timezone.utc)
        
        # Clear old message tracking data (older than 1 hour)
        for guild_id in list(self.message_tracking.keys()):
            self.message_tracking[guild_id] = deque([
                msg for msg in self.message_tracking[guild_id]
                if (current_time - msg['timestamp']).total_seconds() <= 3600
            ], maxlen=100)
        
        # Reset spam warnings (daily reset)
        self.spam_warnings.clear()
        
        # Clean up empty entries
        empty_guilds = [
            guild_id for guild_id, messages in self.message_tracking.items()
            if not messages
        ]
        for guild_id in empty_guilds:
            del self.message_tracking[guild_id]
            if guild_id in self.user_message_counts:
                del self.user_message_counts[guild_id]
            if guild_id in self.user_last_message:
                del self.user_last_message[guild_id]

    @continuous_spam_check.before_loop
    async def before_continuous_spam_check(self):
        """Wait until bot is ready before starting the task"""
        await self.bot.wait_until_ready()

    @reset_daily_counters.before_loop
    async def before_reset_daily_counters(self):
        """Wait until bot is ready before starting the task"""
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(ContinuousSpamMonitor(bot))