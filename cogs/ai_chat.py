import discord
from discord.ext import commands
from discord import app_commands
import logging
import re
import os
import json
import asyncio
from datetime import datetime, timezone
from utils.guild_settings import guild_settings
from utils.translations import get_text
from utils.free_ai_system import FreeAISystem

class AIChatSystem(commands.Cog):
    """AI-powered chat system using GPT-4o"""
    
    def __init__(self, bot):
        self.bot = bot
        self.guild_settings = guild_settings
        
        # Initialize Free AI System
        self.free_ai = FreeAISystem()
        logging.info("Free AI system initialized successfully")
        
    @commands.Cog.listener()
    async def on_message(self, message):
        """Monitor messages for AI chat triggers"""
        # Skip bots and DMs
        if message.author.bot or not message.guild:
            return
            
        guild_id = message.guild.id
        
        # Check if AI chat is enabled for this guild
        ai_enabled = self.guild_settings.get_setting(guild_id, 'ai_chat_enabled', False)
        
        if not ai_enabled:
            return
            
        # Check if message should trigger AI response
        should_respond = await self.should_respond_to_message(message)
        
        if should_respond:
            try:
                # Generate AI response (with a typing indicator for better UX)
                async with message.channel.typing():
                    response = await self.generate_ai_response(message)
                
                if response:
                    # Send response
                    await message.channel.send(response)
                    logging.debug(f"AI responded in guild {guild_id}, channel {message.channel.id}")
                    
            except Exception as e:
                logging.error(f"Error in AI chat system: {e}")
                # Send error message in French/English
                error_msg = get_text(guild_id, "ai_error", 
                    "❌ Erreur lors de la génération de la réponse IA / AI response generation error")
                await message.channel.send(error_msg)
    
    async def should_respond_to_message(self, message):
        """Determine if the bot should respond to this message"""
        content = message.content.lower()
        bot_name = self.bot.user.name.lower()
        bot_mention = f"<@{self.bot.user.id}>"
        bot_mention_nick = f"<@!{self.bot.user.id}>"
        
        # Respond if:
        # 1. Bot is mentioned directly
        if bot_mention in message.content or bot_mention_nick in message.content:
            return True
            
        # 2. Bot name is mentioned (check various forms)
        name_variants = [bot_name, 'popocorp', 'popolcorp', 'popocorps', 'popo']
        for variant in name_variants:
            if variant in content:
                return True
            
        # 3. Message contains question words directed at bot specifically (must also mention bot or be very specific)
        bot_directed_questions = [
            f'{bot_name} qui es', f'{bot_name} comment', f'{bot_name} pourquoi',
            f'{bot_name} peux-tu', f'{bot_name} aide', f'{bot_name} help',
            'qui es-tu', 'comment tu', 'peux-tu aider', 'aide-moi',
            'what are you', 'can you help', 'help me'
        ]
        
        if any(phrase in content for phrase in bot_directed_questions):
            return True
            
        # 4. Direct reply to bot's message
        if message.reference and message.reference.message_id:
            try:
                referenced_message = await message.channel.fetch_message(message.reference.message_id)
                if referenced_message.author == self.bot.user:
                    return True
            except:
                pass
                
        return False
    
    async def generate_ai_response(self, message):
        """Generate AI response using Free AI System"""
        try:
            # Check if user is admin
            is_admin = message.author.guild_permissions.manage_guild or message.author.guild_permissions.administrator
            
            # Prepare guild info for context
            guild_info = {
                'name': message.guild.name,
                'member_count': message.guild.member_count,
                'id': message.guild.id
            }
            
            # Generate response using the AI system, off the event loop to avoid
            # blocking the bot during the (network) AI call
            loop = asyncio.get_event_loop()
            ai_response = await loop.run_in_executor(
                None, self.free_ai.generate_response, message, guild_info, is_admin
            )
            
            # Check for dangerous situations and alert staff if needed
            if self.free_ai.is_dangerous_situation(message.content):
                await self.alert_staff_dangerous_situation(message)
            
            return ai_response
            
        except Exception as e:
            logging.error(f"Free AI system error: {e}")
            return None
    
    async def check_for_dangerous_content(self, original_message, ai_response):
        """Check for dangerous content and alert staff if needed"""
        try:
            # Keywords indicating dangerous situations
            danger_keywords = [
                # Suicide/self-harm (French)
                'suicide', 'suicider', 'me tuer', 'tuer moi', 'mourir', 'mort', 'fin de vie',
                'automutilation', 'me faire mal', 'blesser moi', 'couper', 'saigner',
                'plus envie de vivre', 'envie de mourir', 'disparaître', 'en finir',
                
                # Suicide/self-harm (English)  
                'kill myself', 'suicide', 'end my life', 'want to die', 'self harm',
                'cut myself', 'hurt myself', 'don\'t want to live', 'end it all',
                
                # Violence/threats
                'tuer quelqu\'un', 'faire du mal', 'violence', 'attaque', 'blesser',
                'kill someone', 'hurt others', 'violence', 'attack', 'harm others',
                
                # Extreme distress
                'détresse', 'désespoir', 'aide moi', 'au secours', 'dépression grave',
                'distress', 'despair', 'help me', 'severe depression', 'crisis'
            ]
            
            # Check both original message and AI response for danger keywords
            content_to_check = f"{original_message.content.lower()} {ai_response.lower()}"
            
            dangerous_detected = False
            for keyword in danger_keywords:
                if keyword in content_to_check:
                    dangerous_detected = True
                    break
            
            # Also use OpenAI to analyze if content seems dangerous
            if not dangerous_detected:
                danger_analysis = await self.analyze_content_danger(original_message.content)
                if danger_analysis and danger_analysis.get('is_dangerous', False):
                    dangerous_detected = True
            
            if dangerous_detected:
                await self.alert_staff_dangerous_situation(original_message)
                
        except Exception as e:
            logging.error(f"Error checking dangerous content: {e}")
    
    async def analyze_content_danger(self, content):
        """Use OpenAI to analyze if content indicates a dangerous situation"""
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o", # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
                messages=[
                    {
                        "role": "system",
                        "content": "Tu es un système de détection de sécurité. Analyse si le message indique une situation dangereuse nécessitant une intervention (suicide, automutilation, violence, détresse grave). Réponds en JSON avec 'is_dangerous' (boolean) et 'reason' (string)."
                    },
                    {
                        "role": "user", 
                        "content": content
                    }
                ],
                response_format={"type": "json_object"},
                max_tokens=150
            )
            
            content = response.choices[0].message.content
            if content:
                result = json.loads(content)
                return result
            return None
            
        except Exception as e:
            logging.error(f"Error analyzing content danger: {e}")
            return None
    
    async def alert_staff_dangerous_situation(self, message):
        """Alert staff about a dangerous situation detected in AI chat"""
        try:
            guild = message.guild
            if not guild:
                return
            
            # Get audit logger to send critical alert
            audit_logger = self.bot.get_cog('AuditLogger')
            if not audit_logger:
                return
            
            # Create alert embed
            embed = discord.Embed(
                title="🚨 SITUATION CRITIQUE DÉTECTÉE",
                description="L'IA a détecté une conversation préoccupante nécessitant une attention immédiate du staff.",
                color=0xFF0000,
                timestamp=datetime.now(timezone.utc)
            )
            
            embed.add_field(
                name="👤 Utilisateur",
                value=f"{message.author.mention} (`{message.author.id}`)",
                inline=True
            )
            
            embed.add_field(
                name="📍 Canal",
                value=f"{message.channel.mention}",
                inline=True
            )
            
            embed.add_field(
                name="🕒 Heure",
                value=f"<t:{int(message.created_at.timestamp())}:F>",
                inline=True
            )
            
            # Truncate message content for safety while preserving context
            content_preview = message.content[:200] + "..." if len(message.content) > 200 else message.content
            embed.add_field(
                name="💬 Aperçu du message",
                value=f"```{content_preview}```",
                inline=False
            )
            
            embed.add_field(
                name="⚠️ Action requise",
                value="Un membre du staff doit vérifier cette conversation et apporter un soutien approprié si nécessaire.",
                inline=False
            )
            
            embed.add_field(
                name="📋 Ressources d'aide",
                value="• France: 3114 (numéro national de prévention du suicide)\n• Suicide Écoute: 01 45 39 40 00\n• SOS Amitié: 09 72 39 40 50",
                inline=False
            )
            
            # Send critical alert with staff mention
            await audit_logger.send_critical_alert(
                guild, 
                None,  # We'll handle the channel ourselves
                "Situation critique détectée dans une conversation IA",
                message.author
            )
            
            # Also send to log channel with embed
            await audit_logger.send_log(guild, embed, critical=True, alert_reason="AI_DANGEROUS_CONTENT")
            
            logging.warning(f"Critical situation detected in AI chat - Guild: {guild.id}, User: {message.author.id}, Channel: {message.channel.id}")
            
        except Exception as e:
            logging.error(f"Error alerting staff about dangerous situation: {e}")
    
    async def check_system_control_request(self, message):
        """Check if message contains system control request"""
        content = message.content.lower()
        
        # System control keywords
        control_patterns = {
            'spam_detection': ['désactiv.*spam', 'disable.*spam', 'arrêt.*spam', 'stop.*spam'],
            'audit_logs': ['désactiv.*audit', 'disable.*audit', 'arrêt.*log', 'stop.*log'],
            'welcome_system': ['désactiv.*bienvenue', 'disable.*welcome', 'arrêt.*accueil', 'stop.*welcome'],
            'ai_chat': ['désactiv.*ia', 'disable.*ai', 'arrêt.*chat', 'stop.*chat', 'tais.*toi'],
            'raid_mode': ['désactiv.*raid', 'disable.*raid', 'arrêt.*protection', 'stop.*raid']
        }
        
        for system, patterns in control_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content):
                    action = 'disable' if any(word in content for word in ['désactiv', 'disable', 'arrêt', 'stop', 'tais']) else 'enable'
                    return {'system': system, 'action': action}
        
        return None
    
    async def handle_system_control(self, message, action):
        """Handle system control requests from admins"""
        guild_id = message.guild.id
        system = action['system']
        action_type = action['action']
        
        try:
            # Map system names to settings
            setting_map = {
                'spam_detection': 'continuous_spam_enabled',
                'audit_logs': 'audit_logs_enabled', 
                'welcome_system': 'welcome_enabled',
                'ai_chat': 'ai_chat_enabled',
                'raid_mode': 'raid_mode_enabled'
            }
            
            setting_name = setting_map.get(system)
            if not setting_name:
                return "❌ Système non reconnu / System not recognized"
            
            # Apply the setting
            enabled = action_type == 'enable'
            self.guild_settings.set_setting(guild_id, setting_name, enabled)
            
            # Create response message
            system_names = {
                'spam_detection': 'Détection de Spam 24/7 / 24/7 Spam Detection',
                'audit_logs': 'Journaux d\'Audit / Audit Logs',
                'welcome_system': 'Système de Bienvenue / Welcome System',
                'ai_chat': 'Chat IA / AI Chat',
                'raid_mode': 'Mode Raid / Raid Mode'
            }
            
            status_fr = "activé" if enabled else "désactivé"
            status_en = "enabled" if enabled else "disabled"
            
            return f"✅ {system_names[system]} {status_fr} / {status_en} par {message.author.display_name}"
            
        except Exception as e:
            logging.error(f"Error controlling system {system}: {e}")
            return "❌ Erreur lors du contrôle du système / Error controlling system"
    
    def create_system_prompt(self, guild, is_admin=False):
        """Create system prompt for the AI"""
        guild_name = guild.name if guild else "Server"
        
        admin_prompt = ""
        if is_admin:
            admin_prompt = """
            
COMMANDES ADMIN SPÉCIALES:
- Tu peux contrôler les systèmes du bot si un admin le demande
- Réponds aux demandes comme "désactive le spam" ou "arrête l'audit"
- Confirme toujours les actions effectuées"""
        
        return f"""Tu es PopoCorps, un bot Discord de modération cool et protecteur pour le serveur "{guild_name}".

PERSONNALITÉ CONSTANTE:
- Amical et décontracté, comme un pote vigilant
- Protecteur mais avec de l'humour
- Tu peux être vulgaire de manière affectueuse si l'utilisateur l'est aussi
- Humble mais confiant dans tes capacités
- Empathique et à l'écoute
- Réponds en français par défaut, en anglais si l'utilisateur écrit en anglais

TRAITS CARACTÉRISTIQUES:
- Tu utilises parfois des émojis amicaux (🛡️, 🤖, ⚡, 🎯)
- Tu te présentes comme "votre gardien numérique"
- Tu dis souvent "Je veille sur cette communauté"
- Tu encourages l'entraide et la bienveillance

RÈGLES POUR LA VULGARITÉ:
- Si l'utilisateur utilise des insultes affectueuses (genre "putain c'est ouf" ou "bordel de merde"), tu peux répondre dans le même registre
- Utilise des mots comme "putain", "bordel", "merde" de manière naturelle et amicale
- JAMAIS d'insultes directes envers une personne (pas de "connard", "salope", etc.)
- Reste toujours bienveillant même en étant vulgaire
- Si c'est de l'affection brute entre potes, joue le jeu

DÉTECTION DE SITUATIONS CRITIQUES:
- Si tu détectes des mentions de suicide, automutilation, violence, harcèlement grave ou détresse psychologique
- ALERTE IMMÉDIATEMENT: Réponds avec empathie ET signale au staff
- Phrases d'alerte: "Je préviens l'équipe de modération", "Les responsables vont t'aider"
- Encourage à chercher de l'aide professionnelle

Tes capacités:
- Modération avancée avec IA
- Détection de spam et raids 24/7  
- Système d'audit complet
- Messages de bienvenue personnalisés
- Dashboard web de configuration

Instructions:
- Garde tes réponses courtes mais chaleureuses (max 2-3 phrases)
- Sois toujours bienveillant et protecteur
- Si on te demande des commandes, mentionne /help avec un émoji
- Encourage la communauté positive
- ALERTE le staff pour toute situation préoccupante{admin_prompt}"""

    async def build_conversation_context(self, message):
        """Build conversation context from recent messages"""
        channel_id = message.channel.id
        context_parts = []
        
        # Add recent conversation memory
        if channel_id in self.CONVERSATION_MEMORY:
            for interaction in self.CONVERSATION_MEMORY[channel_id][-3:]:  # Last 3 interactions
                context_parts.append(f"{interaction['user']}: {interaction['content']}")
                context_parts.append(f"PopoCorps: {interaction['response']}")
        
        # Add current channel context
        context_parts.append(f"Current channel: #{message.channel.name}")
        context_parts.append(f"User: {message.author.display_name}")
        
        return "\n".join(context_parts)
    
    @app_commands.command(name="ai", description="Toggle AI chat system / Activer/désactiver le système de chat IA")
    @app_commands.describe(enabled="Enable or disable AI chat / Activer ou désactiver le chat IA")
    async def toggle_ai_chat(self, interaction: discord.Interaction, enabled: bool):
        """Toggle AI chat system for the server"""
        # Check permissions
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "❌ Vous devez avoir la permission 'Gérer le serveur' / You need 'Manage Server' permission",
                ephemeral=True
            )
            return
            
        await interaction.response.defer()
        
        guild_id = interaction.guild.id
        self.guild_settings.set_setting(guild_id, 'ai_chat_enabled', enabled)
        
        status = "activé" if enabled else "désactivé"
        status_en = "enabled" if enabled else "disabled"
        
        embed = discord.Embed(
            title="🤖 Système de Chat IA / AI Chat System",
            description=f"Le chat IA a été **{status}** / AI chat has been **{status_en}**",
            color=discord.Color.green() if enabled else discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )
        
        if enabled:
            embed.add_field(
                name="ℹ️ Comment ça marche / How it works",
                value="Le bot répondra quand:\n"
                      "• Il est mentionné (@PopoCorps)\n"
                      "• Son nom est dit dans un message\n"
                      "• On répond à un de ses messages\n"
                      "• Des questions courtes sont posées\n\n"
                      "The bot will respond when:\n"
                      "• It's mentioned (@PopoCorps)\n"
                      "• Its name is said in a message\n"
                      "• Someone replies to its messages\n"
                      "• Short questions are asked",
                inline=False
            )
        
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AIChatSystem(bot))