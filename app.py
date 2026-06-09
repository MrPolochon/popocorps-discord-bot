import os
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import sessionmaker
from sqlalchemy import desc, func
from datetime import datetime, timedelta
import discord
from discord.ext import commands
import asyncio
import threading
import json
from models import Warning, get_db_session, engine, DATABASE_URL
from utils.guild_settings import GuildSettings

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "dashboard-secret-key-2024"
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize SQLAlchemy with Flask
db = SQLAlchemy(app)

# Initialize guild settings
guild_settings = GuildSettings()

# Global bot reference (will be set by the Discord bot)
discord_bot = None

# User info cache to avoid repeated API calls
user_cache = {}
cache_timestamp = {}

def set_discord_bot(bot):
    """Set the Discord bot reference for the dashboard"""
    global discord_bot
    discord_bot = bot

def get_bot_stats():
    """Get basic bot statistics"""
    if not discord_bot:
        return {
            'status': 'offline',
            'guilds': 0,
            'users': 0,
            'uptime': '0 minutes'
        }
    
    return {
        'status': 'online' if discord_bot.is_ready() else 'connecting',
        'guilds': len(discord_bot.guilds),
        'users': sum(guild.member_count for guild in discord_bot.guilds),
        'latency': round(discord_bot.latency * 1000, 2)
    }

def get_guild_info(guild_id):
    """Get information about a specific guild"""
    if not discord_bot:
        return None
    
    guild = discord_bot.get_guild(guild_id)
    if not guild:
        return None
    
    return {
        'id': guild.id,
        'name': guild.name,
        'icon': str(guild.icon.url) if guild.icon else None,
        'member_count': guild.member_count,
        'owner': str(guild.owner) if guild.owner else 'Unknown',
        'created_at': guild.created_at.strftime('%Y-%m-%d')
    }

def get_user_info(user_id, guild_id=None):
    """Get user information from Discord with caching"""
    cache_key = f"{user_id}_{guild_id or 'global'}"
    current_time = datetime.utcnow()
    
    # Check cache first (valid for 5 minutes)
    if cache_key in user_cache and cache_key in cache_timestamp:
        if (current_time - cache_timestamp[cache_key]).seconds < 300:
            return user_cache[cache_key]
    
    if not discord_bot:
        fallback_data = {
            'id': user_id,
            'username': f'Utilisateur #{user_id}',
            'display_name': f'Utilisateur #{user_id}',
            'avatar_url': None
        }
        user_cache[cache_key] = fallback_data
        cache_timestamp[cache_key] = current_time
        return fallback_data
    
    try:
        # Try to get user from bot's internal cache first
        user = discord_bot.get_user(user_id)
        
        # Try to get member from guild for display name
        member = None
        if guild_id:
            guild = discord_bot.get_guild(guild_id)
            if guild:
                member = guild.get_member(user_id)
        
        if user or member:
            # Use member info if available, otherwise user info
            source = member or user
            display_name = source.display_name if hasattr(source, 'display_name') else source.name
            username = user.name if user else f'user_{user_id}'
            avatar_url = str(source.avatar.url) if source.avatar else None
            
            user_data = {
                'id': user_id,
                'username': username,
                'display_name': display_name,
                'avatar_url': avatar_url
            }
            
            # Cache the result
            user_cache[cache_key] = user_data
            cache_timestamp[cache_key] = current_time
            return user_data
            
    except Exception as e:
        print(f"Error fetching user {user_id}: {e}")
    
    # Fallback if user not found
    fallback_data = {
        'id': user_id,
        'username': f'Utilisateur #{user_id}',
        'display_name': f'Utilisateur #{user_id}',
        'avatar_url': None
    }
    
    # Cache the fallback too to avoid repeated lookups
    user_cache[cache_key] = fallback_data
    cache_timestamp[cache_key] = current_time
    return fallback_data

