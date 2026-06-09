import discord
from discord.ext import commands
from discord import app_commands
from utils.guild_settings import GuildSettings
from datetime import datetime, timezone
import asyncio

class SetupView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.guild_settings = GuildSettings()
        self.current_step = 0
        self.setup_data = {}
        
    async def start_setup(self, interaction):
        """Start the interactive setup process"""
        embed = discord.Embed(
            title="🛠️ Configuration du Bot",
            description="Je vais vous guider à travers la configuration complète du bot.\n"
                       "Vous pouvez annuler à tout moment en cliquant sur ❌",
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(
            name="📋 Éléments à configurer",
            value="• 📝 Salon de logs\n"
                  "• 📢 Salon d'annonces\n"
                  "• 👑 Rôle administrateur\n"
                  "• 👥 Rôle membre\n"
                  "• 👋 Salon de bienvenue\n"
                  "• 👋 Salon d'au revoir\n"
                  "• 🎨 Messages personnalisés",
            inline=False
        )
        
        embed.set_footer(text="Configuration interactive • Étape 1/7")
        
        await interaction.response.edit_message(embed=embed, view=self)
        await self.ask_log_channel(interaction)
    
    async def ask_log_channel(self, interaction):
        """Ask for log channel configuration"""
        embed = discord.Embed(
            title="📝 Configuration du Salon de Logs",
            description="Dans quel salon voulez-vous recevoir tous les logs d'audit ?\n"
                       "(Messages supprimés, modifications, membres qui rejoignent/quittent, etc.)",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="💡 Instructions",
            value="Tapez le nom du salon (ex: logs) ou mentionnez-le (#logs) ou tapez `skip` pour passer",
            inline=False
        )
        
        embed.set_footer(text="Configuration • Étape 1/7 • Salon de logs")
        
        await interaction.followup.edit_message(interaction.message.id, embed=embed, view=self)
        
        def check(message):
            return message.author == interaction.user and message.channel == interaction.channel
            
        try:
            msg = await interaction.client.wait_for('message', check=check, timeout=60.0)
            
            if msg.content.lower() == 'skip':
                self.setup_data['log_channel'] = None
            elif msg.channel_mentions:
                self.setup_data['log_channel'] = msg.channel_mentions[0]
            else:
                # Try to find channel by name
                channel_name = msg.content.strip().lower()
                found_channel = None
                for channel in interaction.guild.text_channels:
                    if channel.name.lower() == channel_name:
                        found_channel = channel
                        break
                if found_channel:
                    self.setup_data['log_channel'] = found_channel
                else:
                    await msg.reply("❌ Salon non trouvé. Tapez le nom exact du salon ou mentionnez-le, ou tapez `skip`")
                    return await self.ask_log_channel(interaction)
                
            await msg.delete()
            await self.ask_announcement_channel(interaction)
            
        except asyncio.TimeoutError:
            await self.timeout_response(interaction)
    
    async def ask_announcement_channel(self, interaction):
        """Ask for announcement channel configuration"""
        embed = discord.Embed(
            title="📢 Configuration du Salon d'Annonces",
            description="Dans quel salon voulez-vous recevoir les annonces importantes ?\n"
                       "(Alertes de sécurité, notifications de raid, etc.)",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="💡 Instructions", 
            value="Tapez le nom du salon (ex: annonces) ou mentionnez-le (#annonces) ou tapez `skip` pour passer",
            inline=False
        )
        
        embed.set_footer(text="Configuration • Étape 2/7 • Salon d'annonces")
        
        await interaction.followup.edit_message(interaction.message.id, embed=embed, view=self)
        
        def check(message):
            return message.author == interaction.user and message.channel == interaction.channel
            
        try:
            msg = await interaction.client.wait_for('message', check=check, timeout=60.0)
            
            if msg.content.lower() == 'skip':
                self.setup_data['announcement_channel'] = None
            elif msg.channel_mentions:
                self.setup_data['announcement_channel'] = msg.channel_mentions[0]
            else:
                # Try to find channel by name
                channel_name = msg.content.strip().lower()
                found_channel = None
                for channel in interaction.guild.text_channels:
                    if channel.name.lower() == channel_name:
                        found_channel = channel
                        break
                if found_channel:
                    self.setup_data['announcement_channel'] = found_channel
                else:
                    await msg.reply("❌ Salon non trouvé. Tapez le nom exact du salon ou mentionnez-le, ou tapez `skip`")
                    return await self.ask_announcement_channel(interaction)
                
            await msg.delete()
            await self.ask_admin_role(interaction)
            
        except asyncio.TimeoutError:
            await self.timeout_response(interaction)
    
    async def ask_admin_role(self, interaction):
        """Ask for admin role configuration"""
        embed = discord.Embed(
            title="👑 Configuration du Rôle Administrateur",
            description="Quel rôle doit avoir accès aux commandes d'administration ?\n"
                       "(Les membres avec ce rôle pourront utiliser toutes les commandes)",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="💡 Instructions",
            value="Tapez le nom du rôle (ex: Admin) ou mentionnez-le (@Admin) ou tapez `skip` pour passer",
            inline=False
        )
        
        embed.set_footer(text="Configuration • Étape 3/7 • Rôle administrateur")
        
        await interaction.followup.edit_message(interaction.message.id, embed=embed, view=self)
        
        def check(message):
            return message.author == interaction.user and message.channel == interaction.channel
            
        try:
            msg = await interaction.client.wait_for('message', check=check, timeout=60.0)
            
            if msg.content.lower() == 'skip':
                self.setup_data['admin_role'] = None
            elif msg.role_mentions:
                self.setup_data['admin_role'] = msg.role_mentions[0]
            else:
                # Try to find role by name
                role_name = msg.content.strip().lower()
                found_role = None
                for role in interaction.guild.roles:
                    if role.name.lower() == role_name:
                        found_role = role
                        break
                if found_role:
                    self.setup_data['admin_role'] = found_role
                else:
                    await msg.reply("❌ Rôle non trouvé. Tapez le nom exact du rôle ou mentionnez-le, ou tapez `skip`")
                    return await self.ask_admin_role(interaction)
                
            await msg.delete()
            await self.ask_member_role(interaction)
            
        except asyncio.TimeoutError:
            await self.timeout_response(interaction)

    async def ask_member_role(self, interaction):
        """Ask for member role configuration"""
        embed = discord.Embed(
            title="👥 Configuration du Rôle Membre",
            description="Quel rôle est donné aux membres vérifiés ?\n"
                       "(Utilisé pour le mode raid et la protection)",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="💡 Instructions",
            value="Tapez le nom du rôle (ex: Membre) ou mentionnez-le (@Membre) ou tapez `skip` pour passer",
            inline=False
        )
        
        embed.set_footer(text="Configuration • Étape 4/7 • Rôle membre")
        
        await interaction.followup.edit_message(interaction.message.id, embed=embed, view=self)
        
        def check(message):
            return message.author == interaction.user and message.channel == interaction.channel
            
        try:
            msg = await interaction.client.wait_for('message', check=check, timeout=60.0)
            
            if msg.content.lower() == 'skip':
                self.setup_data['member_role'] = None
            elif msg.role_mentions:
                self.setup_data['member_role'] = msg.role_mentions[0]
            else:
                # Try to find role by name
                role_name = msg.content.strip().lower()
                found_role = None
                for role in interaction.guild.roles:
                    if role.name.lower() == role_name:
                        found_role = role
                        break
                if found_role:
                    self.setup_data['member_role'] = found_role
                else:
                    await msg.reply("❌ Rôle non trouvé. Tapez le nom exact du rôle ou mentionnez-le, ou tapez `skip`")
                    return await self.ask_member_role(interaction)
                
            await msg.delete()
            await self.ask_welcome_channel(interaction)
            
        except asyncio.TimeoutError:
            await self.timeout_response(interaction)

    async def ask_welcome_channel(self, interaction):
        """Ask for welcome channel configuration"""
        embed = discord.Embed(
            title="👋 Configuration du Salon de Bienvenue",
            description="Dans quel salon voulez-vous envoyer les messages de bienvenue ?\n"
                       "(Messages avec images personnalisées quand quelqu'un rejoint)",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="💡 Instructions",
            value="Tapez le nom du salon (ex: bienvenue) ou mentionnez-le (#bienvenue) ou tapez `skip` pour passer",
            inline=False
        )
        
        embed.set_footer(text="Configuration • Étape 5/7 • Salon de bienvenue")
        
        await interaction.followup.edit_message(interaction.message.id, embed=embed, view=self)
        
        def check(message):
            return message.author == interaction.user and message.channel == interaction.channel
            
        try:
            msg = await interaction.client.wait_for('message', check=check, timeout=60.0)
            
            if msg.content.lower() == 'skip':
                self.setup_data['welcome_channel'] = None
            elif msg.channel_mentions:
                self.setup_data['welcome_channel'] = msg.channel_mentions[0]
            else:
                # Try to find channel by name
                channel_name = msg.content.strip().lower()
                found_channel = None
                for channel in interaction.guild.text_channels:
                    if channel.name.lower() == channel_name:
                        found_channel = channel
                        break
                if found_channel:
                    self.setup_data['welcome_channel'] = found_channel
                else:
                    await msg.reply("❌ Salon non trouvé. Tapez le nom exact du salon ou mentionnez-le, ou tapez `skip`")
                    return await self.ask_welcome_channel(interaction)
                
            await msg.delete()
            await self.ask_goodbye_channel(interaction)
            
        except asyncio.TimeoutError:
            await self.timeout_response(interaction)

    async def ask_goodbye_channel(self, interaction):
        """Ask for goodbye channel configuration"""
        embed = discord.Embed(
            title="👋 Configuration du Salon d'Au Revoir",
            description="Dans quel salon voulez-vous envoyer les messages d'au revoir ?\n"
                       "(Messages quand quelqu'un quitte le serveur)",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="💡 Instructions",
            value="Tapez le nom du salon (ex: aurevoir) ou mentionnez-le (#aurevoir) ou tapez `skip` pour passer",
            inline=False
        )
        
        embed.set_footer(text="Configuration • Étape 6/7 • Salon d'au revoir")
        
        await interaction.followup.edit_message(interaction.message.id, embed=embed, view=self)
        
        def check(message):
            return message.author == interaction.user and message.channel == interaction.channel
            
        try:
            msg = await interaction.client.wait_for('message', check=check, timeout=60.0)
            
            if msg.content.lower() == 'skip':
                self.setup_data['goodbye_channel'] = None
            elif msg.channel_mentions:
                self.setup_data['goodbye_channel'] = msg.channel_mentions[0]
            else:
                # Try to find channel by name
                channel_name = msg.content.strip().lower()
                found_channel = None
                for channel in interaction.guild.text_channels:
                    if channel.name.lower() == channel_name:
                        found_channel = channel
                        break
                if found_channel:
                    self.setup_data['goodbye_channel'] = found_channel
                else:
                    await msg.reply("❌ Salon non trouvé. Tapez le nom exact du salon ou mentionnez-le, ou tapez `skip`")
                    return await self.ask_goodbye_channel(interaction)
                
            await msg.delete()
            await self.finish_setup(interaction)
            
        except asyncio.TimeoutError:
            await self.timeout_response(interaction)

    async def finish_setup(self, interaction):
        """Complete the setup and save settings"""
        # Save all settings
        if self.setup_data.get('log_channel'):
            self.guild_settings.set_log_channel(self.guild_id, self.setup_data['log_channel'].id)
        if self.setup_data.get('announcement_channel'):
            self.guild_settings.set_announcement_channel(self.guild_id, self.setup_data['announcement_channel'].id)
        if self.setup_data.get('admin_role'):
            self.guild_settings.set_admin_role(self.guild_id, self.setup_data['admin_role'].id)
        if self.setup_data.get('member_role'):
            self.guild_settings.set_member_role(self.guild_id, self.setup_data['member_role'].id)
        if self.setup_data.get('welcome_channel'):
            self.guild_settings.set_welcome_channel(self.guild_id, self.setup_data['welcome_channel'].id)
            self.guild_settings.set_welcome_enabled(self.guild_id, True)
        if self.setup_data.get('goodbye_channel'):
            self.guild_settings.set_goodbye_channel(self.guild_id, self.setup_data['goodbye_channel'].id)
            self.guild_settings.set_goodbye_enabled(self.guild_id, True)

        # Create summary embed
        embed = discord.Embed(
            title="✅ Configuration Terminée !",
            description="Le bot a été configuré avec succès sur votre serveur.",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
        
        config_summary = []
        if self.setup_data.get('log_channel'):
            config_summary.append(f"📝 **Logs:** {self.setup_data['log_channel'].mention}")
        if self.setup_data.get('announcement_channel'):
            config_summary.append(f"📢 **Annonces:** {self.setup_data['announcement_channel'].mention}")
        if self.setup_data.get('admin_role'):
            config_summary.append(f"👑 **Admin:** {self.setup_data['admin_role'].mention}")
        if self.setup_data.get('member_role'):
            config_summary.append(f"👥 **Membre:** {self.setup_data['member_role'].mention}")
        if self.setup_data.get('welcome_channel'):
            config_summary.append(f"👋 **Bienvenue:** {self.setup_data['welcome_channel'].mention}")
        if self.setup_data.get('goodbye_channel'):
            config_summary.append(f"👋 **Au revoir:** {self.setup_data['goodbye_channel'].mention}")
            
        if config_summary:
            embed.add_field(name="📋 Configuration Actuelle", value='\n'.join(config_summary), inline=False)
        
        embed.add_field(
            name="🚀 Prochaines Étapes",
            value="• Utilisez `/help` pour voir toutes les commandes\n"
                  "• Configurez les messages de bienvenue dans le tableau de bord web\n"
                  "• Testez le système avec `/testsystem`\n"
                  "• Utilisez `/setup reset` pour réinitialiser la configuration",
            inline=False
        )
        
        embed.set_footer(text="Configuration terminée avec succès !")
        
        self.clear_items()
        await interaction.followup.edit_message(interaction.message.id, embed=embed, view=self)

    async def timeout_response(self, interaction):
        """Handle timeout"""
        embed = discord.Embed(
            title="⏰ Configuration Expirée",
            description="La configuration a expiré. Utilisez `/setup` pour recommencer.",
            color=discord.Color.red()
        )
        self.clear_items()
        await interaction.followup.edit_message(interaction.message.id, embed=embed, view=self)

    @discord.ui.button(label="❌ Annuler", style=discord.ButtonStyle.danger)
    async def cancel_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel the setup process"""
        embed = discord.Embed(
            title="❌ Configuration Annulée",
            description="La configuration a été annulée. Aucun changement n'a été effectué.",
            color=discord.Color.red()
        )
        self.clear_items()
        await interaction.response.edit_message(embed=embed, view=self)

class SetupSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild_settings = GuildSettings()

    @app_commands.command(name="setup", description="Configuration interactive complète du bot")
    async def setup_command(self, interaction: discord.Interaction):
        """Setup command with multiple options"""
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "❌ Vous devez avoir la permission 'Gérer le serveur' pour utiliser cette commande.",
                ephemeral=True
            )
            return

        await self.start_interactive_setup(interaction)

    async def start_interactive_setup(self, interaction):
        """Start the interactive setup process"""
        embed = discord.Embed(
            title="🛠️ Configuration Interactive du Bot",
            description="Bienvenue dans la configuration interactive !\n"
                       "Je vais vous guider étape par étape pour configurer toutes les fonctionnalités du bot.",
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(
            name="⚡ Fonctionnalités",
            value="• 📝 Logs d'audit complets\n"
                  "• 🛡️ Protection anti-raid\n"
                  "• 👋 Messages de bienvenue/au revoir\n"
                  "• ⚠️ Système d'avertissements\n"
                  "• 🔍 Détection de spam 24/7\n"
                  "• 🎯 Alertes de sécurité intelligentes",
            inline=True
        )
        
        embed.add_field(
            name="🎮 Actions Disponibles",
            value="• **Commencer** - Configuration interactive\n"
                  "• **Reset** - Réinitialiser la configuration\n"
                  "• **Voir** - Afficher la configuration actuelle",
            inline=True
        )
        
        embed.set_footer(text="Cliquez sur un bouton pour commencer")
        
        view = SetupControlView(interaction.guild.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def reset_configuration(self, interaction):
        """Reset all bot configuration"""
        # Create confirmation embed
        embed = discord.Embed(
            title="🔄 Réinitialisation de la Configuration",
            description="⚠️ **ATTENTION** ⚠️\n\n"
                       "Vous êtes sur le point de réinitialiser TOUTE la configuration du bot :\n"
                       "• Salons de logs et d'annonces\n"
                       "• Rôles administrateur et membre\n" 
                       "• Configuration de bienvenue/au revoir\n"
                       "• Paramètres de langue\n"
                       "• Toutes les préférences personnalisées",
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(
            name="❓ Êtes-vous sûr ?",
            value="Cette action est **irréversible** et effacera tous vos paramètres.",
            inline=False
        )
        
        view = ResetConfirmView(interaction.guild.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def view_configuration(self, interaction):
        """View current configuration"""
        guild_id = interaction.guild.id
        
        embed = discord.Embed(
            title="📋 Configuration Actuelle",
            description=f"Configuration du bot pour **{interaction.guild.name}**",
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )
        
        # Get current settings
        log_channel_id = self.guild_settings.get_log_channel(guild_id)
        announcement_channel_id = self.guild_settings.get_announcement_channel(guild_id)
        admin_role_id = self.guild_settings.get_admin_role(guild_id)
        member_role_id = self.guild_settings.get_member_role(guild_id)
        welcome_channel_id = self.guild_settings.get_welcome_channel(guild_id)
        goodbye_channel_id = self.guild_settings.get_goodbye_channel(guild_id)
        
        # Format settings display
        settings = []
        
        if log_channel_id:
            channel = interaction.guild.get_channel(log_channel_id)
            settings.append(f"📝 **Logs:** {channel.mention if channel else 'Salon supprimé'}")
        else:
            settings.append("📝 **Logs:** Non configuré")
            
        if announcement_channel_id:
            channel = interaction.guild.get_channel(announcement_channel_id)
            settings.append(f"📢 **Annonces:** {channel.mention if channel else 'Salon supprimé'}")
        else:
            settings.append("📢 **Annonces:** Non configuré")
            
        if admin_role_id:
            role = interaction.guild.get_role(admin_role_id)
            settings.append(f"👑 **Admin:** {role.mention if role else 'Rôle supprimé'}")
        else:
            settings.append("👑 **Admin:** Non configuré")
            
        if member_role_id:
            role = interaction.guild.get_role(member_role_id)
            settings.append(f"👥 **Membre:** {role.mention if role else 'Rôle supprimé'}")
        else:
            settings.append("👥 **Membre:** Non configuré")
            
        welcome_enabled = self.guild_settings.is_welcome_enabled(guild_id)
        if welcome_enabled and welcome_channel_id:
            channel = interaction.guild.get_channel(welcome_channel_id)
            settings.append(f"👋 **Bienvenue:** {channel.mention if channel else 'Salon supprimé'} ✅")
        else:
            settings.append("👋 **Bienvenue:** Désactivé")
            
        goodbye_enabled = self.guild_settings.is_goodbye_enabled(guild_id)
        if goodbye_enabled and goodbye_channel_id:
            channel = interaction.guild.get_channel(goodbye_channel_id)
            settings.append(f"👋 **Au revoir:** {channel.mention if channel else 'Salon supprimé'} ✅")
        else:
            settings.append("👋 **Au revoir:** Désactivé")
        
        embed.add_field(name="⚙️ Paramètres", value='\n'.join(settings), inline=False)
        
        # Check completion status
        configured_count = sum([
            bool(log_channel_id),
            bool(announcement_channel_id),
            bool(admin_role_id),
            bool(member_role_id),
            bool(welcome_enabled and welcome_channel_id),
            bool(goodbye_enabled and goodbye_channel_id)
        ])
        
        completion_percentage = (configured_count / 6) * 100
        
        if completion_percentage == 100:
            status = "🟢 Configuration complète"
            color = discord.Color.green()
        elif completion_percentage >= 50:
            status = f"🟡 Configuration partielle ({completion_percentage:.0f}%)"
            color = discord.Color.orange()
        else:
            status = f"🔴 Configuration incomplète ({completion_percentage:.0f}%)"
            color = discord.Color.red()
            
        embed.color = color
        embed.add_field(name="📊 État", value=status, inline=False)
        
        embed.set_footer(text="Utilisez /setup pour modifier la configuration")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class SetupControlView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=300)
        self.guild_id = guild_id

    @discord.ui.button(label="🛠️ Commencer la Configuration", style=discord.ButtonStyle.primary)
    async def start_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Start the interactive setup"""
        view = SetupView(self.guild_id)
        await view.start_setup(interaction)

    @discord.ui.button(label="🔄 Reset", style=discord.ButtonStyle.danger) 
    async def reset_config(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Reset configuration"""
        setup_cog = None
        for cog in interaction.client.cogs.values():
            if cog.__class__.__name__ == 'SetupSystem':
                setup_cog = cog
                break
        if setup_cog:
            await setup_cog.reset_configuration(interaction)

    @discord.ui.button(label="📋 Voir Config", style=discord.ButtonStyle.secondary)
    async def view_config(self, interaction: discord.Interaction, button: discord.ui.Button):
        """View current configuration"""
        setup_cog = None
        for cog in interaction.client.cogs.values():
            if cog.__class__.__name__ == 'SetupSystem':
                setup_cog = cog
                break
        if setup_cog:
            await setup_cog.view_configuration(interaction)

class ResetConfirmView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.guild_settings = GuildSettings()

    @discord.ui.button(label="✅ Confirmer Reset", style=discord.ButtonStyle.danger)
    async def confirm_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm and perform reset"""
        # Reset all settings
        self.guild_settings.reset_guild_settings(self.guild_id)
        
        embed = discord.Embed(
            title="✅ Configuration Réinitialisée",
            description="Toute la configuration du bot a été réinitialisée avec succès.\n"
                       "Utilisez `/setup` pour reconfigurer le bot.",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
        
        self.clear_items()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="❌ Annuler", style=discord.ButtonStyle.secondary)
    async def cancel_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel reset"""
        embed = discord.Embed(
            title="❌ Reset Annulé",
            description="La réinitialisation a été annulée. Aucun changement n'a été effectué.",
            color=discord.Color.blue()
        )
        
        self.clear_items()
        await interaction.response.edit_message(embed=embed, view=self)

async def setup(bot):
    await bot.add_cog(SetupSystem(bot))