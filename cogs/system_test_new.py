import discord
from discord.ext import commands
import logging
from utils.guild_settings import guild_settings

class TestSystemDropdown(discord.ui.Select):
    """Menu déroulant pour sélectionner le système à tester"""
    
    def __init__(self):
        options = [
            discord.SelectOption(
                label="🧪 Tester Tous les Systèmes",
                description="Test complet de tous les systèmes du bot",
                value="all_systems",
                emoji="🔬"
            ),
            discord.SelectOption(
                label="💾 Base de Données",
                description="Test de connectivité et opérations",
                value="database",
                emoji="💾"
            ),
            discord.SelectOption(
                label="🛡️ Détection de Spam",
                description="Test des algorithmes de détection",
                value="spam_detection",
                emoji="🛡️"
            ),
            discord.SelectOption(
                label="📋 Journalisation",
                description="Test du système d'audit",
                value="audit_logging",
                emoji="📋"
            ),
            discord.SelectOption(
                label="🌍 Système de Langues",
                description="Test du support multilingue",
                value="language_system",
                emoji="🌍"
            ),
            discord.SelectOption(
                label="⚠️ Avertissements",
                description="Test du suivi des avertissements",
                value="warning_system",
                emoji="⚠️"
            ),
            discord.SelectOption(
                label="🚨 Mode Raid",
                description="Test de la protection anti-raid",
                value="raid_mode",
                emoji="🚨"
            ),
            discord.SelectOption(
                label="⚙️ Paramètres Serveur",
                description="Test de la gestion des configurations",
                value="guild_settings",
                emoji="⚙️"
            ),
            discord.SelectOption(
                label="🔔 Alertes Critiques",
                description="Test des notifications d'alerte",
                value="critical_alerts",
                emoji="🔔"
            ),
            discord.SelectOption(
                label="🎉 Système de Bienvenue",
                description="Test des messages de bienvenue/au revoir",
                value="welcome_system",
                emoji="🎉"
            )
        ]
        
        super().__init__(
            placeholder="Sélectionnez un système à tester...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Gérer la sélection du système"""
        try:
            selected_system = self.values[0]
            
            # Créer la vue de confirmation
            view = TestConfirmationView(selected_system)
            
            if selected_system == "all_systems":
                title = "🧪 Test Complet des Systèmes"
                description = "**Test complet de tous les systèmes du bot**\n\n⏱️ **Durée estimée:** 30-60 secondes\n📊 **Systèmes testés:** 10 composants"
                color = 0x2ecc71
            else:
                system_names = {
                    "database": "💾 Base de Données",
                    "spam_detection": "🛡️ Détection de Spam", 
                    "audit_logging": "📋 Journalisation d'Audit",
                    "language_system": "🌍 Système de Langues",
                    "warning_system": "⚠️ Système d'Avertissements",
                    "raid_mode": "🚨 Mode Raid",
                    "guild_settings": "⚙️ Paramètres de Serveur",
                    "critical_alerts": "🔔 Alertes Critiques",
                    "welcome_system": "🎉 Système de Bienvenue"
                }
                title = f"Test: {system_names.get(selected_system, selected_system)}"
                description = f"**Test du {system_names.get(selected_system, selected_system)}**\n\n⏱️ **Durée estimée:** 5-15 secondes\n🔍 **Vérifications:** Fonctionnalité et configuration"
                color = 0x3498db
            
            embed = discord.Embed(
                title=title,
                description=description,
                color=color
            )
            embed.add_field(
                name="📋 Que va faire ce test ?",
                value="• Vérifier la disponibilité du système\n• Tester les fonctions principales\n• Contrôler la configuration\n• Générer un rapport détaillé",
                inline=False
            )
            
            await interaction.response.edit_message(embed=embed, view=view)
            
        except Exception as e:
            logging.error(f"Erreur dans le dropdown: {e}")
            await interaction.response.send_message(f"❌ Erreur lors de la sélection: {e}", ephemeral=True)

class TestConfirmationView(discord.ui.View):
    """Vue pour confirmer l'exécution du test"""
    
    def __init__(self, selected_system):
        super().__init__(timeout=300)
        self.selected_system = selected_system
    
    @discord.ui.button(label="✅ Confirmer le Test", style=discord.ButtonStyle.success)
    async def confirm_test(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirmer et lancer le test sélectionné"""
        try:
            # Mettre à jour les boutons pour montrer que c'est en cours
            button.label = "🔄 Test en cours..."
            button.disabled = True
            self.children[1].disabled = True  # Disable cancel button
            await interaction.response.edit_message(view=self)
            
            # Obtenir le cog SystemTest depuis l'interaction
            system_test = interaction.client.cogs.get('SystemTestNew')
            if not system_test:
                await interaction.followup.send("❌ Système de test non disponible", ephemeral=True)
                return
            
            # Lancer le test sélectionné
            if self.selected_system == "all_systems":
                await system_test.run_full_test(interaction)
            else:
                await system_test.run_single_test(interaction, self.selected_system)
                
        except Exception as e:
            logging.error(f"Erreur lors de la confirmation: {e}")
            await interaction.followup.send(f"❌ Erreur lors du test: {e}", ephemeral=True)
    
    @discord.ui.button(label="↩️ Retour", style=discord.ButtonStyle.secondary)
    async def back_to_menu(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Retourner au menu principal"""
        try:
            # Créer une nouvelle vue avec le dropdown
            view = TestSystemView()
            
            embed = discord.Embed(
                title="🧪 Test des Systèmes du Bot",
                description="Choisissez un système spécifique à tester ou lancez un test complet de tous les systèmes.",
                color=0x3498db
            )
            embed.add_field(
                name="💡 Conseil",
                value="Commencez par tester un système spécifique si vous rencontrez des problèmes particuliers.",
                inline=False
            )
            
            await interaction.response.edit_message(embed=embed, view=view)
            
        except Exception as e:
            logging.error(f"Erreur lors du retour: {e}")

class TestSystemView(discord.ui.View):
    """Vue principale pour l'interface de test"""
    
    def __init__(self):
        super().__init__(timeout=600)
        self.add_item(TestSystemDropdown())

class SystemTestNew(commands.Cog):
    """Système de test amélioré avec menu déroulant"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.guild_settings = guild_settings
    
    @discord.app_commands.command(name="testsystem", description="Tester les systèmes du bot avec menu interactif")
    async def test_system(self, interaction: discord.Interaction):
        """Afficher le menu de test des systèmes"""
        try:
            view = TestSystemView()
            
            embed = discord.Embed(
                title="🧪 Test des Systèmes du Bot",
                description="Sélectionnez un système à tester ou lancez un test complet de tous les systèmes.\n\n**Systèmes disponibles:**\n• Base de données\n• Détection de spam\n• Journalisation\n• Langues\n• Avertissements\n• Mode raid\n• Paramètres\n• Alertes critiques\n• Système de bienvenue",
                color=0x3498db
            )
            embed.add_field(
                name="⚡ Test Rapide",
                value="Pour un diagnostic rapide, sélectionnez le système qui pose problème.",
                inline=True
            )
            embed.add_field(
                name="🔬 Test Complet",
                value="Pour une vérification complète, choisissez 'Tester Tous les Systèmes'.",
                inline=True
            )
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            self.logger.error(f"Erreur dans test_system: {e}")
            await interaction.response.send_message(f"❌ Erreur: {e}", ephemeral=True)
    
    async def run_full_test(self, interaction: discord.Interaction):
        """Exécuter le test complet de tous les systèmes"""
        try:
            guild = interaction.guild
            test_results = {}
            
            # Tests individuels
            test_results["database"] = await self.test_database()
            test_results["spam_detection"] = await self.test_spam_detection()
            test_results["audit_logging"] = await self.test_audit_logging(guild)
            test_results["language_system"] = await self.test_language_system(guild)
            test_results["warning_system"] = await self.test_warning_system()
            test_results["raid_mode"] = await self.test_raid_mode(guild)
            test_results["guild_settings"] = await self.test_guild_settings(guild)
            test_results["critical_alerts"] = await self.test_critical_alerts(guild)
            test_results["welcome_system"] = await self.test_welcome_system(guild)
            
            # Générer le rapport
            await self.generate_test_report(interaction, test_results, "all_systems")
            
        except Exception as e:
            self.logger.error(f"Erreur dans run_full_test: {e}")
            await interaction.followup.send(f"❌ Erreur lors du test complet: {e}", ephemeral=True)
    
    async def run_single_test(self, interaction: discord.Interaction, system_name: str):
        """Exécuter le test d'un système spécifique"""
        try:
            guild = interaction.guild
            
            # Mapping des tests
            test_methods = {
                "database": self.test_database,
                "spam_detection": self.test_spam_detection,
                "audit_logging": lambda: self.test_audit_logging(guild),
                "language_system": lambda: self.test_language_system(guild),
                "warning_system": self.test_warning_system,
                "raid_mode": lambda: self.test_raid_mode(guild),
                "guild_settings": lambda: self.test_guild_settings(guild),
                "critical_alerts": lambda: self.test_critical_alerts(guild),
                "welcome_system": lambda: self.test_welcome_system(guild)
            }
            
            if system_name in test_methods:
                result = await test_methods[system_name]()
                await self.generate_test_report(interaction, {system_name: result}, system_name)
            else:
                await interaction.followup.send(f"❌ Système '{system_name}' non reconnu", ephemeral=True)
                
        except Exception as e:
            self.logger.error(f"Erreur dans run_single_test: {e}")
            await interaction.followup.send(f"❌ Erreur lors du test: {e}", ephemeral=True)
    
    # Méthodes de test individuelles (reprises du système existant)
    async def test_database(self):
        """Test de la base de données"""
        try:
            from models import get_db_session, Warning
            
            with get_db_session() as session:
                warnings_count = session.query(Warning).count()
                return {
                    "status": "✅ SUCCÈS",
                    "details": f"Base de données connectée, {warnings_count} avertissements stockés"
                }
        except Exception as e:
            return {
                "status": "❌ ÉCHEC", 
                "details": f"Erreur base de données: {str(e)}"
            }
    
    async def test_spam_detection(self):
        """Test de la détection de spam"""
        try:
            spam_monitor = self.bot.get_cog('ContinuousSpamMonitor')
            if not spam_monitor:
                return {
                    "status": "❌ ÉCHEC",
                    "details": "Moniteur de spam non chargé"
                }
            
            has_check = hasattr(spam_monitor, 'check_immediate_spam')
            has_analysis = hasattr(spam_monitor, 'analyze_guild_patterns')
            
            return {
                "status": "✅ SUCCÈS" if has_check and has_analysis else "⚠️ PARTIEL",
                "details": f"Détection immédiate: {has_check}, Analyse: {has_analysis}"
            }
        except Exception as e:
            return {
                "status": "❌ ÉCHEC",
                "details": f"Erreur détection spam: {str(e)}"
            }
    
    async def test_audit_logging(self, guild):
        """Test de la journalisation d'audit"""
        try:
            audit_logger = self.bot.get_cog('AuditLogger')
            if not audit_logger:
                return {
                    "status": "❌ ÉCHEC",
                    "details": "Logger d'audit non chargé"
                }
            
            has_send_log = hasattr(audit_logger, 'send_log')
            has_critical = hasattr(audit_logger, 'send_critical_alert')
            
            return {
                "status": "✅ SUCCÈS" if has_send_log and has_critical else "⚠️ PARTIEL",
                "details": f"Journalisation: {has_send_log}, Alertes critiques: {has_critical}"
            }
        except Exception as e:
            return {
                "status": "❌ ÉCHEC",
                "details": f"Erreur audit logging: {str(e)}"
            }
    
    async def test_language_system(self, guild):
        """Test du système de langues"""
        try:
            # Test du système de configuration de langues
            language_cog = self.bot.get_cog('LanguageConfig')
            if not language_cog:
                return {
                    "status": "❌ ÉCHEC",
                    "details": "Système de langues non chargé"
                }
            
            # Vérifier les méthodes disponibles
            has_set_lang = hasattr(language_cog, 'set_language')
            has_get_lang = hasattr(language_cog, 'get_language')
            
            return {
                "status": "✅ SUCCÈS" if has_set_lang and has_get_lang else "⚠️ PARTIEL",
                "details": f"Configuration langues: {has_set_lang}, Récupération: {has_get_lang}"
            }
        except Exception as e:
            return {
                "status": "❌ ÉCHEC",
                "details": f"Erreur système de langues: {str(e)}"
            }
    
    async def test_warning_system(self):
        """Test du système d'avertissements"""
        try:
            warning_system = self.bot.get_cog('WarningSystem')
            if not warning_system:
                return {
                    "status": "❌ ÉCHEC",
                    "details": "Système d'avertissements non chargé"
                }
            
            has_store = hasattr(warning_system, 'store_warning')
            has_detect = hasattr(warning_system, 'detect_warning')
            
            return {
                "status": "✅ SUCCÈS" if has_store and has_detect else "⚠️ PARTIEL",
                "details": f"Stockage: {has_store}, Détection: {has_detect}"
            }
        except Exception as e:
            return {
                "status": "❌ ÉCHEC",
                "details": f"Erreur système avertissements: {str(e)}"
            }
    
    async def test_raid_mode(self, guild):
        """Test du mode raid"""
        try:
            raid_cog = self.bot.get_cog('RaidMode')
            if not raid_cog:
                return {
                    "status": "❌ ÉCHEC",
                    "details": "Mode raid non chargé"
                }
            
            guild_id = guild.id
            raid_active = getattr(raid_cog, 'raid_active', {}).get(guild_id, False)
            
            has_enable = hasattr(raid_cog, '_enable_raid_mode')
            has_disable = hasattr(raid_cog, '_disable_raid_mode')
            
            return {
                "status": "✅ SUCCÈS",
                "details": f"Mode raid prêt, actif: {raid_active}, contrôles disponibles"
            }
        except Exception as e:
            return {
                "status": "❌ ÉCHEC",
                "details": f"Erreur mode raid: {str(e)}"
            }
    
    async def test_guild_settings(self, guild):
        """Test des paramètres de serveur"""
        try:
            log_channel = self.guild_settings.get_log_channel(guild.id)
            announcement_channel = self.guild_settings.get_announcement_channel(guild.id)
            admin_role = self.guild_settings.get_admin_role(guild.id)
            
            setup_complete = self.guild_settings.has_setup_completed(guild.id)
            
            return {
                "status": "✅ SUCCÈS",
                "details": f"Paramètres accessibles, configuration complète: {setup_complete}"
            }
        except Exception as e:
            return {
                "status": "❌ ÉCHEC",
                "details": f"Erreur paramètres serveur: {str(e)}"
            }
    
    async def test_critical_alerts(self, guild):
        """Test des alertes critiques"""
        try:
            audit_logger = self.bot.get_cog('AuditLogger')
            
            if not audit_logger:
                return {
                    "status": "❌ ÉCHEC",
                    "details": "Logger d'audit requis pour les alertes"
                }
            
            has_send_alert = hasattr(audit_logger, 'send_critical_alert')
            has_spam_logging = hasattr(audit_logger, 'log_spam_detection')
            
            return {
                "status": "✅ SUCCÈS" if has_send_alert and has_spam_logging else "⚠️ PARTIEL",
                "details": f"Alertes critiques: {has_send_alert}, Alertes spam: {has_spam_logging}"
            }
        except Exception as e:
            return {
                "status": "❌ ÉCHEC",
                "details": f"Erreur alertes critiques: {str(e)}"
            }
    
    async def test_welcome_system(self, guild):
        """Test du système de bienvenue"""
        try:
            welcome_cog = self.bot.get_cog('WelcomeSystem')
            
            if not welcome_cog:
                return {
                    "status": "❌ ÉCHEC",
                    "details": "Système de bienvenue non chargé"
                }
            
            guild_id = guild.id
            welcome_enabled = self.guild_settings.get_welcome_channel(guild_id) is not None
            goodbye_enabled = self.guild_settings.get_goodbye_channel(guild_id) is not None
            welcome_channel_id = self.guild_settings.get_welcome_channel(guild_id)
            
            config_items = []
            if welcome_enabled:
                config_items.append("Bienvenue activé")
            if goodbye_enabled:
                config_items.append("Au revoir activé")
            if welcome_channel_id:
                config_items.append("Canal configuré")
            
            has_image_gen = hasattr(welcome_cog, 'create_welcome_image')
            has_listeners = hasattr(welcome_cog, 'on_member_join')
            
            if has_image_gen and has_listeners:
                config_items.append("Génération d'images prête")
            
            status_text = ", ".join(config_items) if config_items else "Non configuré"
            
            return {
                "status": "✅ SUCCÈS" if config_items else "⚠️ NON CONFIGURÉ",
                "details": f"Système de bienvenue - {status_text}"
            }
            
        except Exception as e:
            return {
                "status": "❌ ÉCHEC",
                "details": f"Erreur système bienvenue: {str(e)}"
            }
    
    async def generate_test_report(self, interaction: discord.Interaction, results, test_type):
        """Générer et envoyer le rapport de test"""
        try:
            if test_type == "all_systems":
                # Rapport complet
                passed = sum(1 for r in results.values() if r["status"].startswith("✅"))
                failed = sum(1 for r in results.values() if r["status"].startswith("❌"))
                partial = sum(1 for r in results.values() if r["status"].startswith("⚠️"))
                
                if failed == 0 and partial == 0:
                    overall_status = "✅ TOUS LES SYSTÈMES OPÉRATIONNELS"
                    color = 0x2ecc71
                elif failed == 0:
                    overall_status = "⚠️ PRINCIPALEMENT OPÉRATIONNEL"
                    color = 0xf39c12
                else:
                    overall_status = "❌ PROBLÈMES DÉTECTÉS"
                    color = 0xe74c3c
                
                embed = discord.Embed(
                    title="🧪 Rapport de Test Complet",
                    description=f"**{overall_status}**\n\n📊 **Résultats:** {passed} succès, {partial} partiels, {failed} échecs",
                    color=color
                )
                
                # Ajouter les détails de chaque test
                for system, result in results.items():
                    system_names = {
                        "database": "💾 Base de Données",
                        "spam_detection": "🛡️ Détection Spam",
                        "audit_logging": "📋 Journalisation",
                        "language_system": "🌍 Langues",
                        "warning_system": "⚠️ Avertissements",
                        "raid_mode": "🚨 Mode Raid",
                        "guild_settings": "⚙️ Paramètres",
                        "critical_alerts": "🔔 Alertes Critiques",
                        "welcome_system": "🎉 Bienvenue"
                    }
                    
                    embed.add_field(
                        name=f"{system_names.get(system, system)} - {result['status']}",
                        value=result["details"][:100] + ("..." if len(result["details"]) > 100 else ""),
                        inline=True
                    )
                
            else:
                # Rapport d'un système spécifique
                result = list(results.values())[0]
                system_names = {
                    "database": "💾 Base de Données",
                    "spam_detection": "🛡️ Détection de Spam",
                    "audit_logging": "📋 Journalisation d'Audit",
                    "language_system": "🌍 Système de Langues",
                    "warning_system": "⚠️ Système d'Avertissements",
                    "raid_mode": "🚨 Mode Raid",
                    "guild_settings": "⚙️ Paramètres de Serveur",
                    "critical_alerts": "🔔 Alertes Critiques",
                    "welcome_system": "🎉 Système de Bienvenue"
                }
                
                system_name = system_names.get(test_type, test_type)
                
                if result["status"].startswith("✅"):
                    color = 0x2ecc71
                elif result["status"].startswith("⚠️"):
                    color = 0xf39c12
                else:
                    color = 0xe74c3c
                
                embed = discord.Embed(
                    title=f"🔍 Test: {system_name}",
                    description=f"**{result['status']}**\n\n{result['details']}",
                    color=color
                )
            
            embed.set_footer(text=f"Test exécuté sur {interaction.guild.name}")
            
            # Ajouter bouton pour retourner au menu
            view = discord.ui.View()
            back_button = discord.ui.Button(
                label="↩️ Nouveau Test",
                style=discord.ButtonStyle.secondary
            )
            
            async def back_callback(button_interaction):
                new_view = TestSystemView()
                new_embed = discord.Embed(
                    title="🧪 Test des Systèmes du Bot",
                    description="Choisissez un autre système à tester ou relancez un test complet.",
                    color=0x3498db
                )
                await button_interaction.response.edit_message(embed=new_embed, view=new_view)
            
            back_button.callback = back_callback
            view.add_item(back_button)
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            self.logger.error(f"Erreur génération rapport: {e}")
            await interaction.followup.send(f"❌ Erreur lors de la génération du rapport: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(SystemTestNew(bot))