@app.route('/')
def dashboard():
    """Main dashboard page"""
    bot_stats = get_bot_stats()
    
    # Get recent warnings (last 24 hours)
    db_session = get_db_session()
    try:
        recent_warnings_raw = db_session.query(Warning).filter(
            Warning.timestamp >= datetime.utcnow() - timedelta(days=1)
        ).order_by(desc(Warning.timestamp)).limit(10).all()
        
        # Enrich warnings with user information
        recent_warnings = []
        for warning in recent_warnings_raw:
            user_info = get_user_info(warning.user_id, warning.guild_id)
            guild_info = get_guild_info(warning.guild_id)
            
            warning_data = {
                'id': warning.id,
                'guild_id': warning.guild_id,
                'guild_name': guild_info['name'] if guild_info else f'Serveur #{warning.guild_id}',
                'user_id': warning.user_id,
                'username': user_info['username'],
                'display_name': user_info['display_name'],
                'avatar_url': user_info['avatar_url'],
                'moderator_id': warning.moderator_id,
                'reason': warning.reason,
                'bot_source': warning.bot_source,
                'timestamp': warning.timestamp,
                'message_id': warning.message_id,
                'channel_id': warning.channel_id
            }
            recent_warnings.append(warning_data)
        
        # Get warning statistics
        total_warnings = db_session.query(Warning).count()
        warnings_today = db_session.query(Warning).filter(
            Warning.timestamp >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()
        
        # Get warnings by bot source
        bot_stats_query = db_session.query(
            Warning.bot_source,
            func.count(Warning.id).label('count')
        ).group_by(Warning.bot_source).all()
        
        bot_warning_stats = {stat[0]: stat[1] for stat in bot_stats_query}
        
    except Exception as e:
        print(f"Database error: {e}")
        recent_warnings = []
        total_warnings = 0
        warnings_today = 0
        bot_warning_stats = {}
    finally:
        db_session.close()
    
    # Get guild information
    guilds_info = []
    if discord_bot:
        for guild in discord_bot.guilds:
            guilds_info.append(get_guild_info(guild.id))
    
    return render_template('dashboard.html',
                         bot_stats=bot_stats,
                         recent_warnings=recent_warnings,
                         total_warnings=total_warnings,
                         warnings_today=warnings_today,
                         bot_warning_stats=bot_warning_stats,
                         guilds=guilds_info)

@app.route('/warnings')
def warnings_page():
    """Warnings management page"""
    page = request.args.get('page', 1, type=int)
    guild_id = request.args.get('guild_id', type=int)
    bot_source = request.args.get('bot_source', '')
    
    db_session = get_db_session()
    try:
        query = db_session.query(Warning)
        
        # Filter by guild if specified
        if guild_id:
            query = query.filter(Warning.guild_id == guild_id)
        
        # Filter by bot source if specified
        if bot_source:
            query = query.filter(Warning.bot_source == bot_source)
        
        # Paginate results
        per_page = 25
        offset = (page - 1) * per_page
        warnings_raw = query.order_by(desc(Warning.timestamp)).offset(offset).limit(per_page).all()
        
        # Enrich warnings with user information
        warnings = []
        for warning in warnings_raw:
            user_info = get_user_info(warning.user_id, warning.guild_id)
            guild_info = get_guild_info(warning.guild_id)
            
            # Get moderator info if available
            moderator_info = None
            if warning.moderator_id is not None:
                moderator_info = get_user_info(warning.moderator_id, warning.guild_id)
            
            warning_data = {
                'id': warning.id,
                'guild_id': warning.guild_id,
                'guild_name': guild_info['name'] if guild_info else f'Serveur #{warning.guild_id}',
                'user_id': warning.user_id,
                'username': user_info['username'],
                'display_name': user_info['display_name'],
                'avatar_url': user_info['avatar_url'],
                'moderator_id': warning.moderator_id,
                'moderator_username': moderator_info['username'] if moderator_info else None,
                'moderator_display_name': moderator_info['display_name'] if moderator_info else None,
                'reason': warning.reason,
                'bot_source': warning.bot_source,
                'timestamp': warning.timestamp,
                'message_id': warning.message_id,
                'channel_id': warning.channel_id
            }
            warnings.append(warning_data)
        
        # Get total count for pagination
        total_warnings = query.count()
        total_pages = (total_warnings + per_page - 1) // per_page
        
        # Get unique bot sources for filter
        bot_sources = db_session.query(Warning.bot_source).distinct().all()
        bot_sources = [source[0] for source in bot_sources if source[0]]
        
    except Exception as e:
        print(f"Database error: {e}")
        warnings = []
        total_warnings = 0
        total_pages = 0
        bot_sources = []
    finally:
        db_session.close()
    
    # Get guild information for warnings
    guilds_info = {}
    if discord_bot:
        for guild in discord_bot.guilds:
            guilds_info[guild.id] = guild.name
    
    return render_template('warnings.html',
                         warnings=warnings,
                         page=page,
                         total_pages=total_pages,
                         total_warnings=total_warnings,
                         bot_sources=bot_sources,
                         guilds_info=guilds_info,
                         current_guild_id=guild_id,
                         current_bot_source=bot_source)

@app.route('/api/stats')
def api_stats():
    """API endpoint for real-time statistics"""
    bot_stats = get_bot_stats()
    
    db_session = get_db_session()
    try:
        # Get warnings in the last hour
        warnings_last_hour = db_session.query(Warning).filter(
            Warning.timestamp >= datetime.utcnow() - timedelta(hours=1)
        ).count()
        
        # Get active raids (if any)
        # This would need to be implemented in the raid system
        active_raids = 0  # Placeholder
        
    except Exception as e:
        warnings_last_hour = 0
        active_raids = 0
    finally:
        db_session.close()
    
    return jsonify({
        'bot_stats': bot_stats,
        'warnings_last_hour': warnings_last_hour,
        'active_raids': active_raids,
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/api/warnings/<int:user_id>')
def api_user_warnings(user_id):
    """API endpoint to get warnings for a specific user"""
    guild_id = request.args.get('guild_id', type=int)
    
    db_session = get_db_session()
    try:
        query = db_session.query(Warning).filter(Warning.user_id == user_id)
        
        if guild_id:
            query = query.filter(Warning.guild_id == guild_id)
        
        warnings = query.order_by(desc(Warning.timestamp)).all()
        
        warnings_data = []
        for warning in warnings:
            warnings_data.append({
                'id': warning.id,
                'reason': warning.reason,
                'bot_source': warning.bot_source,
                'timestamp': warning.timestamp.isoformat(),
                'moderator_id': warning.moderator_id,
                'guild_id': warning.guild_id
            })
        
        return jsonify({
            'user_id': user_id,
            'warnings': warnings_data,
            'total': len(warnings_data)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db_session.close()

@app.route('/guilds')
def guilds_page():
    """Guild management page"""
    guilds_data = []
    
    if discord_bot:
        for guild in discord_bot.guilds:
            guild_info = get_guild_info(guild.id)
            
            # Get guild settings
            log_channel_id = guild_settings.get_log_channel(guild.id)
            announcement_channel_id = guild_settings.get_announcement_channel(guild.id)
            admin_role_id = guild_settings.get_admin_role(guild.id)
            
            # Get welcome/goodbye settings
            welcome_enabled = guild_settings.is_welcome_enabled(guild.id)
            goodbye_enabled = guild_settings.is_goodbye_enabled(guild.id)
            welcome_channel_id = guild_settings.get_welcome_channel(guild.id)
            goodbye_channel_id = guild_settings.get_goodbye_channel(guild.id)
            
            # Get warning count for this guild
            db_session = get_db_session()
            try:
                warning_count = db_session.query(Warning).filter(
                    Warning.guild_id == guild.id
                ).count()
            except:
                warning_count = 0
            finally:
                db_session.close()
            
            guild_info.update({
                'log_channel_id': log_channel_id,
                'announcement_channel_id': announcement_channel_id,
                'admin_role_id': admin_role_id,
                'warning_count': warning_count,
                'welcome_enabled': welcome_enabled,
                'goodbye_enabled': goodbye_enabled,
                'welcome_channel_id': welcome_channel_id,
                'goodbye_channel_id': goodbye_channel_id,
                'setup_complete': bool(log_channel_id or announcement_channel_id)
            })
            
            guilds_data.append(guild_info)
    
    return render_template('guilds.html', guilds=guilds_data)

@app.route('/guild/<int:guild_id>/welcome')
def welcome_config_page(guild_id):
    """Welcome/goodbye configuration page for a specific guild"""
    if not discord_bot:
        flash("Bot is not connected", "error")
        return redirect(url_for('guilds_page'))
    
    guild = discord_bot.get_guild(guild_id)
    if not guild:
        flash("Guild not found", "error")
        return redirect(url_for('guilds_page'))
    
    # Get current settings
    welcome_settings = {
        'enabled': guild_settings.is_welcome_enabled(guild_id),
        'channel_id': guild_settings.get_welcome_channel(guild_id),
        'message': guild_settings.get_welcome_message(guild_id),
        'background': guild_settings.get_welcome_background(guild_id),
        'font': guild_settings.get_welcome_font(guild_id)
    }
    
    goodbye_settings = {
        'enabled': guild_settings.is_goodbye_enabled(guild_id),
        'channel_id': guild_settings.get_goodbye_channel(guild_id),
        'message': guild_settings.get_goodbye_message(guild_id),
        'background': guild_settings.get_goodbye_background(guild_id),
        'font': guild_settings.get_goodbye_font(guild_id)
    }
    
    # Get guild channels for dropdown
    text_channels = [channel for channel in guild.channels if channel.type == discord.ChannelType.text]
    
    # Available fonts
    available_fonts = ["Arial", "Times", "Courier", "Helvetica", "Comic Sans", "Impact", "Trebuchet"]
    
    return render_template('welcome_config.html', 
                         guild=guild, 
                         welcome_settings=welcome_settings,
                         goodbye_settings=goodbye_settings,
                         text_channels=text_channels,
                         available_fonts=available_fonts)

@app.route('/guild/<int:guild_id>/welcome/save', methods=['POST'])
def save_welcome_config(guild_id):
    """Save welcome/goodbye configuration"""
    try:
        # Welcome settings
        welcome_enabled = request.form.get('welcome_enabled') == 'on'
        welcome_channel_id = request.form.get('welcome_channel_id')
        welcome_message = request.form.get('welcome_message', '').strip()
        welcome_background = request.form.get('welcome_background', '').strip()
        welcome_font = request.form.get('welcome_font', 'Arial')
        
        # Goodbye settings
        goodbye_enabled = request.form.get('goodbye_enabled') == 'on'
        goodbye_channel_id = request.form.get('goodbye_channel_id')
        goodbye_message = request.form.get('goodbye_message', '').strip()
        goodbye_background = request.form.get('goodbye_background', '').strip()
        goodbye_font = request.form.get('goodbye_font', 'Arial')
        
        # Save welcome settings
        guild_settings.set_welcome_enabled(guild_id, welcome_enabled)
        if welcome_channel_id:
            guild_settings.set_welcome_channel(guild_id, int(welcome_channel_id))
        if welcome_message:
            guild_settings.set_welcome_message(guild_id, welcome_message)
        if welcome_background:
            guild_settings.set_welcome_background(guild_id, welcome_background)
        guild_settings.set_welcome_font(guild_id, welcome_font)
        
        # Save goodbye settings
        guild_settings.set_goodbye_enabled(guild_id, goodbye_enabled)
        if goodbye_channel_id:
            guild_settings.set_goodbye_channel(guild_id, int(goodbye_channel_id))
        if goodbye_message:
            guild_settings.set_goodbye_message(guild_id, goodbye_message)
        if goodbye_background:
            guild_settings.set_goodbye_background(guild_id, goodbye_background)
        guild_settings.set_goodbye_font(guild_id, goodbye_font)
        
        flash("Welcome/goodbye settings saved successfully!", "success")
        
    except Exception as e:
        flash(f"Error saving settings: {str(e)}", "error")
    
    return redirect(url_for('welcome_config_page', guild_id=guild_id))

@app.route('/system-control')
def system_control_page():
    """System control dashboard page"""
    return render_template('system_control.html')

@app.route('/api/system-states')
def api_system_states():
    """API endpoint to get current system states"""
    if not discord_bot:
        return jsonify({"error": "Bot not available"}), 500
    
    try:
        # Get guild settings instance from bot
        guild_settings = getattr(discord_bot, 'guild_settings', None)
        if not guild_settings:
            from utils.guild_settings import GuildSettings
            guild_settings = GuildSettings()
        
        # For now, return states for the first guild the bot is in
        guild_id = None
        if discord_bot.guilds:
            guild_id = discord_bot.guilds[0].id
        
        if not guild_id:
            return jsonify({
                "ai_chat_enabled": False,
                "continuous_spam_enabled": False,
                "audit_logs_enabled": False,
                "welcome_enabled": False,
                "goodbye_enabled": False,
                "raid_mode_enabled": False
            })
        
        states = {
            "ai_chat_enabled": guild_settings.get_setting(guild_id, 'ai_chat_enabled', False),
            "continuous_spam_enabled": guild_settings.get_setting(guild_id, 'continuous_spam_enabled', True),
            "audit_logs_enabled": guild_settings.get_setting(guild_id, 'audit_logs_enabled', True),
            "welcome_enabled": guild_settings.is_welcome_enabled(guild_id),
            "goodbye_enabled": guild_settings.is_goodbye_enabled(guild_id),
            "raid_mode_enabled": guild_settings.get_setting(guild_id, 'raid_mode_enabled', True)
        }
        
        return jsonify(states)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/toggle-system', methods=['POST'])
def api_toggle_system():
    """API endpoint to toggle system states"""
    if not discord_bot:
        return jsonify({"error": "Bot not available"}), 500
    
    try:
        data = request.get_json()
        system = data.get('system')
        enabled = data.get('enabled')
        
        if not system or enabled is None:
            return jsonify({"error": "Missing system or enabled parameter"}), 400
        
        # Get guild settings instance from bot
        guild_settings = getattr(discord_bot, 'guild_settings', None)
        if not guild_settings:
            from utils.guild_settings import GuildSettings
            guild_settings = GuildSettings()
        
        # For now, use the first guild the bot is in
        guild_id = None
        if discord_bot.guilds:
            guild_id = discord_bot.guilds[0].id
        
        if not guild_id:
            return jsonify({"error": "Bot not in any guilds"}), 400
        
        # Map system names to appropriate settings methods
        if system == 'ai_chat_enabled':
            guild_settings.set_setting(guild_id, 'ai_chat_enabled', enabled)
        elif system == 'continuous_spam_enabled':
            guild_settings.set_setting(guild_id, 'continuous_spam_enabled', enabled)
        elif system == 'audit_logs_enabled':
            guild_settings.set_setting(guild_id, 'audit_logs_enabled', enabled)
        elif system == 'welcome_enabled':
            guild_settings.set_welcome_enabled(guild_id, enabled)
        elif system == 'goodbye_enabled':
            guild_settings.set_goodbye_enabled(guild_id, enabled)
        elif system == 'raid_mode_enabled':
            guild_settings.set_setting(guild_id, 'raid_mode_enabled', enabled)
        else:
            return jsonify({"error": "Unknown system"}), 400
        
        return jsonify({"success": True, "message": f"System {system} {'enabled' if enabled else 'disabled'}"})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)