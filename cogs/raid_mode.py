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

    def _raid_system_enabled(self, guild_id: int) -> bool:
        """Verifie si le systeme anti-raid est active pour ce serveur."""
        return guild_settings.get_setting(guild_id, "raid_mode_enabled", True)

    def _validate_raid_setup(self, guild: discord.Guild) -> str | None:
        """Retourne un message d'erreur si la config est incomplete."""
        if not self.get_member_role(guild):
            return (
                "⚠️ Aucun **rôle membre** configuré. Lance `/setup` pour définir "
                "le rôle membre (nécessaire au verrouillage des salons)."
            )
        if not guild.me.guild_permissions.manage_channels:
            return "⚠️ Il me manque la permission **Gérer les salons** pour verrouiller les canaux."
        return None

    @commands.Cog.listener()
    async def on_message(self, message):
        """Suivi spam en mode raid + suppression automatique des flooders."""
        if message.author.bot or not message.guild:
            return

        guild_id = message.guild.id
        if not self.raid_active.get(guild_id, False):
            return

        track_message(message)

        if message.author.id not in get_spammer_ids(guild_id):
            return

        try:
            await message.delete()
        except (discord.Forbidden, discord.NotFound):
            pass

        member = message.author
        if (
            isinstance(member, discord.Member)
            and not has_raid_mode_permission(member)
            and member.guild.me.guild_permissions.moderate_members
            and (member.top_role < member.guild.me.top_role)
        ):
            try:
                await member.timeout(
                    timedelta(minutes=10),
                    reason="Spam détecté pendant le mode raid",
                )
            except (discord.Forbidden, discord.HTTPException):
                pass

    async def cog_load(self):
        """Reinitialise les etats raid orphelins apres redemarrage."""
        for guild_id, active in list(self.raid_active.items()):
            if not active:
                continue
            self.raid_active[guild_id] = False
            self.channel_states.pop(guild_id, None)
            self.invite_states.pop(guild_id, None)
            self.save_raid_state(guild_id)
            guild = self.bot.get_guild(guild_id)
            if not guild:
                continue
            log_channel_id = guild_settings.get_log_channel(guild_id)
            if not log_channel_id:
                continue
            log_channel = guild.get_channel(log_channel_id)
            if not log_channel:
                continue
            try:
                embed = discord.Embed(
                    title="⚠️ Mode raid réinitialisé",
                    description=(
                        "Le bot a redémarré pendant un mode raid actif. "
                        "Les salons **n'ont pas été re-verrouillés** automatiquement.\n"
                        "Relance `/raid on` si la menace persiste."
                    ),
                    color=discord.Color.orange(),
                    timestamp=datetime.now(),
                )
                await log_channel.send(embed=embed)
            except Exception as e:
                logging.error("Erreur notification reset raid guild %s: %s", guild_id, e)

    async def auto_activate_raid(self, guild: discord.Guild, reason: str) -> bool:
        """Active le mode raid automatiquement (si auto_raid_enabled)."""
        guild_id = guild.id
        if self.raid_active.get(guild_id, False):
            return False
        if not guild_settings.get_setting(guild_id, "auto_raid_enabled", False):
            return False
        if not self._raid_system_enabled(guild_id):
            return False
        setup_error = self._validate_raid_setup(guild)
        if setup_error:
            logging.warning("Auto-raid impossible guild %s: %s", guild_id, setup_error)
            return False

        class _AutoInteraction:
            def __init__(self, g):
                self.guild = g
                self.user = g.me
                self.response = self
                self.followup = self

            async def defer(self, **kwargs):
                return None

            async def send(self, *args, **kwargs):
                return None

        logging.info("Auto-activation mode raid guild %s: %s", guild_id, reason)
        await self._enable_raid_mode(_AutoInteraction(guild), auto_reason=reason)
        return True

    def _register_commands(self):
        """Register slash commands for the bot."""
        raid_group = app_commands.Group(name="raid", description="Protection anti-raid")

        @raid_group.command(name="on", description="Activer le mode raid — verrouille les salons")
        async def raid_on(interaction: discord.Interaction):
            if not has_raid_mode_permission(interaction.user):
                await interaction.response.send_message(
                    get_text(interaction.guild.id, 'no_permission'),
                    ephemeral=True
                )
                return
            if not self._raid_system_enabled(interaction.guild.id):
                await interaction.response.send_message(
                    "❌ Le mode anti-raid est désactivé sur ce serveur (tableau de bord).",
                    ephemeral=True,
                )
                return
            setup_error = self._validate_raid_setup(interaction.guild)
            if setup_error:
                await interaction.response.send_message(setup_error, ephemeral=True)
                return
            await self._enable_raid_mode(interaction)

        @raid_group.command(name="off", description="Désactiver le mode raid — restaure les permissions")
        async def raid_off(interaction: discord.Interaction):
            if not has_raid_mode_permission(interaction.user):
                await interaction.response.send_message(
                    get_text(interaction.guild.id, 'no_permission'),
                    ephemeral=True
                )
                return
            await self._disable_raid_mode(interaction)

        @raid_group.command(name="status", description="Statut du mode raid et de la configuration")
        async def raid_status(interaction: discord.Interaction):
            await self._check_raid_status(interaction)

        @raid_group.command(name="help", description="Aide sur la protection anti-raid")
        async def raid_help(interaction: discord.Interaction):
            embed = discord.Embed(
                title="🛡️ Aide — Protection Anti-Raid",
                description=(
                    "PopoCorps protège votre serveur contre le spam massif et les raids coordonnés."
                ),
                color=discord.Color.blue(),
            )
            embed.add_field(
                name="Commandes principales",
                value=(
                    "🟢 `/raid on` — Active le mode raid (double scan + verrouillage)\n"
                    "🔴 `/raid off` — Désactive et restaure les permissions\n"
                    "ℹ️ `/raid status` — Affiche l'état actuel\n"
                    "🛠️ `/setup` — Configure logs, annonces, rôles admin/membre"
                ),
                inline=False,
            )
            embed.add_field(
                name="Pendant le mode raid",
                value=(
                    "• Verrouillage des salons pour le rôle membre\n"
                    "• Pause des invitations\n"
                    "• Suppression auto des messages de spammeurs\n"
                    "• Timeout 10 min des comptes floodant"
                ),
                inline=False,
            )
            embed.add_field(
                name="Surveillance 24/7",
                value=(
                    "Le bot détecte les attaques coordonnées et les raids "
                    "(nouveaux comptes + spam). Active **auto-raid** dans le "
                    "tableau de bord pour un verrouillage automatique."
                ),
                inline=False,
            )
            embed.add_field(
                name="Permissions requises",
                value="Gérer le serveur, rôle admin configuré dans `/setup`, ou propriétaire.",
                inline=False,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

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

    async def _enable_raid_mode(self, interaction, auto_reason: str | None = None):
        """Active le mode raid — scan spam puis verrouillage des salons."""
        guild_id = interaction.guild.id
        auto_mode = auto_reason is not None

        if self.raid_active.get(guild_id, False):
            if not auto_mode and hasattr(interaction.response, "send_message"):
                await interaction.response.send_message("⚠️ Le mode raid est déjà actif !", ephemeral=True)
            return

        if not auto_mode and hasattr(interaction, "response") and hasattr(interaction.response, "defer"):
            await interaction.response.defer()

        progress_message = None
        try:
            if not auto_mode:
                if hasattr(interaction, "followup") and hasattr(interaction.followup, "send"):
                    progress_message = await interaction.followup.send("🔍 Analyse du spam en cours...")
                else:
                    progress_message = await interaction.send("🔍 Analyse du spam en cours...")

            reset_tracking(guild_id)
            self.raid_active[guild_id] = True

            if not auto_mode and progress_message:
                for label, seconds in [("Phase 1", 3), ("Phase 2", 3)]:
                    for i in range(seconds, 0, -1):
                        await progress_message.edit(content=f"🔍 {label} : scan anti-spam ({i}s)")
                        await asyncio.sleep(1)

            all_detected_spammers = get_spammer_ids(guild_id)
            total_unique_spammers = len(all_detected_spammers)

            if all_detected_spammers:
                audit_logger = self.bot.get_cog('AuditLogger')
                if audit_logger:
                    try:
                        await audit_logger.log_spam_detection(
                            interaction.guild, all_detected_spammers, total_unique_spammers * 3
                        )
                    except Exception as e:
                        logging.error("Erreur alerte spam: %s", e)

            if progress_message:
                await progress_message.edit(
                    content=f"✅ Scan terminé — {total_unique_spammers} menace(s) détectée(s). Verrouillage..."
                )

            member_role = self.get_member_role(interaction.guild)
            if not member_role:
                self.raid_active[guild_id] = False
                self.save_raid_state(guild_id)
                if not auto_mode:
                    await interaction.followup.send(
                        "❌ Rôle membre non configuré. Utilise `/setup`.", ephemeral=True
                    )
                return

            self.channel_states[guild_id] = {}
            self.invite_states[guild_id] = {}
            log_channel_id = guild_settings.get_log_channel(guild_id)
            announcement_channel_id = guild_settings.get_announcement_channel(guild_id)

            locked = 0
            for channel in interaction.guild.text_channels:
                if channel.id in (log_channel_id, announcement_channel_id):
                    continue
                try:
                    current_perms = channel.overwrites_for(member_role)
                    self.channel_states[guild_id][channel.id] = {
                        'role_id': member_role.id,
                        'send_messages': current_perms.send_messages,
                        'send_messages_in_threads': current_perms.send_messages_in_threads,
                        'create_public_threads': current_perms.create_public_threads,
                        'create_private_threads': current_perms.create_private_threads,
                        'add_reactions': current_perms.add_reactions,
                    }
                    new_perms = discord.PermissionOverwrite()
                    new_perms.send_messages = False
                    new_perms.send_messages_in_threads = False
                    new_perms.create_public_threads = False
                    new_perms.create_private_threads = False
                    new_perms.add_reactions = False
                    await channel.set_permissions(member_role, overwrite=new_perms)
                    locked += 1
                except discord.Forbidden:
                    logging.warning("Pas la permission sur le salon %s", channel.name)
                except Exception as e:
                    logging.error("Erreur verrouillage %s: %s", channel.name, e)

            self.invite_states[guild_id] = {'invites_paused': False}
            if interaction.guild.me.guild_permissions.manage_guild:
                try:
                    await interaction.guild.edit(
                        invites_disabled=True,
                        reason="Mode raid activé",
                    )
                    self.invite_states[guild_id]['invites_paused'] = True
                except Exception as e:
                    logging.error("Erreur pause invitations: %s", e)

            self.save_raid_state(guild_id)
            actor = interaction.user
            log_raid_event(interaction.guild, actor, "enabled")
            self.start_spam_cleanup(interaction.guild)

            title = "🚨 MODE RAID ACTIVÉ 🚨"
            if auto_reason:
                title = "🚨 MODE RAID AUTO-ACTIVÉ 🚨"
            description = (
                f"**{locked}** salon(s) verrouillé(s) pour {member_role.mention}. "
                "Les invitations sont suspendues."
            )
            if auto_reason:
                description = f"{description}\n\n**Déclencheur :** {auto_reason}"

            embed = discord.Embed(title=title, description=description, color=discord.Color.red())
            embed.add_field(name="Activé par", value=actor.mention, inline=False)
            embed.add_field(name="Désactiver", value="Utilise `/raid off` quand la menace est passée.", inline=False)

            if progress_message:
                await progress_message.delete()
            if not auto_mode:
                await interaction.followup.send(embed=embed)

            await self._notify_raid_channels(
                interaction.guild, guild_id, embed, all_detected_spammers, auto_mode
            )

        except Exception as e:
            self.raid_active[guild_id] = False
            self.save_raid_state(guild_id)
            if not auto_mode:
                await interaction.followup.send(f"⚠️ Erreur activation mode raid : {e}")
            logging.error("Erreur mode raid guild %s: %s", interaction.guild.name, e)

    async def _notify_raid_channels(self, guild, guild_id, embed, spammer_ids, auto_mode):
        """Envoie les notifications dans les salons log et annonces."""
        log_channel_id = guild_settings.get_log_channel(guild_id)
        if log_channel_id:
            log_channel = guild.get_channel(log_channel_id)
            if log_channel:
                try:
                    await log_channel.send(embed=embed)
                    if spammer_ids and not auto_mode:
                        await self.ask_spam_cleanup(guild, spammer_ids)
                except Exception as e:
                    logging.error("Erreur notification log raid: %s", e)

        announcement_channel_id = guild_settings.get_announcement_channel(guild_id)
        if announcement_channel_id:
            announcement_channel = guild.get_channel(announcement_channel_id)
            if announcement_channel:
                try:
                    ann = discord.Embed(
                        title="🚨 MODE RAID ACTIVÉ",
                        description=(
                            "Les salons sont verrouillés en raison d'une attaque. "
                            "Merci de patienter pendant que l'équipe modère."
                        ),
                        color=discord.Color.red(),
                    )
                    await announcement_channel.send(embed=ann)
                except Exception as e:
                    logging.error("Erreur annonce raid: %s", e)

    def get_member_role(self, guild):
        """Get the configured member role for the guild."""
        member_role_id = guild_settings.get_member_role(guild.id)
        if member_role_id:
            return guild.get_role(member_role_id)
        return None

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
                    if not channel:
                        continue

                    role_id = permissions.get('role_id')
                    role = interaction.guild.get_role(role_id) if role_id else self.get_member_role(interaction.guild)
                    if not role:
                        continue

                    current_perms = channel.overwrites_for(role)
                    new_perms = discord.PermissionOverwrite(**current_perms._values)
                    for key in (
                        'send_messages',
                        'send_messages_in_threads',
                        'create_public_threads',
                        'create_private_threads',
                        'add_reactions',
                    ):
                        if key in permissions:
                            setattr(new_perms, key, permissions[key])
                    await channel.set_permissions(role, overwrite=new_perms)

                    processed_channels += 1
                    if total_channels and (processed_channels % 5 == 0 or processed_channels == total_channels):
                        progress_percentage = int((processed_channels / total_channels) * 100)
                        await progress_message.edit(
                            content=f"🔓 Désactivation du mode raid... ({progress_percentage}%)"
                        )

                except discord.Forbidden:
                    logging.warning("Pas la permission sur le salon %s", channel_id)
                except Exception as e:
                    logging.error("Erreur déverrouillage salon %s: %s", channel_id, e)

            if interaction.guild.me.guild_permissions.manage_guild:
                try:
                    await interaction.guild.edit(
                        invites_disabled=False,
                        reason="Mode raid désactivé",
                    )
                except Exception as e:
                    logging.error("Erreur réactivation invitations: %s", e)

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
                title="✅ MODE RAID DÉSACTIVÉ",
                description="Les permissions des salons ont été restaurées.",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Désactivé par",
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
        """Affiche le statut du mode raid."""
        guild_id = interaction.guild.id
        is_active = self.raid_active.get(guild_id, False)
        member_role = self.get_member_role(interaction.guild)

        if is_active:
            embed = discord.Embed(
                title="🚨 Statut du mode raid",
                description=(
                    "**Mode raid ACTIF**\n"
                    "Les salons sont verrouillés pour le rôle membre. "
                    "Les invitations sont suspendues."
                ),
                color=discord.Color.red(),
            )
            spammer_ids = get_spammer_ids(guild_id)
            if spammer_ids:
                spammer_info = ""
                for user_id in list(spammer_ids)[:10]:
                    user = interaction.guild.get_member(user_id)
                    user_name = user.name if user else f"Inconnu ({user_id})"
                    spammer_info += f"• **{user_name}**\n"
                if len(spammer_ids) > 10:
                    spammer_info += f"• … et {len(spammer_ids) - 10} autres"
                embed.add_field(
                    name=f"Spammeurs détectés ({len(spammer_ids)})",
                    value=spammer_info,
                    inline=False,
                )
        else:
            embed = discord.Embed(
                title="✅ Statut du mode raid",
                description="**Mode raid INACTIF** — fonctionnement normal.",
                color=discord.Color.green(),
            )

        config_lines = []
        log_channel_id = guild_settings.get_log_channel(guild_id)
        announcement_channel_id = guild_settings.get_announcement_channel(guild_id)
        admin_role_id = guild_settings.get_admin_role(guild_id)

        if log_channel_id:
            ch = interaction.guild.get_channel(log_channel_id)
            config_lines.append(f"📝 Logs : {ch.mention if ch else 'salon supprimé'}")
        else:
            config_lines.append("📝 Logs : non configuré")

        if announcement_channel_id:
            ch = interaction.guild.get_channel(announcement_channel_id)
            config_lines.append(f"📢 Annonces : {ch.mention if ch else 'salon supprimé'}")
        else:
            config_lines.append("📢 Annonces : non configuré")

        if admin_role_id:
            role = interaction.guild.get_role(admin_role_id)
            config_lines.append(f"👑 Admin : {role.mention if role else 'rôle supprimé'}")
        else:
            config_lines.append("👑 Admin : non configuré")

        if member_role:
            config_lines.append(f"👥 Membre : {member_role.mention}")
        else:
            config_lines.append("👥 Membre : **non configuré** (requis pour `/raid on`)")

        auto_raid = guild_settings.get_setting(guild_id, "auto_raid_enabled", False)
        config_lines.append(f"🤖 Auto-raid : {'activé' if auto_raid else 'désactivé'}")
        config_lines.append(
            f"⚙️ Système : {'activé' if self._raid_system_enabled(guild_id) else 'désactivé'}"
        )

        embed.add_field(name="Configuration", value="\n".join(config_lines), inline=False)
        if not member_role or not log_channel_id:
            embed.add_field(
                name="Action requise",
                value="Lance `/setup` pour configurer le serveur avant d'utiliser le mode raid.",
                inline=False,
            )

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
                            await cleanup_spam(guild, log_channel, delete_messages=bool(spammer_ids))

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