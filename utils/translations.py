"""
Multi-language support for the Discord bot
Supports English (default) and French
"""

import discord
from typing import Dict, Any

# Language translations
TRANSLATIONS = {
    'en': {
        # Common messages
        'no_permission': "❌ You don't have permission to use this command.",
        'error_occurred': "❌ An error occurred.",
        'success': "✅ Success!",
        'user': "User",
        'moderator': "Moderator",
        'reason': "Reason",
        'duration': "Duration",
        'channel': "Channel",
        'messages_deleted': "Messages Deleted",
        'expires': "Expires",
        'target_user': "Target User",
        
        # Raid mode
        'raid_enabled': "🚨 Raid Mode Enabled",
        'raid_disabled': "✅ Raid Mode Disabled",
        'raid_status': "📊 Raid Mode Status",
        'raid_scanning': "Scanning for spam for 3 seconds...",
        'raid_locked_channels': "Locked all text channels to prevent spam",
        'raid_restored_permissions': "Restored previous channel permissions",
        'raid_currently_active': "Currently Active",
        'raid_currently_inactive': "Currently Inactive",
        'raid_setup_complete': "Raid mode setup completed",
        
        # Warning system
        'warning_issued': "⚠️ Warning Issued",
        'warning_recorded': "Warning has been recorded in the database",
        'warnings_for_user': "Warnings for",
        'no_warnings_found': "No warnings found for this user",
        'warnings_cleared': "All warnings cleared for",
        'warning_detected': "Warning detected from",
        
        # Moderation commands
        'channel_locked': "🔒 Channel Locked",
        'channel_unlocked': "🔓 Channel Unlocked",
        'channel_already_locked': "🔒 Channel Already Locked",
        'channel_not_locked': "🔓 Channel Not Locked",
        'messages_cleared': "🗑️ Messages Cleared",
        'user_banned': "🔨 User Banned",
        'user_kicked': "👢 User Kicked",
        'user_muted': "🔇 User Muted",
        'user_unmuted': "🔊 User Unmuted",
        'user_not_muted': "This user is not currently muted",
        
        # DM notifications
        'dm_banned_title': "You have been banned",
        'dm_banned_desc': "You have been banned from **{guild_name}**",
        'dm_kicked_title': "You have been kicked",
        'dm_kicked_desc': "You have been kicked from **{guild_name}**",
        'dm_muted_title': "You have been muted",
        'dm_muted_desc': "You have been muted in **{guild_name}**",
        
        # Dashboard
        'web_dashboard': "🌐 Web Dashboard",
        'dashboard_desc': "Access the online dashboard to monitor and manage your bot",
        'dashboard_features': "**Features:**\n• Real-time bot statistics and monitoring\n• Warning management from all moderation bots\n• Server configuration and setup status\n• Cross-platform user safety tracking",
        'dashboard_pages': "**Available Pages:**\n• Main Dashboard - Live statistics and overview\n• Warnings - Filter and search warning history\n• Guilds - Server management and configuration",
        'dashboard_auto_refresh': "Dashboard updates automatically every 30 seconds",
        
        # Error messages
        'invalid_amount': "Amount must be between 1 and 100 messages",
        'invalid_duration': "Duration must be between 1 minute and 40320 minutes (28 days)",
        'cannot_target_higher_role': "You cannot target a user with equal or higher role than you",
        'cannot_target_self': "You cannot target yourself",
        'no_manage_messages': "I don't have permission to delete messages in this channel",
        'no_ban_permission': "I don't have permission to ban this user",
        'no_kick_permission': "I don't have permission to kick this user",
        'no_timeout_permission': "I don't have permission to timeout this user",
        'no_channel_permission': "I don't have permission to modify channel permissions",
        
        # Command descriptions
        'cmd_raid_on': "Enable raid mode - locks down all text channels",
        'cmd_raid_off': "Disable raid mode - restores previous channel permissions",
        'cmd_raid_status': "Check the current status of raid mode",
        'cmd_raid_setup': "Configure log and announcement channels for raid notifications",
        'cmd_warn': "Issue a warning to a user",
        'cmd_warnlist': "Display warnings for a user",
        'cmd_clearwarns': "Clear all warnings for a user",
        'cmd_dashboard': "Get the web dashboard link",
        'cmd_lock': "Lock a channel to prevent regular members from sending messages",
        'cmd_unlock': "Unlock a channel to restore normal permissions",
        'cmd_clear': "Delete a specified number of messages from the channel",
        'cmd_ban': "Ban a user from the server",
        'cmd_kick': "Kick a user from the server",
        'cmd_mute': "Temporarily mute a user using Discord's timeout feature",
        'cmd_unmute': "Remove timeout from a muted user",
        
        # Language configuration
        'language_config': "🌐 Language Configuration",
        'choose_language': "Choose the bot's language for this server:",
        'react_to_select': "React with {flag} to select",
        'language_set': "Language set to **{language}**",
        'language_timeout': "⏰ Timeout - Language selection timed out. Please try again.",
        
        # Setup process
        'setup_welcome': "🛠️ Bot Setup",
        'setup_welcome_desc': "Let's configure your bot step by step. Type 'cancel' at any time to stop.",
        'setup_log_channel': "**Step 1/4: Log Channel**\nPlease mention the channel where you want raid logs to be sent (e.g. #logs), or type 'skip' to skip this step:",
        'setup_announcement_channel': "**Step 2/4: Announcement Channel**\nPlease mention the channel for raid announcements (e.g. #announcements), or type 'skip' to skip:",
        'setup_admin_role': "**Step 3/4: Admin Role**\nPlease mention the role that can use raid commands (e.g. @Moderator), or type 'skip' to skip:",
        'setup_member_role': "**Step 4/4: Member Role**\nPlease mention the default member role (e.g. @Member), or type 'skip' to skip:",
        'setup_complete': "✅ Setup Complete!",
        'setup_summary': "Here's your configuration summary:",
        'setup_cancelled': "❌ Setup Cancelled",
        'setup_timeout': "⏰ Setup timed out. Please run the command again.",
        'invalid_channel': "❌ Invalid channel. Please mention a valid channel or type 'skip'.",
        'invalid_role': "❌ Invalid role. Please mention a valid role or type 'skip'.",
        'not_configured': "Not configured",
    },
    
    'fr': {
        # Messages communs
        'no_permission': "❌ Vous n'avez pas la permission d'utiliser cette commande.",
        'error_occurred': "❌ Une erreur s'est produite.",
        'success': "✅ Succès !",
        'user': "Utilisateur",
        'moderator': "Modérateur",
        'reason': "Raison",
        'duration': "Durée",
        'channel': "Canal",
        'messages_deleted': "Messages Supprimés",
        'expires': "Expire",
        'target_user': "Utilisateur Ciblé",
        
        # Mode raid
        'raid_enabled': "🚨 Mode Raid Activé",
        'raid_disabled': "✅ Mode Raid Désactivé",
        'raid_status': "📊 Statut du Mode Raid",
        'raid_scanning': "Analyse des spams pendant 3 secondes...",
        'raid_locked_channels': "Tous les canaux texte verrouillés pour prévenir le spam",
        'raid_restored_permissions': "Permissions précédentes restaurées",
        'raid_currently_active': "Actuellement Actif",
        'raid_currently_inactive': "Actuellement Inactif",
        'raid_setup_complete': "Configuration du mode raid terminée",
        
        # Système d'avertissement
        'warning_issued': "⚠️ Avertissement Émis",
        'warning_recorded': "L'avertissement a été enregistré dans la base de données",
        'warnings_for_user': "Avertissements pour",
        'no_warnings_found': "Aucun avertissement trouvé pour cet utilisateur",
        'warnings_cleared': "Tous les avertissements effacés pour",
        'warning_detected': "Avertissement détecté de",
        
        # Commandes de modération
        'channel_locked': "🔒 Canal Verrouillé",
        'channel_unlocked': "🔓 Canal Déverrouillé",
        'channel_already_locked': "🔒 Canal Déjà Verrouillé",
        'channel_not_locked': "🔓 Canal Non Verrouillé",
        'messages_cleared': "🗑️ Messages Supprimés",
        'user_banned': "🔨 Utilisateur Banni",
        'user_kicked': "👢 Utilisateur Expulsé",
        'user_muted': "🔇 Utilisateur Muet",
        'user_unmuted': "🔊 Utilisateur Démuet",
        'user_not_muted': "Cet utilisateur n'est pas actuellement muet",
        
        # Notifications MP
        'dm_banned_title': "Vous avez été banni",
        'dm_banned_desc': "Vous avez été banni de **{guild_name}**",
        'dm_kicked_title': "Vous avez été expulsé",
        'dm_kicked_desc': "Vous avez été expulsé de **{guild_name}**",
        'dm_muted_title': "Vous avez été rendu muet",
        'dm_muted_desc': "Vous avez été rendu muet dans **{guild_name}**",
        
        # Tableau de bord
        'web_dashboard': "🌐 Tableau de Bord Web",
        'dashboard_desc': "Accédez au tableau de bord en ligne pour surveiller et gérer votre bot",
        'dashboard_features': "**Fonctionnalités :**\n• Statistiques en temps réel et surveillance du bot\n• Gestion des avertissements de tous les bots de modération\n• Configuration du serveur et statut de configuration\n• Suivi de sécurité utilisateur multi-plateforme",
        'dashboard_pages': "**Pages Disponibles :**\n• Tableau de Bord Principal - Statistiques en direct et aperçu\n• Avertissements - Filtrer et rechercher l'historique des avertissements\n• Serveurs - Gestion et configuration des serveurs",
        'dashboard_auto_refresh': "Le tableau de bord se met à jour automatiquement toutes les 30 secondes",
        
        # Messages d'erreur
        'invalid_amount': "La quantité doit être entre 1 et 100 messages",
        'invalid_duration': "La durée doit être entre 1 minute et 40320 minutes (28 jours)",
        'cannot_target_higher_role': "Vous ne pouvez pas cibler un utilisateur avec un rôle égal ou supérieur au vôtre",
        'cannot_target_self': "Vous ne pouvez pas vous cibler vous-même",
        'no_manage_messages': "Je n'ai pas la permission de supprimer des messages dans ce canal",
        'no_ban_permission': "Je n'ai pas la permission de bannir cet utilisateur",
        'no_kick_permission': "Je n'ai pas la permission d'expulser cet utilisateur",
        'no_timeout_permission': "Je n'ai pas la permission de rendre muet cet utilisateur",
        'no_channel_permission': "Je n'ai pas la permission de modifier les permissions du canal",
        
        # Descriptions des commandes
        'cmd_raid_on': "Activer le mode raid - verrouille tous les canaux texte",
        'cmd_raid_off': "Désactiver le mode raid - restaure les permissions précédentes",
        'cmd_raid_status': "Vérifier le statut actuel du mode raid",
        'cmd_raid_setup': "Configurer les canaux de log et d'annonce pour les notifications de raid",
        'cmd_warn': "Émettre un avertissement à un utilisateur",
        'cmd_warnlist': "Afficher les avertissements pour un utilisateur",
        'cmd_clearwarns': "Effacer tous les avertissements pour un utilisateur",
        'cmd_dashboard': "Obtenir le lien du tableau de bord web",
        'cmd_lock': "Verrouiller un canal pour empêcher les membres réguliers d'envoyer des messages",
        'cmd_unlock': "Déverrouiller un canal pour restaurer les permissions normales",
        'cmd_clear': "Supprimer un nombre spécifié de messages du canal",
        'cmd_ban': "Bannir un utilisateur du serveur",
        'cmd_kick': "Expulser un utilisateur du serveur",
        'cmd_mute': "Rendre temporairement muet un utilisateur en utilisant la fonction de timeout de Discord",
        'cmd_unmute': "Retirer le timeout d'un utilisateur muet",
        
        # Configuration de langue
        'language_config': "🌐 Configuration de Langue",
        'choose_language': "Choisissez la langue du bot pour ce serveur :",
        'react_to_select': "Réagissez avec {flag} pour sélectionner",
        'language_set': "Langue définie sur **{language}**",
        'language_timeout': "⏰ Délai dépassé - La sélection de langue a expiré. Veuillez réessayer.",
        
        # Processus de configuration
        'setup_welcome': "🛠️ Configuration du Bot",
        'setup_welcome_desc': "Configurons votre bot étape par étape. Tapez 'annuler' à tout moment pour arrêter.",
        'setup_log_channel': "**Étape 1/4 : Canal de Log**\nVeuillez mentionner le canal où vous voulez que les logs de raid soient envoyés (ex: #logs), ou tapez 'passer' pour ignorer cette étape :",
        'setup_announcement_channel': "**Étape 2/4 : Canal d'Annonces**\nVeuillez mentionner le canal pour les annonces de raid (ex: #annonces), ou tapez 'passer' pour ignorer :",
        'setup_admin_role': "**Étape 3/4 : Rôle Admin**\nVeuillez mentionner le rôle qui peut utiliser les commandes de raid (ex: @Modérateur), ou tapez 'passer' pour ignorer :",
        'setup_member_role': "**Étape 4/4 : Rôle Membre**\nVeuillez mentionner le rôle membre par défaut (ex: @Membre), ou tapez 'passer' pour ignorer :",
        'setup_complete': "✅ Configuration Terminée !",
        'setup_summary': "Voici le résumé de votre configuration :",
        'setup_cancelled': "❌ Configuration Annulée",
        'setup_timeout': "⏰ Configuration expirée. Veuillez relancer la commande.",
        'invalid_channel': "❌ Canal invalide. Veuillez mentionner un canal valide ou tapez 'passer'.",
        'invalid_role': "❌ Rôle invalide. Veuillez mentionner un rôle valide ou tapez 'passer'.",
        'not_configured': "Non configuré",
    }
}

