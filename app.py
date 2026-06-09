import os
import hmac
import logging
import secrets as secrets_module
from urllib.parse import urlencode
import requests
from flask import Flask, render_template, render_template_string, request, jsonify, session, redirect, url_for, flash
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
from utils.guild_settings import guild_settings

app = Flask(__name__)
app.secret_key = (
    os.environ.get("SESSION_SECRET")
    or os.environ.get("FLASK_SECRET_KEY")
    or secrets_module.token_hex(32)
)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize SQLAlchemy with Flask
db = SQLAlchemy(app)

# Global bot reference (will be set by the Discord bot)
discord_bot = None

# User info cache to avoid repeated API calls
user_cache = {}
cache_timestamp = {}

# ---------------------------------------------------------------------------
# Authentification du dashboard
# Exige : mot de passe correct + connexion Discord (OAuth2) + etre membre du
# serveur avec le role admin configure (ou permission Administrateur/Gerer le serveur).
# ---------------------------------------------------------------------------
DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD")
DISCORD_CLIENT_ID = os.environ.get("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.environ.get("DISCORD_CLIENT_SECRET")
DISCORD_API_BASE = "https://discord.com/api"
logger = logging.getLogger(__name__)

# Endpoints accessibles sans authentification
PUBLIC_ENDPOINTS = {"login", "auth_discord", "oauth_callback", "oauth_setup", "logout", "static"}


def _dashboard_ready():
    """Le dashboard n'est utilisable que si l'auth est entierement configuree."""
    return bool(
        DASHBOARD_PASSWORD
        and DISCORD_CLIENT_ID
        and DISCORD_CLIENT_SECRET
        and os.environ.get("DASHBOARD_BASE_URL", "").strip()
    )


def _oauth_redirect_uri():
    """Construit l'URL de redirection OAuth (doit correspondre EXACTEMENT au portail Discord)."""
    base = os.environ.get("DASHBOARD_BASE_URL", "").strip().rstrip("/")
    if not base:
        host = request.headers.get("X-Forwarded-Host", request.host)
        base = f"https://{host}".rstrip("/")
    elif not base.startswith(("http://", "https://")):
        base = f"https://{base}"
    return f"{base}/callback"


def _check_dashboard_access(user_id: int) -> str:
    """Verifie l'acces au dashboard via le bot.

    L'acces exige STRICTEMENT le role admin configure dans le setup (aucun
    contournement par les permissions Discord).

    Retourne:
    - 'ok'                 : l'utilisateur possede le role admin configure
    - 'no_role_configured' : l'utilisateur est membre mais aucun role admin n'est configure
    - 'denied'             : non membre, ou membre sans le role admin configure
    """
    if not discord_bot:
        return "denied"
    member_of_any = False
    needs_config = False
    for guild in discord_bot.guilds:
        member = guild.get_member(user_id)
        if not member:
            continue
        member_of_any = True
        admin_role_id = guild_settings.get_admin_role(guild.id)
        if not admin_role_id:
            needs_config = True
            continue
        if any(r.id == admin_role_id for r in member.roles):
            return "ok"
    if needs_config:
        return "no_role_configured"
    return "denied"


@app.before_request
def _require_authentication():
    if request.endpoint in PUBLIC_ENDPOINTS:
        return None
    if not _dashboard_ready():
        return (
            "Dashboard desactive : configure DASHBOARD_PASSWORD, DISCORD_CLIENT_ID, "
            "DISCORD_CLIENT_SECRET et DASHBOARD_BASE_URL (URL publique Railway, sans slash final).",
            503,
        )
    if session.get("authenticated"):
        return None
    if request.path.startswith("/api/"):
        return jsonify({"error": "authentication required"}), 401
    return redirect(url_for("login", next=request.path))


LOGIN_HTML = """
<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PopoCorps · Connexion</title>
<style>
  body{font-family:system-ui,Segoe UI,Roboto,sans-serif;background:#0b0e14;color:#e6e6e6;
       display:flex;min-height:100vh;align-items:center;justify-content:center;margin:0}
  .card{background:#151a23;padding:32px;border-radius:14px;width:320px;box-shadow:0 10px 40px rgba(0,0,0,.4)}
  h1{font-size:20px;margin:0 0 4px}p{color:#9aa4b2;font-size:13px;margin:0 0 20px}
  input{width:100%;box-sizing:border-box;padding:11px;border-radius:8px;border:1px solid #2a3340;
        background:#0b0e14;color:#fff;margin-bottom:14px}
  button{width:100%;padding:11px;border:0;border-radius:8px;background:#5865F2;color:#fff;
         font-weight:600;cursor:pointer}
  .err{background:#3a1b1b;color:#ff9b9b;padding:9px;border-radius:8px;font-size:13px;margin-bottom:14px}
</style></head>
<body><form class="card" method="post">
  <h1>🛡️ PopoCorps</h1>
  <p>Connexion au tableau de bord</p>
  {% if error %}<div class="err">{{ error }}</div>{% endif %}
  <input type="password" name="password" placeholder="Mot de passe" autofocus required>
  <button type="submit">Continuer avec Discord</button>
</form></body></html>
"""


@app.route("/login", methods=["GET", "POST"])
def login():
    if not _dashboard_ready():
        return (
            "Dashboard desactive : configure DASHBOARD_PASSWORD, DISCORD_CLIENT_ID, "
            "DISCORD_CLIENT_SECRET et DASHBOARD_BASE_URL.",
            503,
        )
    if session.get("authenticated"):
        return redirect(url_for("dashboard"))
    error = None
    if request.method == "POST":
        password = request.form.get("password", "")
        if hmac.compare_digest(password.encode("utf-8"), DASHBOARD_PASSWORD.encode("utf-8")):
            # Mot de passe OK -> on lance la verification d'identite Discord
            session["pw_ok"] = True
            next_path = request.args.get("next", "")
            if next_path.startswith("/"):
                session["post_login_next"] = next_path
            return redirect(url_for("auth_discord"))
        error = "Mot de passe incorrect."
        return render_template_string(LOGIN_HTML, error=error), 401
    return render_template_string(LOGIN_HTML, error=error)


@app.route("/oauth-setup")
def oauth_setup():
    """Affiche l'URI de redirection exacte a enregistrer dans le portail Discord."""
    if not (DISCORD_CLIENT_ID and os.environ.get("DASHBOARD_BASE_URL", "").strip()):
        return (
            "Configure DASHBOARD_BASE_URL et DISCORD_CLIENT_ID sur Railway, puis recharge cette page.",
            503,
        )
    redirect_uri = _oauth_redirect_uri()
    return (
        f"<h1>Configuration OAuth Discord</h1>"
        f"<p>Ajoute <strong>exactement</strong> cette URL dans le portail Discord "
        f"(OAuth2 → Redirects) :</p>"
        f"<pre style='background:#eee;padding:12px;font-size:14px'>{redirect_uri}</pre>"
        f"<p>Client ID : <code>{DISCORD_CLIENT_ID}</code></p>"
        f"<p><a href='/login'>Retour connexion</a></p>",
        200,
        {"Content-Type": "text/html; charset=utf-8"},
    )


@app.route("/auth/discord")
def auth_discord():
    if not _dashboard_ready() or not session.get("pw_ok"):
        return redirect(url_for("login"))
    state = secrets_module.token_urlsafe(24)
    session["oauth_state"] = state
    redirect_uri = _oauth_redirect_uri()
    logger.info("OAuth redirect_uri=%s client_id=%s", redirect_uri, DISCORD_CLIENT_ID)
    params = {
        "client_id": DISCORD_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "identify",
        "state": state,
        "prompt": "consent",
    }
    return redirect(f"{DISCORD_API_BASE}/oauth2/authorize?{urlencode(params)}")


@app.route("/callback")
def oauth_callback():
    if not _dashboard_ready() or not session.get("pw_ok"):
        return redirect(url_for("login"))
    # Verif CSRF
    if not request.args.get("state") or request.args.get("state") != session.get("oauth_state"):
        return "Etat OAuth invalide. Reessaie de te connecter.", 400
    code = request.args.get("code")
    if not code:
        return redirect(url_for("login"))
    try:
        token_resp = requests.post(
            f"{DISCORD_API_BASE}/oauth2/token",
            data={
                "client_id": DISCORD_CLIENT_ID,
                "client_secret": DISCORD_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": _oauth_redirect_uri(),
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
        token_resp.raise_for_status()
        access_token = token_resp.json().get("access_token")
        if not access_token:
            return "Echec de l'authentification Discord.", 401
        me = requests.get(
            f"{DISCORD_API_BASE}/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15,
        )
        me.raise_for_status()
        user = me.json()
        user_id = int(user["id"])
    except Exception as e:
        print(f"OAuth error: {e}")
        return "Erreur lors de l'authentification Discord.", 502

    access = _check_dashboard_access(user_id)
    if access == "no_role_configured":
        session.clear()
        return (
            "⚠️ Aucun rôle admin n'est configuré sur le serveur. "
            "Un administrateur doit d'abord lancer la commande /setup dans Discord "
            "pour définir le rôle admin, puis tu pourras te connecter.",
            403,
        )
    if access != "ok":
        session.clear()
        return (
            "Accès refusé : tu dois être membre du serveur ET posséder le rôle admin "
            "configuré dans le setup.",
            403,
        )

    # Authentifie
    session.pop("pw_ok", None)
    session.pop("oauth_state", None)
    session["authenticated"] = True
    session["discord_user_id"] = user_id
    session["discord_username"] = user.get("username")
    next_path = session.pop("post_login_next", None)
    return redirect(next_path if next_path else url_for("dashboard"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


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
        gs = getattr(discord_bot, 'guild_settings', None) or guild_settings
        
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
        gs = getattr(discord_bot, 'guild_settings', None) or guild_settings
        
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