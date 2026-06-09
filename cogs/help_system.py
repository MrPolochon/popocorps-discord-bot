import discord
from discord.ext import commands
from discord import app_commands
from typing import Dict, List
from utils.translations import get_text, get_guild_language

class HelpView(discord.ui.View):
    """Interactive help view with pagination"""
    
    def __init__(self, guild_id: int):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.guild_id = guild_id
        self.current_page = 0
        self.pages = self._create_help_pages()
        self.max_pages = len(self.pages)
        
    def _create_help_pages(self) -> List[Dict]:
        """Create help pages with commands organized by category"""
        lang = get_guild_language(self.guild_id)
        
        if lang == 'fr':
            pages = [
                {
                    "title": "📖 Guide d'Aide - Page 1/7",
                    "description": "**Bienvenue dans le système d'aide du bot de protection**\n\nUtilisez les boutons ci-dessous pour naviguer entre les différentes sections.",
                    "fields": [
                        {
                            "name": "🛡️ Protection contre les Raids",
                            "value": "Commandes pour activer et gérer la protection contre les raids",
                            "inline": False
                        },
                        {
                            "name": "⚠️ Système d'Avertissements",
                            "value": "Gestion des avertissements et modération des utilisateurs",
                            "inline": False
                        },
                        {
                            "name": "🔨 Commandes de Modération",
                            "value": "Outils de modération pour gérer votre serveur",
                            "inline": False
                        },
                        {
                            "name": "🤖 Fonctionnalités Automatiques",
                            "value": "Surveillance 24/7, détection de spam et alertes intelligentes",
                            "inline": False
                        },
                        {
                            "name": "⚙️ Configuration",
                            "value": "Configuration du bot et paramètres du serveur",
                            "inline": False
                        },
                        {
                            "name": "🧪 Tests et Diagnostics",
                            "value": "Outils de test et diagnostic du système",
                            "inline": False
                        }
                    ],
                    "color": discord.Color.blue()
                },
                {
                    "title": "🛡️ Protection contre les Raids - Page 2/7",
                    "description": "**Commandes de protection contre les raids**\n\nCes commandes vous aident à protéger votre serveur contre les attaques de spam et les raids.",
                    "fields": [
                        {
                            "name": "/raid on",
                            "value": "🟢 **Active le mode raid**\nVerrouille tous les canaux texte pour empêcher le spam\n*Permissions: Gérer le serveur*",
                            "inline": False
                        },
                        {
                            "name": "/raid off", 
                            "value": "🔴 **Désactive le mode raid**\nRestaure les permissions précédentes des canaux\n*Permissions: Gérer le serveur*",
                            "inline": False
                        },
                        {
                            "name": "/raid status",
                            "value": "ℹ️ **Vérifie le statut du mode raid**\nAffiche si le mode raid est actif ou inactif\n*Permissions: Aucune*",
                            "inline": False
                        },
                        {
                            "name": "/setup",
                            "value": "⚙️ **Configure le serveur**\nSalons logs/annonces, rôles admin et membre (requis pour le lockdown)\n*Permissions: Gérer le serveur*",
                            "inline": False
                        },
                        {
                            "name": "/raid help",
                            "value": "📖 **Aide anti-raid détaillée**\nGuide complet du système de protection\n*Permissions: Aucune*",
                            "inline": False
                        }
                    ],
                    "color": discord.Color.red()
                },
                {
                    "title": "⚠️ Système d'Avertissements - Page 3/7",
                    "description": "**Gestion des avertissements**\n\nSystème complet de suivi des avertissements avec détection automatique des autres bots de modération.",
                    "fields": [
                        {
                            "name": "/warn <utilisateur> [raison]",
                            "value": "⚠️ **Émet un avertissement**\nDonne un avertissement à un utilisateur avec une raison optionnelle\n*Permissions: Gérer le serveur*",
                            "inline": False
                        },
                        {
                            "name": "/warnlist [utilisateur]",
                            "value": "📋 **Affiche les avertissements**\nMontre tous les avertissements d'un utilisateur\n*Permissions: Gérer le serveur*",
                            "inline": False
                        },
                        {
                            "name": "/clearwarns <utilisateur>",
                            "value": "🗑️ **Efface les avertissements**\nSupprime tous les avertissements d'un utilisateur\n*Permissions: Gérer le serveur*",
                            "inline": False
                        },
                        {
                            "name": "/dashboard",
                            "value": "🌐 **Tableau de bord web**\nAccédez au tableau de bord en ligne pour gérer les avertissements\n*Permissions: Aucune*",
                            "inline": False
                        }
                    ],
                    "color": discord.Color.orange()
                },
                {
                    "title": "🔨 Commandes de Modération - Page 4/7",
                    "description": "**Outils de modération avancés**\n\nCommandes pour gérer et modérer votre serveur efficacement.",
                    "fields": [
                        {
                            "name": "/lock [canal] [raison]",
                            "value": "🔒 **Verrouille un canal**\nEmpêche les membres normaux d'envoyer des messages\n*Permissions: Gérer les canaux*",
                            "inline": False
                        },
                        {
                            "name": "/unlock [canal] [raison]",
                            "value": "🔓 **Déverrouille un canal**\nRestaure les permissions normales du canal\n*Permissions: Gérer les canaux*",
                            "inline": False
                        },
                        {
                            "name": "/clear <nombre> [utilisateur]",
                            "value": "🗑️ **Supprime des messages**\nSupprime un nombre spécifié de messages (1-100)\n*Permissions: Gérer les messages*",
                            "inline": False
                        },
                        {
                            "name": "/ban <utilisateur> [raison]",
                            "value": "🔨 **Bannit un utilisateur**\nBannit définitivement un utilisateur du serveur\n*Permissions: Bannir des membres*",
                            "inline": False
                        },
                        {
                            "name": "/kick <utilisateur> [raison]",
                            "value": "👢 **Expulse un utilisateur**\nExpulse un utilisateur du serveur\n*Permissions: Expulser des membres*",
                            "inline": False
                        },
                        {
                            "name": "/mute <utilisateur> <durée> [raison]",
                            "value": "🔇 **Rend muet un utilisateur**\nRend temporairement muet un utilisateur (max 28 jours)\n*Permissions: Modérer les membres*",
                            "inline": False
                        },
                        {
                            "name": "/unmute <utilisateur> [raison]",
                            "value": "🔊 **Retire le silence**\nRetire le timeout d'un utilisateur muet\n*Permissions: Modérer les membres*",
                            "inline": False
                        }
                    ],
                    "color": discord.Color.dark_red()
                },
                {
                    "title": "⚙️ Configuration - Page 5/6",
                    "description": "**Configuration et paramètres**\n\nCommandes pour configurer le bot selon vos besoins.",
                    "fields": [
                        {
                            "name": "/language",
                            "value": "🌐 **Configure la langue**\nDéfinit la langue du bot pour ce serveur (Français/Anglais)\n*Permissions: Gérer le serveur*",
                            "inline": False
                        },
                        {
                            "name": "Détection Automatique",
                            "value": "🤖 **Surveillance 24/7**\nLe bot surveille automatiquement:\n• Les spams et attaques coordonnées\n• Les avertissements d'autres bots\n• Les changements de permissions critiques\n• Les activités suspectes",
                            "inline": False
                        },
                        {
                            "name": "Alertes Intelligentes",
                            "value": "🧠 **Système d'alertes intelligent**\nLes alertes critiques ne se déclenchent que pour:\n• Les actions non-administrateurs\n• Les changements de sécurité suspects\n• Les attaques de spam détectées",
                            "inline": False
                        }
                    ],
                    "color": discord.Color.green()
                },
                {
                    "title": "🤖 Fonctionnalités Automatiques - Page 6/7",
                    "description": "**Surveillance et protection automatique 24/7**\n\nLe bot surveille en permanence votre serveur et réagit automatiquement aux menaces.",
                    "fields": [
                        {
                            "name": "🕐 Surveillance Continue",
                            "value": "**Surveillance 24/7 des messages**\nLe bot analyse tous les messages en temps réel pour détecter:\n• Spam et messages répétitifs\n• Attaques coordonnées entre plusieurs utilisateurs\n• Patterns de raid (nouveaux membres + spam immédiat)\n• Contenus suspects et comportements anormaux",
                            "inline": False
                        },
                        {
                            "name": "🧠 Alertes Intelligentes",
                            "value": "**Système d'alertes intelligent**\nLes alertes critiques se déclenchent uniquement pour:\n• Actions effectuées par des non-administrateurs\n• Modifications dangereuses de permissions\n• Changements de rôles suspects\n• Attribution de permissions sensibles\n• Suppressions/modifications de canaux critiques",
                            "inline": False
                        },
                        {
                            "name": "🔍 Double Scan Anti-Raid",
                            "value": "**Mode raid avec double vérification**\nQuand activé via `/raid on` :\n• Double scan de 3 secondes pour détecter le spam\n• Verrouillage des salons pour le rôle membre\n• Pause des invitations\n• Suppression auto + timeout des flooders",
                            "inline": False
                        },
                        {
                            "name": "⚡ Détection d'Attaques Coordonnées",
                            "value": "**Protection contre les raids organisés**\n• Détection de messages identiques envoyés par plusieurs utilisateurs\n• Identification des raids de nouveaux comptes\n• Alertes immédiates au staff en cas d'attaque massive\n• Analyse des patterns de comportement suspects",
                            "inline": False
                        },
                        {
                            "name": "📊 Suivi Universel des Avertissements",
                            "value": "**Surveillance multi-bots**\nLe bot capture automatiquement:\n• Avertissements de DraftBot, Carl-bot, MEE6, etc.\n• Sanctions émises par d'autres bots de modération\n• Historique complet centralisé par utilisateur\n• Tracking des récidivistes sur tous les systèmes",
                            "inline": False
                        },
                        {
                            "name": "📈 Niveaux de Risque Gradués",
                            "value": "**Évaluation intelligente des menaces**\n• **Faible** : log silencieux\n• **Modéré** : notification staff\n• **Élevé** : alerte critique\n• **Critique** : auto-raid si activé dans le tableau de bord",
                            "inline": False
                        }
                    ],
                    "color": discord.Color.from_rgb(138, 43, 226)
                },
                {
                    "title": "🧪 Tests et Diagnostics - Page 7/7",
                    "description": "**Outils de diagnostic**\n\nCommandes pour tester et diagnostiquer le système.",
                    "fields": [
                        {
                            "name": "/ping",
                            "value": "🏓 **Test de connectivité**\nVérifie si le bot répond et affiche la latence\n*Permissions: Aucune*",
                            "inline": False
                        },
                        {
                            "name": "/testsystem",
                            "value": "🧪 **Test complet du système**\nEffectue un test complet de tous les systèmes du bot avec rapport détaillé\n*Permissions: Gérer le serveur*",
                            "inline": False
                        },
                        {
                            "name": "Support",
                            "value": "💬 **Besoin d'aide?**\nSi vous rencontrez des problèmes:\n• Vérifiez les permissions du bot\n• Consultez les logs dans votre canal de log configuré\n• Utilisez `/testsystem` pour diagnostiquer les problèmes",
                            "inline": False
                        },
                        {
                            "name": "Permissions Requises",
                            "value": "🔑 **Permissions importantes**\nLe bot a besoin de:\n• Gérer les canaux (pour le mode raid)\n• Gérer les messages (pour la suppression)\n• Voir les logs d'audit (pour les alertes intelligentes)\n• Envoyer des messages et embeds",
                            "inline": False
                        }
                    ],
                    "color": discord.Color.purple()
                }
            ]
        else:  # English
            pages = [
                {
                    "title": "📖 Help Guide - Page 1/7",
                    "description": "**Welcome to the protection bot help system**\n\nUse the buttons below to navigate between different sections.",
                    "fields": [
                        {
                            "name": "🛡️ Raid Protection",
                            "value": "Commands to activate and manage raid protection",
                            "inline": False
                        },
                        {
                            "name": "⚠️ Warning System",
                            "value": "Warning management and user moderation",
                            "inline": False
                        },
                        {
                            "name": "🔨 Moderation Commands",
                            "value": "Moderation tools to manage your server",
                            "inline": False
                        },
                        {
                            "name": "🤖 Automatic Features",
                            "value": "24/7 monitoring, spam detection and intelligent alerts",
                            "inline": False
                        },
                        {
                            "name": "⚙️ Configuration",
                            "value": "Bot configuration and server settings",
                            "inline": False
                        },
                        {
                            "name": "🧪 Testing & Diagnostics",
                            "value": "System testing and diagnostic tools",
                            "inline": False
                        }
                    ],
                    "color": discord.Color.blue()
                },
                {
                    "title": "🛡️ Raid Protection - Page 2/7",
                    "description": "**Raid protection commands**\n\nThese commands help protect your server against spam attacks and raids.",
                    "fields": [
                        {
                            "name": "/raid on",
                            "value": "🟢 **Enable raid mode**\nLocks all text channels to prevent spam\n*Permissions: Manage Server*",
                            "inline": False
                        },
                        {
                            "name": "/raid off",
                            "value": "🔴 **Disable raid mode**\nRestores previous channel permissions\n*Permissions: Manage Server*",
                            "inline": False
                        },
                        {
                            "name": "/raid status",
                            "value": "ℹ️ **Check raid mode status**\nShows if raid mode is active or inactive\n*Permissions: None*",
                            "inline": False
                        },
                        {
                            "name": "/setup",
                            "value": "⚙️ **Configure the server**\nLog/announcement channels, admin and member roles\n*Permissions: Manage Server*",
                            "inline": False
                        },
                        {
                            "name": "/raid help",
                            "value": "📖 **Detailed raid protection help**\n*Permissions: None*",
                            "inline": False
                        }
                    ],
                    "color": discord.Color.red()
                },
                {
                    "title": "⚠️ Warning System - Page 3/7",
                    "description": "**Warning management**\n\nComprehensive warning tracking system with automatic detection from other moderation bots.",
                    "fields": [
                        {
                            "name": "/warn <user> [reason]",
                            "value": "⚠️ **Issue a warning**\nGive a warning to a user with optional reason\n*Permissions: Manage Server*",
                            "inline": False
                        },
                        {
                            "name": "/warnlist [user]",
                            "value": "📋 **Display warnings**\nShow all warnings for a user\n*Permissions: Manage Server*",
                            "inline": False
                        },
                        {
                            "name": "/clearwarns <user>",
                            "value": "🗑️ **Clear warnings**\nRemove all warnings for a user\n*Permissions: Manage Server*",
                            "inline": False
                        },
                        {
                            "name": "/dashboard",
                            "value": "🌐 **Web dashboard**\nAccess the online dashboard to manage warnings\n*Permissions: None*",
                            "inline": False
                        }
                    ],
                    "color": discord.Color.orange()
                },
                {
                    "title": "🔨 Moderation Commands - Page 4/7",
                    "description": "**Advanced moderation tools**\n\nCommands to effectively manage and moderate your server.",
                    "fields": [
                        {
                            "name": "/lock [channel] [reason]",
                            "value": "🔒 **Lock a channel**\nPrevents regular members from sending messages\n*Permissions: Manage Channels*",
                            "inline": False
                        },
                        {
                            "name": "/unlock [channel] [reason]",
                            "value": "🔓 **Unlock a channel**\nRestores normal channel permissions\n*Permissions: Manage Channels*",
                            "inline": False
                        },
                        {
                            "name": "/clear <amount> [user]",
                            "value": "🗑️ **Delete messages**\nDelete a specified number of messages (1-100)\n*Permissions: Manage Messages*",
                            "inline": False
                        },
                        {
                            "name": "/ban <user> [reason]",
                            "value": "🔨 **Ban a user**\nPermanently ban a user from the server\n*Permissions: Ban Members*",
                            "inline": False
                        },
                        {
                            "name": "/kick <user> [reason]",
                            "value": "👢 **Kick a user**\nKick a user from the server\n*Permissions: Kick Members*",
                            "inline": False
                        },
                        {
                            "name": "/mute <user> <duration> [reason]",
                            "value": "🔇 **Mute a user**\nTemporarily mute a user (max 28 days)\n*Permissions: Moderate Members*",
                            "inline": False
                        },
                        {
                            "name": "/unmute <user> [reason]",
                            "value": "🔊 **Unmute a user**\nRemove timeout from a muted user\n*Permissions: Moderate Members*",
                            "inline": False
                        }
                    ],
                    "color": discord.Color.dark_red()
                },
                {
                    "title": "⚙️ Configuration - Page 5/6",
                    "description": "**Configuration and settings**\n\nCommands to configure the bot according to your needs.",
                    "fields": [
                        {
                            "name": "/language",
                            "value": "🌐 **Configure language**\nSet the bot language for this server (French/English)\n*Permissions: Manage Server*",
                            "inline": False
                        },
                        {
                            "name": "Automatic Detection",
                            "value": "🤖 **24/7 Monitoring**\nThe bot automatically monitors:\n• Spam and coordinated attacks\n• Warnings from other bots\n• Critical permission changes\n• Suspicious activities",
                            "inline": False
                        },
                        {
                            "name": "Intelligent Alerts",
                            "value": "🧠 **Smart alert system**\nCritical alerts only trigger for:\n• Non-administrator actions\n• Suspicious security changes\n• Detected spam attacks",
                            "inline": False
                        }
                    ],
                    "color": discord.Color.green()
                },
                {
                    "title": "🤖 Automatic Features - Page 6/7",
                    "description": "**24/7 Automatic monitoring and protection**\n\nThe bot continuously monitors your server and automatically responds to threats.",
                    "fields": [
                        {
                            "name": "🕐 Continuous Monitoring",
                            "value": "**24/7 Message surveillance**\nThe bot analyzes all messages in real-time to detect:\n• Spam and repetitive messages\n• Coordinated attacks between multiple users\n• Raid patterns (new members + immediate spam)\n• Suspicious content and abnormal behaviors",
                            "inline": False
                        },
                        {
                            "name": "🧠 Intelligent Alerts",
                            "value": "**Smart alert system**\nCritical alerts only trigger for:\n• Actions performed by non-administrators\n• Dangerous permission modifications\n• Suspicious role changes\n• Sensitive permission assignments\n• Critical channel deletions/modifications",
                            "inline": False
                        },
                        {
                            "name": "🔍 Double-Scan Anti-Raid",
                            "value": "**Raid mode with double verification**\nWhen enabled, raid mode performs:\n• First 3-second scan to detect spam\n• Second 3-second scan for confirmation\n• Automatic channel lockdown if threat confirmed\n• Detailed spammer report to moderators",
                            "inline": False
                        },
                        {
                            "name": "⚡ Coordinated Attack Detection",
                            "value": "**Protection against organized raids**\n• Detection of identical messages sent by multiple users\n• Identification of new account raids\n• Immediate staff alerts for massive attacks\n• Analysis of suspicious behavior patterns",
                            "inline": False
                        },
                        {
                            "name": "📊 Universal Warning Tracking",
                            "value": "**Multi-bot surveillance**\nThe bot automatically captures:\n• Warnings from DraftBot, Carl-bot, MEE6, etc.\n• Sanctions issued by other moderation bots\n• Complete centralized user history\n• Repeat offender tracking across all systems",
                            "inline": False
                        },
                        {
                            "name": "📈 Graduated Risk Levels",
                            "value": "**Intelligent threat assessment**\n• **Low**: Minor suspicious activity, silent logging\n• **Moderate**: Problematic behavior, staff notification\n• **High**: Confirmed threat, immediate critical alert\n• **Critical**: Active attack, automatic actions triggered",
                            "inline": False
                        }
                    ],
                    "color": discord.Color.from_rgb(138, 43, 226)
                },
                {
                    "title": "🧪 Testing & Diagnostics - Page 7/7",
                    "description": "**Diagnostic tools**\n\nCommands to test and diagnose the system.",
                    "fields": [
                        {
                            "name": "/ping",
                            "value": "🏓 **Connectivity test**\nChecks if the bot is responding and displays latency\n*Permissions: None*",
                            "inline": False
                        },
                        {
                            "name": "/testsystem",
                            "value": "🧪 **Comprehensive system test**\nPerforms a complete test of all bot systems with detailed report\n*Permissions: Manage Server*",
                            "inline": False
                        },
                        {
                            "name": "Support",
                            "value": "💬 **Need help?**\nIf you encounter issues:\n• Check bot permissions\n• Review logs in your configured log channel\n• Use `/testsystem` to diagnose problems",
                            "inline": False
                        },
                        {
                            "name": "Required Permissions",
                            "value": "🔑 **Important permissions**\nThe bot needs:\n• Manage Channels (for raid mode)\n• Manage Messages (for deletion)\n• View Audit Log (for intelligent alerts)\n• Send Messages and Embeds",
                            "inline": False
                        }
                    ],
                    "color": discord.Color.purple()
                }
            ]
        
        return pages
    
    def create_embed(self) -> discord.Embed:
        """Create embed for current page"""
        page = self.pages[self.current_page]
        embed = discord.Embed(
            title=page["title"],
            description=page["description"],
            color=page["color"]
        )
        
        for field in page["fields"]:
            embed.add_field(
                name=field["name"],
                value=field["value"],
                inline=field["inline"]
            )
        
        embed.set_footer(text=f"Page {self.current_page + 1}/{self.max_pages} • Utilisez les boutons pour naviguer")
        return embed
    
    @discord.ui.button(label="◀️ Précédent", style=discord.ButtonStyle.secondary, disabled=True)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to previous page"""
        if self.current_page > 0:
            self.current_page -= 1
            self._update_buttons()
            await interaction.response.edit_message(embed=self.create_embed(), view=self)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label="🏠 Accueil", style=discord.ButtonStyle.primary)
    async def home_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to home page"""
        self.current_page = 0
        self._update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)
    
    @discord.ui.button(label="Suivant ▶️", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to next page"""
        if self.current_page < self.max_pages - 1:
            self.current_page += 1
            self._update_buttons()
            await interaction.response.edit_message(embed=self.create_embed(), view=self)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label="❌ Fermer", style=discord.ButtonStyle.danger)
    async def close_help(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Close the help menu"""
        lang = get_guild_language(self.guild_id)
        if lang == 'fr':
            embed = discord.Embed(
                title="📖 Aide Fermée",
                description="Le menu d'aide a été fermé. Utilisez `/help` pour l'ouvrir à nouveau.",
                color=discord.Color.gray()
            )
        else:
            embed = discord.Embed(
                title="📖 Help Closed",
                description="Help menu has been closed. Use `/help` to open it again.",
                color=discord.Color.gray()
            )
        
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()
    
    def _update_buttons(self):
        """Update button states based on current page"""
        # Previous button
        self.children[0].disabled = (self.current_page == 0)
        
        # Next button  
        self.children[2].disabled = (self.current_page == self.max_pages - 1)
        
        # Update button labels based on language
        lang = get_guild_language(self.guild_id)
        if lang == 'fr':
            self.children[0].label = "◀️ Précédent"
            self.children[1].label = "🏠 Accueil"
            self.children[2].label = "Suivant ▶️"
            self.children[3].label = "❌ Fermer"
        else:
            self.children[0].label = "◀️ Previous"
            self.children[1].label = "🏠 Home"
            self.children[2].label = "Next ▶️"
            self.children[3].label = "❌ Close"
    
    async def on_timeout(self):
        """Handle timeout"""
        # Disable all buttons
        for item in self.children:
            item.disabled = True

class HelpSystem(commands.Cog):
    """Comprehensive help system with interactive pagination"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="help", description="Affiche l'aide complète du bot avec navigation interactive")
    async def help_command(self, interaction: discord.Interaction):
        """Display comprehensive help with interactive navigation"""
        view = HelpView(interaction.guild.id)
        embed = view.create_embed()
        
        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(HelpSystem(bot))