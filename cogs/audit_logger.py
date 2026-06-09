import discord
from discord.ext import commands
import logging
from datetime import datetime, timezone
from utils.guild_settings import guild_settings
from utils.translations import get_text, create_embed
import asyncio

class AuditLogger(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild_settings = guild_settings

    async def send_log(self, guild, embed, critical=False, alert_reason=None):
        """Send log message to the configured log channel"""
        # Reload guild settings to ensure we have the latest configuration
        self.guild_settings.reload_guild_settings(guild.id)
        log_channel_id = self.guild_settings.get_log_channel(guild.id)
        if log_channel_id:
            log_channel = guild.get_channel(log_channel_id)
            if log_channel:
                try:
                    await log_channel.send(embed=embed)
                    
                    # Send critical alert to staff if needed
                    if critical and alert_reason:
                        await self.send_critical_alert(guild, log_channel, alert_reason)
                        
                except discord.Forbidden:
                    logging.warning(f"No permission to send to log channel in guild {guild.id}")
                except Exception as e:
                    logging.error(f"Error sending audit log: {e}")

    async def send_critical_alert(self, guild, log_channel, reason, user=None):
        """Send critical alert notification to staff"""
        admin_role_id = self.guild_settings.get_admin_role(guild.id)
        alert_content = ""
        
        if admin_role_id:
            admin_role = guild.get_role(admin_role_id)
            if admin_role:
                alert_content = f"{admin_role.mention} "
        
        alert_embed = discord.Embed(
            title="🚨 CRITICAL SERVER ALERT",
            description=f"**Immediate admin attention required**\n\n{reason}",
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )
        
        if user:
            alert_embed.add_field(name="Action by", value=f"{user.mention} ({user.id})", inline=True)
            
        alert_embed.add_field(
            name="Required Action",
            value="Please review the above change immediately and take appropriate action if necessary.",
            inline=False
        )
        alert_embed.set_footer(text="This alert was triggered by critical server activity detection")
        
        try:
            await log_channel.send(content=alert_content, embed=alert_embed)
        except Exception as e:
            logging.error(f"Error sending critical alert: {e}")
    
    def is_admin_action(self, guild, user):
        """Check if the user performing the action is an admin and should be excluded from alerts"""
        if not user:
            return False
            
        # Check if user has administrator permission
        if user.guild_permissions.administrator:
            return True
            
        # Check if user has manage server permission
        if user.guild_permissions.manage_guild:
            return True
            
        # Check if user has the configured admin role
        admin_role_id = self.guild_settings.get_admin_role(guild.id)
        if admin_role_id:
            admin_role = guild.get_role(admin_role_id)
            if admin_role and admin_role in user.roles:
                return True
                
        # Check if user is the server owner
        if user == guild.owner:
            return True
            
        return False

    def is_critical_channel_change(self, before, after):
        """Determine if channel change is critical"""
        # Critical if permissions changed significantly
        if hasattr(before, 'overwrites') and hasattr(after, 'overwrites'):
            before_perms = before.overwrites
            after_perms = after.overwrites
            
            # Check if @everyone permissions changed
            everyone_role = before.guild.default_role
            before_everyone = before_perms.get(everyone_role, discord.PermissionOverwrite())
            after_everyone = after_perms.get(everyone_role, discord.PermissionOverwrite())
            
            # Critical permission changes
            critical_perms = ['send_messages', 'view_channel', 'manage_messages', 'administrator']
            for perm in critical_perms:
                before_val = getattr(before_everyone, perm, None)
                after_val = getattr(after_everyone, perm, None)
                if before_val != after_val:
                    return True
        
        return False

    def is_critical_role_change(self, before, after):
        """Determine if role change is critical"""
        # Critical if dangerous permissions were added
        dangerous_perms = [
            'administrator', 'manage_guild', 'manage_channels', 
            'manage_roles', 'ban_members', 'kick_members'
        ]
        
        before_perms = before.permissions
        after_perms = after.permissions
        
        for perm in dangerous_perms:
            if not getattr(before_perms, perm) and getattr(after_perms, perm):
                return True
        
        return False

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        """Log when messages are deleted with full content"""
        if message.author.bot or not message.guild:
            return

        # Get who deleted the message from audit logs
        deleted_by = None
        try:
            async for entry in message.guild.audit_logs(action=discord.AuditLogAction.message_delete, limit=3):
                if (datetime.now(timezone.utc) - entry.created_at).total_seconds() < 5:
                    deleted_by = entry.user
                    break
        except:
            pass

        embed = discord.Embed(
            title="🗑️ Message Supprimé",
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="👤 Auteur", value=f"{message.author.mention} ({message.author.display_name})", inline=True)
        embed.add_field(name="📍 Salon", value=message.channel.mention, inline=True)
        embed.add_field(name="🕐 Envoyé le", value=discord.utils.format_dt(message.created_at, "F"), inline=True)
        
        if deleted_by:
            embed.add_field(name="🔨 Supprimé par", value=f"{deleted_by.mention} ({deleted_by.display_name})", inline=True)
        else:
            embed.add_field(name="🔨 Supprimé par", value="Auteur du message ou inconnu", inline=True)
            
        embed.add_field(name="🆔 ID Message", value=f"`{message.id}`", inline=True)
        
        # Show full message content
        if message.content:
            # Split long messages into multiple fields if needed
            content = message.content
            if len(content) > 1024:
                # Split into chunks of 1000 characters
                chunks = [content[i:i+1000] for i in range(0, len(content), 1000)]
                for i, chunk in enumerate(chunks):
                    field_name = f"📝 Contenu du Message (Partie {i+1}/{len(chunks)})"
                    embed.add_field(name=field_name, value=f"```{chunk}```", inline=False)
            else:
                embed.add_field(name="📝 Contenu du Message", value=f"```{content}```", inline=False)
        else:
            embed.add_field(name="📝 Contenu", value="*Message vide ou média uniquement*", inline=False)
        
        # Show attachments with details
        if message.attachments:
            attachment_info = []
            for att in message.attachments:
                size_mb = round(att.size / (1024 * 1024), 2)
                attachment_info.append(f"**{att.filename}** ({size_mb} MB)")
            embed.add_field(name="📎 Fichiers Joints", value='\n'.join(attachment_info), inline=False)
        
        # Show embeds if any
        if message.embeds:
            embed.add_field(name="🎨 Embeds", value=f"{len(message.embeds)} embed(s) dans le message", inline=False)
        
        # Show reactions if any
        if message.reactions:
            reactions = []
            for reaction in message.reactions:
                reactions.append(f"{reaction.emoji} ({reaction.count})")
            embed.add_field(name="😀 Réactions", value=' • '.join(reactions), inline=False)

        embed.set_thumbnail(url=message.author.display_avatar.url)
        embed.set_footer(text=f"Audit • {message.guild.name} • ID Auteur: {message.author.id}")

        await self.send_log(message.guild, embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        """Log when messages are edited with full before/after content"""
        if before.author.bot or not before.guild or before.content == after.content:
            return

        embed = discord.Embed(
            title="✏️ Message Modifié",
            color=discord.Color.orange(),
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="👤 Auteur", value=f"{before.author.mention} ({before.author.display_name})", inline=True)
        embed.add_field(name="📍 Salon", value=before.channel.mention, inline=True)
        embed.add_field(name="🕐 Modifié le", value=discord.utils.format_dt(after.edited_at or datetime.now(timezone.utc), "F"), inline=True)
        embed.add_field(name="🆔 ID Message", value=f"`{before.id}`", inline=True)
        embed.add_field(name="🔗 Lien", value=f"[Aller au message]({after.jump_url})", inline=True)
        
        # Show full before content
        if before.content:
            if len(before.content) > 1000:
                chunks = [before.content[i:i+1000] for i in range(0, len(before.content), 1000)]
                for i, chunk in enumerate(chunks):
                    field_name = f"📝 Contenu AVANT (Partie {i+1}/{len(chunks)})"
                    embed.add_field(name=field_name, value=f"```{chunk}```", inline=False)
            else:
                embed.add_field(name="📝 Contenu AVANT", value=f"```{before.content}```", inline=False)
        else:
            embed.add_field(name="📝 Contenu AVANT", value="*Message vide*", inline=False)
            
        # Show full after content
        if after.content:
            if len(after.content) > 1000:
                chunks = [after.content[i:i+1000] for i in range(0, len(after.content), 1000)]
                for i, chunk in enumerate(chunks):
                    field_name = f"📝 Contenu APRÈS (Partie {i+1}/{len(chunks)})"
                    embed.add_field(name=field_name, value=f"```{chunk}```", inline=False)
            else:
                embed.add_field(name="📝 Contenu APRÈS", value=f"```{after.content}```", inline=False)
        else:
            embed.add_field(name="📝 Contenu APRÈS", value="*Message vide*", inline=False)
        
        # Show attachment changes if any
        if before.attachments != after.attachments:
            before_files = [att.filename for att in before.attachments]
            after_files = [att.filename for att in after.attachments]
            embed.add_field(name="📎 Fichiers AVANT", value=', '.join(before_files) if before_files else "*Aucun*", inline=True)
            embed.add_field(name="📎 Fichiers APRÈS", value=', '.join(after_files) if after_files else "*Aucun*", inline=True)

        embed.set_thumbnail(url=before.author.display_avatar.url)
        embed.set_footer(text=f"Audit • {before.guild.name} • ID Auteur: {before.author.id}")

        await self.send_log(before.guild, embed)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        """Log when channels are created"""
        embed = discord.Embed(
            title="📝 Channel Created",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="Channel", value=f"{channel.mention} ({channel.name})", inline=True)
        embed.add_field(name="Type", value=str(channel.type).title(), inline=True)
        embed.add_field(name="ID", value=str(channel.id), inline=True)
        
        if hasattr(channel, 'category') and channel.category:
            embed.add_field(name="Category", value=channel.category.name, inline=True)

        await self.send_log(channel.guild, embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """Log when channels are deleted"""
        embed = discord.Embed(
            title="🗑️ Channel Deleted",
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="Channel", value=f"#{channel.name}", inline=True)
        embed.add_field(name="Type", value=str(channel.type).title(), inline=True)
        embed.add_field(name="ID", value=str(channel.id), inline=True)
        
        if hasattr(channel, 'category') and channel.category:
            embed.add_field(name="Category", value=channel.category.name, inline=True)

        await self.send_log(channel.guild, embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        """Log when channels are updated"""
        changes = []
        critical = False
        alert_reason = None
        
        if before.name != after.name:
            changes.append(f"**Name:** `{before.name}` → `{after.name}`")
        
        if hasattr(before, 'topic') and before.topic != after.topic:
            before_topic = before.topic or "None"
            after_topic = after.topic or "None"
            changes.append(f"**Topic:** `{before_topic}` → `{after_topic}`")
        
        if hasattr(before, 'category') and before.category != after.category:
            before_cat = before.category.name if before.category else "None"
            after_cat = after.category.name if after.category else "None"
            changes.append(f"**Category:** `{before_cat}` → `{after_cat}`")
        
        if hasattr(before, 'slowmode_delay') and before.slowmode_delay != after.slowmode_delay:
            changes.append(f"**Slowmode:** `{before.slowmode_delay}s` → `{after.slowmode_delay}s`")

        # Check for critical permission changes, but only alert if not done by admin
        if self.is_critical_channel_change(before, after):
            # Try to get the user who made the change from audit logs
            try:
                async for entry in after.guild.audit_logs(action=discord.AuditLogAction.channel_update, limit=1):
                    if entry.target.id == after.id:
                        if not self.is_admin_action(after.guild, entry.user):
                            critical = True
                            alert_reason = f"Critical permissions changed in {after.mention} by non-admin user {entry.user.mention}. This could affect server security or member access. Please verify these changes were intentional and authorized."
                            changes.append("⚠️ **CRITICAL: Security-sensitive permissions modified by non-admin**")
                        else:
                            changes.append("ℹ️ **Security permissions modified by admin** (No alert needed)")
                        break
            except:
                # If we can't get audit logs, be conservative and alert
                critical = True
                alert_reason = f"Critical permissions changed in {after.mention}. Unable to verify if change was made by admin. Please verify these changes were intentional and authorized."
                changes.append("⚠️ **CRITICAL: Security-sensitive permissions modified** (Unable to verify admin status)")

        if not changes:
            return

        embed = discord.Embed(
            title="⚠️ CRITICAL Channel Updated" if critical else "✏️ Channel Updated",
            color=discord.Color.red() if critical else discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="Channel", value=after.mention, inline=True)
        embed.add_field(name="Type", value=str(after.type).title(), inline=True)
        embed.add_field(name="Changes", value="\n".join(changes), inline=False)

        await self.send_log(after.guild, embed, critical=critical, alert_reason=alert_reason)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        """Log when roles are created"""
        embed = discord.Embed(
            title="🎭 Role Created",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="Role", value=f"{role.mention} ({role.name})", inline=True)
        embed.add_field(name="ID", value=str(role.id), inline=True)
        embed.add_field(name="Color", value=str(role.color), inline=True)
        embed.add_field(name="Mentionable", value=str(role.mentionable), inline=True)
        embed.add_field(name="Hoisted", value=str(role.hoist), inline=True)

        await self.send_log(role.guild, embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        """Log when roles are deleted"""
        embed = discord.Embed(
            title="🗑️ Role Deleted",
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="Role", value=role.name, inline=True)
        embed.add_field(name="ID", value=str(role.id), inline=True)
        embed.add_field(name="Color", value=str(role.color), inline=True)

        await self.send_log(role.guild, embed)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        """Log when roles are updated"""
        changes = []
        critical = False
        alert_reason = None
        
        if before.name != after.name:
            changes.append(f"**Name:** `{before.name}` → `{after.name}`")
        
        if before.color != after.color:
            changes.append(f"**Color:** `{before.color}` → `{after.color}`")
        
        if before.hoist != after.hoist:
            changes.append(f"**Hoisted:** `{before.hoist}` → `{after.hoist}`")
        
        if before.mentionable != after.mentionable:
            changes.append(f"**Mentionable:** `{before.mentionable}` → `{after.mentionable}`")
        
        if before.permissions != after.permissions:
            changes.append("**Permissions:** Updated")
            
            # Check for critical permission changes, but only alert if not done by admin
            if self.is_critical_role_change(before, after):
                dangerous_perms = []
                dangerous_names = {
                    'administrator': 'Administrator',
                    'manage_guild': 'Manage Server',
                    'manage_channels': 'Manage Channels',
                    'manage_roles': 'Manage Roles',
                    'ban_members': 'Ban Members',
                    'kick_members': 'Kick Members'
                }
                
                for perm, name in dangerous_names.items():
                    if not getattr(before.permissions, perm) and getattr(after.permissions, perm):
                        dangerous_perms.append(name)
                
                # Try to get the user who made the change from audit logs
                try:
                    async for entry in after.guild.audit_logs(action=discord.AuditLogAction.role_update, limit=1):
                        if entry.target.id == after.id:
                            if not self.is_admin_action(after.guild, entry.user):
                                critical = True
                                alert_reason = f"DANGEROUS PERMISSIONS GRANTED to role {after.mention} by non-admin user {entry.user.mention}:\n• {', '.join(dangerous_perms)}\n\nThis role can now perform critical server management actions. Verify this change was authorized and review who has this role."
                                changes.append(f"⚠️ **CRITICAL: Dangerous permissions added by non-admin** ({', '.join(dangerous_perms)})")
                            else:
                                changes.append(f"ℹ️ **Dangerous permissions added by admin** ({', '.join(dangerous_perms)}) (No alert needed)")
                            break
                except:
                    # If we can't get audit logs, be conservative and alert
                    critical = True
                    alert_reason = f"DANGEROUS PERMISSIONS GRANTED to role {after.mention}:\n• {', '.join(dangerous_perms)}\n\nUnable to verify if change was made by admin. This role can now perform critical server management actions. Verify this change was authorized and review who has this role."
                    changes.append(f"⚠️ **CRITICAL: Dangerous permissions added** ({', '.join(dangerous_perms)}) (Unable to verify admin status)")

        if not changes:
            return

        embed = discord.Embed(
            title="🚨 CRITICAL Role Updated" if critical else "✏️ Role Updated",
            color=discord.Color.red() if critical else discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="Role", value=after.mention, inline=True)
        embed.add_field(name="ID", value=str(after.id), inline=True)
        embed.add_field(name="Changes", value="\n".join(changes), inline=False)

        await self.send_log(after.guild, embed, critical=critical, alert_reason=alert_reason)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Log when members join with detailed information"""
        embed = discord.Embed(
            title="📥 Membre Rejoint",
            description=f"**{member.mention}** a rejoint le serveur",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="👤 Utilisateur", value=f"{member.mention} ({member.display_name})", inline=True)
        embed.add_field(name="🆔 ID", value=f"`{member.id}`", inline=True)
        embed.add_field(name="👥 Membres Total", value=f"**{member.guild.member_count}** membres", inline=True)
        
        # Account age information
        account_age = datetime.now(timezone.utc) - member.created_at
        if account_age.days < 7:
            age_text = f"⚠️ **{account_age.days} jours** (Compte récent)"
            embed.color = discord.Color.orange()
        elif account_age.days < 30:
            age_text = f"🆕 **{account_age.days} jours**"
        else:
            age_text = f"✅ **{account_age.days} jours**"
            
        embed.add_field(name="📅 Compte créé", value=discord.utils.format_dt(member.created_at, "F"), inline=True)
        embed.add_field(name="⏰ Âge du compte", value=age_text, inline=True)
        embed.add_field(name="🕐 Rejoint le", value=discord.utils.format_dt(member.joined_at or datetime.now(timezone.utc), "F"), inline=True)
        
        # Check if user has default avatar
        if member.avatar is None:
            embed.add_field(name="🖼️ Avatar", value="Avatar par défaut Discord", inline=True)
        else:
            embed.add_field(name="🖼️ Avatar", value="Avatar personnalisé", inline=True)
            
        # Bot status
        embed.add_field(name="🤖 Type", value="Bot" if member.bot else "Utilisateur", inline=True)
        
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Audit • {member.guild.name}")

        await self.send_log(member.guild, embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Log when members leave with detailed information"""
        # Check if user was kicked or banned
        kick_info = None
        ban_info = None
        
        try:
            # Check for kicks in audit log
            async for entry in member.guild.audit_logs(action=discord.AuditLogAction.kick, limit=3):
                if entry.target.id == member.id and (datetime.now(timezone.utc) - entry.created_at).total_seconds() < 10:
                    kick_info = entry
                    break
                    
            # Check for bans in audit log  
            async for entry in member.guild.audit_logs(action=discord.AuditLogAction.ban, limit=3):
                if entry.target.id == member.id and (datetime.now(timezone.utc) - entry.created_at).total_seconds() < 10:
                    ban_info = entry
                    break
        except:
            pass
        
        # Determine leave type and color
        if ban_info:
            title = "🔨 Membre Banni"
            color = discord.Color.dark_red()
            action_type = f"Banni par {ban_info.user.mention}"
            reason = ban_info.reason or "Aucune raison spécifiée"
        elif kick_info:
            title = "👢 Membre Expulsé" 
            color = discord.Color.red()
            action_type = f"Expulsé par {kick_info.user.mention}"
            reason = kick_info.reason or "Aucune raison spécifiée"
        else:
            title = "📤 Membre Parti"
            color = discord.Color.orange()
            action_type = "A quitté le serveur"
            reason = "Départ volontaire"
            
        embed = discord.Embed(
            title=title,
            description=f"**{member.mention}** a quitté le serveur",
            color=color,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="👤 Utilisateur", value=f"{member.mention} ({member.display_name})", inline=True)
        embed.add_field(name="🆔 ID", value=f"`{member.id}`", inline=True)
        embed.add_field(name="👥 Membres Total", value=f"**{member.guild.member_count}** membres", inline=True)
        
        embed.add_field(name="🚪 Type de départ", value=action_type, inline=True)
        
        if member.joined_at:
            time_on_server = datetime.now(timezone.utc) - member.joined_at
            if time_on_server.days > 0:
                duration = f"{time_on_server.days} jours"
            elif time_on_server.seconds > 3600:
                duration = f"{time_on_server.seconds // 3600} heures"
            else:
                duration = f"{time_on_server.seconds // 60} minutes"
            embed.add_field(name="⏱️ Temps sur le serveur", value=duration, inline=True)
            embed.add_field(name="🕐 Avait rejoint le", value=discord.utils.format_dt(member.joined_at, "F"), inline=True)
        
        if reason != "Départ volontaire":
            embed.add_field(name="📋 Raison", value=reason, inline=False)
            
        # Show user's roles at time of leaving
        if member.roles and len(member.roles) > 1:  # Exclude @everyone
            roles = [role.mention for role in member.roles[1:]]  # Skip @everyone
            if len(roles) <= 10:
                embed.add_field(name="🎭 Rôles", value=', '.join(roles), inline=False)
            else:
                embed.add_field(name="🎭 Rôles", value=f"{', '.join(roles[:10])} et {len(roles)-10} autres...", inline=False)
        
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Audit • {member.guild.name}")

        await self.send_log(member.guild, embed)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Log when member details are updated"""
        changes = []
        critical = False
        alert_reason = None
        
        if before.nick != after.nick:
            before_nick = before.nick or "None"
            after_nick = after.nick or "None"
            changes.append(f"**Nickname:** `{before_nick}` → `{after_nick}`")
        
        # Check role changes
        before_roles = set(before.roles)
        after_roles = set(after.roles)
        
        added_roles = after_roles - before_roles
        removed_roles = before_roles - after_roles
        
        if added_roles:
            roles_added = ", ".join([role.name for role in added_roles])
            changes.append(f"**Roles Added:** {roles_added}")
            
            # Check if dangerous roles were added
            dangerous_roles = []
            for role in added_roles:
                if any(getattr(role.permissions, perm, False) for perm in ['administrator', 'manage_guild', 'manage_channels', 'manage_roles', 'ban_members']):
                    dangerous_roles.append(role.name)
            
            if dangerous_roles:
                # Try to get the user who made the change from audit logs
                try:
                    async for entry in after.guild.audit_logs(action=discord.AuditLogAction.member_role_update, limit=1):
                        if entry.target.id == after.id:
                            if not self.is_admin_action(after.guild, entry.user):
                                critical = True
                                alert_reason = f"CRITICAL ROLE ASSIGNMENT: User {after.mention} was given powerful roles by non-admin user {entry.user.mention}: {', '.join(dangerous_roles)}. These roles have dangerous permissions that could compromise server security. Verify this assignment was authorized."
                                changes.append(f"⚠️ **CRITICAL: Powerful roles assigned by non-admin** ({', '.join(dangerous_roles)})")
                            else:
                                changes.append(f"ℹ️ **Powerful roles assigned by admin** ({', '.join(dangerous_roles)}) (No alert needed)")
                            break
                except:
                    # If we can't get audit logs, be conservative and alert
                    critical = True
                    alert_reason = f"CRITICAL ROLE ASSIGNMENT: User {after.mention} was given powerful roles: {', '.join(dangerous_roles)}. Unable to verify if assignment was made by admin. These roles have dangerous permissions that could compromise server security. Verify this assignment was authorized."
                    changes.append(f"⚠️ **CRITICAL: Powerful roles assigned** ({', '.join(dangerous_roles)}) (Unable to verify admin status)")
        
        if removed_roles:
            roles_removed = ", ".join([role.name for role in removed_roles])
            changes.append(f"**Roles Removed:** {roles_removed}")

        if not changes:
            return

        embed = discord.Embed(
            title="🚨 CRITICAL Member Updated" if critical else "✏️ Member Updated",
            color=discord.Color.red() if critical else discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="Member", value=f"{after} ({after.id})", inline=True)
        embed.add_field(name="Changes", value="\n".join(changes), inline=False)
        
        embed.set_thumbnail(url=after.display_avatar.url)

        await self.send_log(after.guild, embed, critical=critical, alert_reason=alert_reason)

    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        """Log when guild settings are updated"""
        changes = []
        
        if before.name != after.name:
            changes.append(f"**Name:** `{before.name}` → `{after.name}`")
        
        if before.description != after.description:
            before_desc = before.description or "None"
            after_desc = after.description or "None"
            changes.append(f"**Description:** `{before_desc}` → `{after_desc}`")
        
        if before.verification_level != after.verification_level:
            changes.append(f"**Verification Level:** `{before.verification_level}` → `{after.verification_level}`")
        
        if before.default_notifications != after.default_notifications:
            changes.append(f"**Default Notifications:** `{before.default_notifications}` → `{after.default_notifications}`")
        
        if before.explicit_content_filter != after.explicit_content_filter:
            changes.append(f"**Content Filter:** `{before.explicit_content_filter}` → `{after.explicit_content_filter}`")

        if not changes:
            return

        embed = discord.Embed(
            title="🏰 Server Updated",
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="Server", value=after.name, inline=True)
        embed.add_field(name="Changes", value="\n".join(changes), inline=False)

        await self.send_log(after, embed)

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        """Log when invites are created"""
        embed = discord.Embed(
            title="🔗 Invite Created",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="Code", value=invite.code, inline=True)
        embed.add_field(name="Channel", value=invite.channel.mention, inline=True)
        embed.add_field(name="Inviter", value=f"{invite.inviter} ({invite.inviter.id})" if invite.inviter else "Unknown", inline=True)
        embed.add_field(name="Max Uses", value=str(invite.max_uses) if invite.max_uses else "Unlimited", inline=True)
        embed.add_field(name="Expires", value=discord.utils.format_dt(invite.expires_at, "R") if invite.expires_at else "Never", inline=True)

        await self.send_log(invite.guild, embed)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        """Log when invites are deleted"""
        embed = discord.Embed(
            title="🗑️ Invite Deleted",
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="Code", value=invite.code, inline=True)
        embed.add_field(name="Channel", value=invite.channel.mention if invite.channel else "Unknown", inline=True)
        embed.add_field(name="Uses", value=str(invite.uses), inline=True)

        await self.send_log(invite.guild, embed)

    async def log_spam_detection(self, guild, spammer_ids, messages_detected):
        """Log spam detection with critical staff alert"""
        embed = discord.Embed(
            title="🚨 SPAM ATTACK DETECTED",
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="Threat Level", value="HIGH - Immediate Action Required", inline=False)
        embed.add_field(name="Spammers Detected", value=str(len(spammer_ids)), inline=True)
        embed.add_field(name="Messages Analyzed", value=str(messages_detected), inline=True)
        
        spammer_list = []
        for user_id in list(spammer_ids)[:5]:  # Limit to first 5 spammers
            user = guild.get_member(user_id)
            if user:
                spammer_list.append(f"• {user.mention} ({user.id})")
            else:
                spammer_list.append(f"• Unknown User ({user_id})")
        
        if len(spammer_ids) > 5:
            spammer_list.append(f"• ... and {len(spammer_ids) - 5} more")
        
        embed.add_field(
            name="Detected Spammers", 
            value="\n".join(spammer_list) if spammer_list else "None identified", 
            inline=False
        )
        
        embed.add_field(
            name="Recommended Actions",
            value="• Enable raid mode if not already active\n• Review and ban confirmed spammers\n• Monitor for additional attacks\n• Check recent joins for suspicious accounts",
            inline=False
        )
        
        alert_reason = f"SPAM ATTACK DETECTED: {len(spammer_ids)} potential spammers identified during raid mode scanning. This indicates a coordinated attack against your server. Immediate moderation action is recommended to prevent further damage."
        
        await self.send_log(guild, embed, critical=True, alert_reason=alert_reason)

async def setup(bot):
    await bot.add_cog(AuditLogger(bot))