# Guild language preferences stored in file for persistence
import json
import os
from pathlib import Path

LANGUAGES_FILE = Path("guild_languages.json")

def _load_guild_languages() -> dict:
    """Load guild language preferences from file"""
    if LANGUAGES_FILE.exists():
        try:
            with open(LANGUAGES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Convert string keys back to int
                return {int(k): v for k, v in data.items()}
        except (json.JSONDecodeError, ValueError):
            pass
    return {}

def _save_guild_languages(languages: dict) -> None:
    """Save guild language preferences to file"""
    try:
        # Convert int keys to string for JSON
        data = {str(k): v for k, v in languages.items()}
        with open(LANGUAGES_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving guild languages: {e}")

# Load existing preferences
GUILD_LANGUAGES = _load_guild_languages()

def get_guild_language(guild_id: int) -> str:
    """Get the preferred language for a guild"""
    return GUILD_LANGUAGES.get(guild_id, 'en')

def set_guild_language(guild_id: int, language: str) -> bool:
    """Set the preferred language for a guild"""
    if language in TRANSLATIONS:
        GUILD_LANGUAGES[guild_id] = language
        _save_guild_languages(GUILD_LANGUAGES)
        return True
    return False

def get_text(guild_id: int, key: str, **kwargs) -> str:
    """Get translated text for a guild"""
    language = get_guild_language(guild_id)
    
    # Fallback to English if key not found in selected language
    if key in TRANSLATIONS[language]:
        text = TRANSLATIONS[language][key]
    elif key in TRANSLATIONS['en']:
        text = TRANSLATIONS['en'][key]
    else:
        return f"[Missing translation: {key}]"
    
    # Format with provided arguments
    if kwargs:
        try:
            return text.format(**kwargs)
        except KeyError:
            return text
    
    return text

def get_available_languages() -> Dict[str, str]:
    """Get list of available languages"""
    return {
        'en': 'English',
        'fr': 'Français'
    }

def create_embed(guild_id: int, title_key: str, description_key: str = None, color: discord.Color = discord.Color.blue(), **kwargs) -> discord.Embed:
    """Create a translated embed"""
    title = get_text(guild_id, title_key, **kwargs)
    
    if description_key:
        description = get_text(guild_id, description_key, **kwargs)
        embed = discord.Embed(title=title, description=description, color=color)
    else:
        embed = discord.Embed(title=title, color=color)
    
    return embed