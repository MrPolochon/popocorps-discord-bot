import discord
import logging
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import re

# Track user message frequency and repetition
user_messages = defaultdict(list)  # {guild_id: {user_id: [message timestamps]}}
message_content_counter = defaultdict(lambda: defaultdict(Counter))  # {guild_id: {user_id: Counter(messages)}}
detected_spammers = defaultdict(set)  # {guild_id: {user_id1, user_id2, ...}}
duplicated_channels = defaultdict(list)  # {guild_id: [channel_id1, channel_id2, ...]}

# Constants for spam detection
MESSAGE_THRESHOLD = 8  # Number of messages in the time window to consider potential spam
TIME_WINDOW = 7  # Time window in seconds
REPETITION_THRESHOLD = 3  # Number of identical messages to consider spam
DUPLICATE_CHANNEL_SIMILARITY = 0.8  # Similarity threshold for duplicate channel detection

def reset_tracking(guild_id):
    """Reset all spam tracking data for a guild."""
    if guild_id in user_messages:
        del user_messages[guild_id]
    if guild_id in message_content_counter:
        del message_content_counter[guild_id]
    if guild_id in detected_spammers:
        detected_spammers[guild_id].clear()
    if guild_id in duplicated_channels:
        duplicated_channels[guild_id].clear()

def initialize_guild(guild_id):
    """Initialize tracking for a new guild."""
    if guild_id not in user_messages:
        user_messages[guild_id] = defaultdict(list)
    if guild_id not in message_content_counter:
        message_content_counter[guild_id] = defaultdict(Counter)
    if guild_id not in detected_spammers:
        detected_spammers[guild_id] = set()
    if guild_id not in duplicated_channels:
        duplicated_channels[guild_id] = []

def track_message(message):
    """Track a message for spam detection."""
    guild_id = message.guild.id
    user_id = message.author.id
    content = message.content
    
    # Skip bot messages
    if message.author.bot:
        return
        
    # Initialize tracking for this guild if it doesn't exist
    initialize_guild(guild_id)
    
    # Add message timestamp
    current_time = datetime.now()
    user_messages[guild_id][user_id].append(current_time)
    
    # Count message content
    if content:
        message_content_counter[guild_id][user_id][content] += 1
        
    # Check for spam conditions
    is_spammer = check_spam_conditions(guild_id, user_id)
    
    # If this is a new spammer, add to the set
    if is_spammer and user_id not in detected_spammers[guild_id]:
        detected_spammers[guild_id].add(user_id)
        guild_name = getattr(message.guild, 'name', f'Guild {guild_id}')
        author_name = getattr(message.author, 'name', f'User {user_id}')
        logging.warning(f"Detected potential spammer in {guild_name}: {author_name} (ID: {user_id})")

def check_spam_conditions(guild_id, user_id):
    """Check if a user meets spam conditions."""
    # Check message frequency
    message_times = user_messages[guild_id][user_id]
    
    # Clean up old messages outside the time window
    current_time = datetime.now()
    cutoff_time = current_time - timedelta(seconds=TIME_WINDOW)
    recent_messages = [t for t in message_times if t >= cutoff_time]
    user_messages[guild_id][user_id] = recent_messages
    
    # Check if message frequency exceeds threshold
    if len(recent_messages) >= MESSAGE_THRESHOLD:
        return True
    
    # Check message repetition
    if user_id in message_content_counter[guild_id]:
        for content, count in message_content_counter[guild_id][user_id].items():
            if count >= REPETITION_THRESHOLD:
                return True
                
    return False

def detect_duplicate_channels(guild):
    """Detect potentially duplicated channels created by spammers."""
    guild_id = guild.id
    
    # Get all text channels
    text_channels = [ch for ch in guild.text_channels if isinstance(ch, discord.TextChannel)]
    
    # Group channels by name similarity
    channel_names = [ch.name.lower() for ch in text_channels]
    duplicates = []
    
    # Simple approach: look for channels with very similar names
    for i, channel in enumerate(text_channels):
        name = channel.name.lower()
        # Remove common special characters
        clean_name = re.sub(r'[_\-・\s]', '', name)
        
        for j, other_channel in enumerate(text_channels):
            if i == j:
                continue
                
            other_name = other_channel.name.lower()
            clean_other_name = re.sub(r'[_\-・\s]', '', other_name)
            
            # Check for similarity
            if clean_name and clean_other_name:
                # If one is contained in the other
                if clean_name in clean_other_name or clean_other_name in clean_name:
                    # Check creation date - newer channels are more likely spam
                    if channel.created_at > guild.created_at + timedelta(days=30):
                        duplicates.append(channel.id)
                        
                # Check for repeated characters (common in spam channels)
                if any(c * 3 in clean_name for c in 'abcdefghijklmnopqrstuvwxyz'):
                    duplicates.append(channel.id)
    
    # Update duplicated channels list
    duplicated_channels[guild_id] = list(set(duplicates))
    
    return duplicated_channels[guild_id]

async def get_spammer_messages(guild, max_messages=100):
    """Retrieve recent messages from detected spammers."""
    guild_id = guild.id
    spammer_ids = detected_spammers.get(guild_id, set())
    
    if not spammer_ids:
        return {}
    
    # Collect messages by spammers from all text channels
    spammer_messages = defaultdict(list)
    
    for channel in guild.text_channels:
        try:
            async for message in channel.history(limit=max_messages):
                if message.author.id in spammer_ids:
                    spammer_messages[message.author.id].append(message)
        except discord.Forbidden:
            logging.warning(f"No permission to read message history in {channel.name}")
        except Exception as e:
            logging.error(f"Error retrieving messages from {channel.name}: {e}")
    
    return spammer_messages

async def cleanup_spam(guild, log_channel=None, delete_messages=True):
    """Clean up spam messages and report spammers to the log channel."""
    guild_id = guild.id
    spammer_ids = detected_spammers.get(guild_id, set())
    channels_to_clean = duplicated_channels.get(guild_id, [])
    
    # If no spammers detected, detect duplicate channels
    if not spammer_ids and not channels_to_clean:
        detect_duplicate_channels(guild)
        channels_to_clean = duplicated_channels.get(guild_id, [])
    
    # 1. Delete duplicated channels if any
    deleted_channels = []
    for channel_id in channels_to_clean:
        try:
            channel = guild.get_channel(channel_id)
            if channel:
                await channel.delete(reason="Raid protection: Detected duplicate spam channel")
                deleted_channels.append(channel.name)
                logging.info(f"Deleted duplicate channel {channel.name} in {guild.name}")
        except discord.Forbidden:
            logging.warning(f"No permission to delete channel {channel_id} in {guild.name}")
        except Exception as e:
            logging.error(f"Error deleting channel {channel_id}: {e}")
    
    # 2. Delete messages from spammers if requested
    deleted_message_count = defaultdict(int)
    if spammer_ids and delete_messages:
        spammer_messages = await get_spammer_messages(guild)
        
        for user_id, messages in spammer_messages.items():
            for message in messages:
                try:
                    await message.delete()
                    deleted_message_count[user_id] += 1
                except discord.Forbidden:
                    pass
                except discord.NotFound:
                    # Message already deleted
                    pass
                except Exception as e:
                    logging.error(f"Error deleting message: {e}")
    
    # 3. Send critical alert via audit logger if spammers detected
    if spammer_ids:
        try:
            # Try to get the bot instance and audit logger
            import sys
            if hasattr(sys.modules.get('__main__'), 'bot'):
                bot = sys.modules['__main__'].bot
                audit_logger = bot.get_cog('AuditLogger')
                if audit_logger:
                    total_messages = sum(len(msgs) for msgs in (await get_spammer_messages(guild)).values())
                    await audit_logger.log_spam_detection(guild, spammer_ids, total_messages)
        except Exception as e:
            logging.error(f"Error sending spam alert via audit logger: {e}")

    # 4. Send report to log channel
    if log_channel:
        try:
            # Create report embed
            embed = discord.Embed(
                title="🚨 Raid Protection - Cleanup Report",
                description="Summary of spam cleanup actions",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            
            # Add spammer information
            if spammer_ids:
                spammers_info = ""
                for user_id in spammer_ids:
                    user = guild.get_member(user_id)
                    user_name = user.name if user else f"Unknown User ({user_id})"
                    msg_count = deleted_message_count.get(user_id, 0)
                    
                    if delete_messages:
                        spammers_info += f"• **{user_name}** (ID: {user_id}) - {msg_count} messages deleted\n"
                    else:
                        spammers_info += f"• **{user_name}** (ID: {user_id}) - messages preserved\n"
                
                embed.add_field(
                    name=f"Detected Spammers ({len(spammer_ids)})",
                    value=spammers_info or "None detected",
                    inline=False
                )
                
                # Add message deletion status
                if not delete_messages and spammer_ids:
                    embed.add_field(
                        name="Message Deletion",
                        value="⚠️ Message deletion was skipped based on moderator decision.",
                        inline=False
                    )
            
            # Add deleted channels information
            if deleted_channels:
                embed.add_field(
                    name=f"Deleted Duplicate Channels ({len(deleted_channels)})",
                    value="\n".join(f"• {name}" for name in deleted_channels) or "None deleted",
                    inline=False
                )
                
            if not spammer_ids and not deleted_channels:
                embed.add_field(
                    name="No Action Taken",
                    value="No spammers or duplicate channels were detected.",
                    inline=False
                )
                
            # Add footer
            embed.set_footer(text=f"Raid mode is active | Server: {guild.name}")
            
            # Send report
            await log_channel.send(embed=embed)
            
        except Exception as e:
            logging.error(f"Error sending cleanup report: {e}")
    
    # Return cleanup statistics
    return {
        "spammers": len(spammer_ids),
        "deleted_channels": len(deleted_channels),
        "deleted_messages": sum(deleted_message_count.values())
    }

def get_spammer_ids(guild_id):
    """Get the set of detected spammer IDs for a guild."""
    return detected_spammers.get(guild_id, set())