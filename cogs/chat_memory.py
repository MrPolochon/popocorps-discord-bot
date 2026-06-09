"""
Chat Memory Cog - Access to PopoCorps' accumulated knowledge and conversation data
"""
import discord
from discord.ext import commands
from discord import app_commands
import sys
import os

# Add current directory to path for imports
sys.path.append('.')
from utils.free_ai_system import FreeAISystem
# Note: guild_settings import removed as not needed for this implementation


class ChatMemorySystem(commands.Cog):
    """Chat memory and knowledge access system"""
    
    def __init__(self, bot):
        self.bot = bot
        self.ai_system = FreeAISystem()
    
    @app_commands.command(name="chatmemory", description="🧠 Accéder à la mémoire conversationnelle de PopoCorps")
    @app_commands.describe(
        type="Type d'informations à afficher",
        user="Utilisateur spécifique (optionnel)"
    )
    @app_commands.choices(type=[
        app_commands.Choice(name="📊 Statistiques générales", value="stats"),
        app_commands.Choice(name="🧠 Connaissances apprises", value="knowledge"),
        app_commands.Choice(name="👤 Profil utilisateur", value="user"),
        app_commands.Choice(name="💬 Conversations récentes", value="recent"),
        app_commands.Choice(name="📈 Analyse complète", value="full")
    ])
    async def chatmemory(
        self, 
        interaction: discord.Interaction, 
        type: str = "stats",
        user: discord.Member = None
    ):
        """Commande pour accéder à la mémoire conversationnelle de PopoCorps"""
        
        if not interaction.guild:
            await interaction.response.send_message("Cette commande ne peut être utilisée qu'en serveur.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        guild_id = interaction.guild.id
        user_id = user.id if user else interaction.user.id
        
        try:
            if type == "stats":
                await self._show_memory_stats(interaction, guild_id, user_id if user else None)
            elif type == "knowledge":
                await self._show_knowledge_summary(interaction, guild_id)
            elif type == "user":
                await self._show_user_profile(interaction, guild_id, user_id)
            elif type == "recent":
                await self._show_recent_conversations(interaction, guild_id, user_id if user else None)
            elif type == "full":
                await self._show_full_analysis(interaction, guild_id)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Erreur lors de l'accès à la mémoire: {str(e)}", ephemeral=True)
    
    async def _show_memory_stats(self, interaction: discord.Interaction, guild_id: int, user_id: int = None):
        """Afficher les statistiques de mémoire"""
        stats = self.ai_system.get_chat_memory_stats(guild_id, user_id)
        
        embed = discord.Embed(
            title="🧠 Mémoire Conversationnelle de PopoCorps",
            description="📊 Statistiques générales de ma mémoire",
            color=0x3498db
        )
        
        # Statistiques générales
        embed.add_field(
            name="📈 Activité Globale",
            value=f"💬 **{stats['total_conversations']}** conversations\n"
                  f"👥 **{stats['unique_users']}** utilisateurs uniques\n"
                  f"🧠 **{stats['knowledge_entries']}** connaissances apprises\n"
                  f"👤 **{stats['user_profiles']}** profils utilisateur",
            inline=False
        )
        
        # Sentiments
        if stats['sentiment_breakdown']:
            sentiment_text = ""
            total_sentiments = sum(stats['sentiment_breakdown'].values())
            if total_sentiments > 0:
                for sentiment, count in stats['sentiment_breakdown'].items():
                    emoji = "😊" if sentiment == "positive" else "😢" if sentiment == "negative" else "😐"
                    percentage = (count / total_sentiments) * 100
                    sentiment_text += f"{emoji} {sentiment.capitalize()}: {count} ({percentage:.1f}%)\n"
            
            embed.add_field(
                name="🎭 Analyse Sentimentale",
                value=sentiment_text or "Aucune donnée",
                inline=True
            )
        
        # Sujets récents
        if stats['recent_topics']:
            topics_text = ""
            for topic, count in stats['recent_topics'][:5]:
                topics_text += f"🔸 {topic}: {count} fois\n"
            
            embed.add_field(
                name="🗣️ Sujets Récents (24h)",
                value=topics_text or "Aucun sujet récent",
                inline=True
            )
        
        # Utilisateurs les plus actifs
        if stats['top_users']:
            users_text = ""
            for user_id, msg_count, relationship in stats['top_users'][:3]:
                try:
                    user = self.bot.get_user(user_id)
                    name = user.display_name if user else f"Utilisateur {user_id}"
                    users_text += f"👤 {name}: {msg_count} messages (♥ {relationship:.1f})\n"
                except:
                    users_text += f"👤 Utilisateur {user_id}: {msg_count} messages\n"
            
            embed.add_field(
                name="🏆 Top Utilisateurs",
                value=users_text or "Aucun utilisateur",
                inline=False
            )
        
        # Patterns appris les plus réussis
        if stats['learned_patterns']:
            patterns_text = ""
            for phrase, success_rate, usage_count in stats['learned_patterns'][:3]:
                patterns_text += f"🎯 \"{phrase[:30]}{'...' if len(phrase) > 30 else ''}\" - {success_rate:.1f}% succès ({usage_count} fois)\n"
            
            embed.add_field(
                name="🎓 Meilleurs Apprentissages",
                value=patterns_text or "Aucun pattern appris",
                inline=False
            )
        
        # Informations spécifiques à l'utilisateur
        if user_id and 'user_specific' in stats:
            user_data = stats['user_specific']
            embed.add_field(
                name="👤 Votre Profil Personnel",
                value=f"💬 **{user_data['total_messages']}** messages échangés\n"
                      f"♥ **{user_data['relationship_strength']:.1f}** force de relation\n"
                      f"🗣️ Style: **{user_data['communication_style']}**\n"
                      f"🕒 Dernière interaction: {user_data['last_interaction']}",
                inline=False
            )
        
        embed.set_footer(text="🤖 PopoCorps - Gardien numérique qui apprend en permanence")
        await interaction.followup.send(embed=embed)
    
    async def _show_knowledge_summary(self, interaction: discord.Interaction, guild_id: int):
        """Afficher le résumé des connaissances"""
        knowledge = self.ai_system.get_all_knowledge_summary(guild_id)
        
        embed = discord.Embed(
            title="🧠 Connaissances Apprises de PopoCorps",
            description="🎓 Tout ce que j'ai appris sur ce serveur",
            color=0x9b59b6
        )
        
        # Progrès d'apprentissage
        if 'learning_progress' in knowledge:
            progress = knowledge['learning_progress']
            embed.add_field(
                name="📈 Progrès d'Apprentissage",
                value=f"🧠 **{progress['total_patterns_learned']}** patterns appris\n"
                      f"✅ **{progress['successful_patterns']}** patterns réussis\n"
                      f"🎯 **{progress['learning_effectiveness']:.1f}%** d'efficacité\n"
                      f"🌟 **{progress['knowledge_diversity']}** catégories maîtrisées",
                inline=False
            )
        
        # Comportements utilisateurs
        if 'user_behaviors' in knowledge:
            behaviors = knowledge['user_behaviors']
            
            # Styles de communication
            if behaviors.get('communication_styles'):
                styles_text = ""
                for style, count in behaviors['communication_styles'].items():
                    emoji = "🎩" if style == "formal" else "🗣️" if style == "casual" else "😤" if style == "vulgar" else "❓"
                    styles_text += f"{emoji} {style.capitalize()}: {count} utilisateurs\n"
                
                embed.add_field(
                    name="🗣️ Styles de Communication",
                    value=styles_text,
                    inline=True
                )
            
            # Niveaux de relation
            if behaviors.get('relationship_levels'):
                levels_text = ""
                for level, count in behaviors['relationship_levels'].items():
                    emoji = "❤️" if level == "familiar" else "🤝" if level == "getting_acquainted" else "👋"
                    levels_text += f"{emoji} {level.replace('_', ' ').title()}: {count}\n"
                
                embed.add_field(
                    name="♥ Niveaux de Relations",
                    value=levels_text,
                    inline=True
                )
        
        # Patterns de conversation
        if 'conversation_patterns' in knowledge:
            patterns = knowledge['conversation_patterns']
            
            # Types de messages les plus communs
            if patterns.get('most_common_types'):
                types_text = ""
                sorted_types = sorted(patterns['most_common_types'].items(), key=lambda x: x[1], reverse=True)
                for msg_type, count in sorted_types[:5]:
                    emoji = "❓" if msg_type == "question" else "💬" if msg_type == "general" else "🎉" if msg_type == "compliment" else "📢"
                    types_text += f"{emoji} {msg_type.title()}: {count}\n"
                
                embed.add_field(
                    name="💭 Types de Messages",
                    value=types_text,
                    inline=True
                )
            
            # Tendances sentimentales
            if patterns.get('sentiment_trends'):
                sentiment_text = ""
                total = sum(patterns['sentiment_trends'].values())
                for sentiment, count in patterns['sentiment_trends'].items():
                    emoji = "😊" if sentiment == "positive" else "😢" if sentiment == "negative" else "😐"
                    percentage = (count / total * 100) if total > 0 else 0
                    sentiment_text += f"{emoji} {sentiment.title()}: {percentage:.1f}%\n"
                
                embed.add_field(
                    name="🎭 Ambiance Générale",
                    value=sentiment_text,
                    inline=True
                )
        
        # Insights spécifiques au serveur
        if 'guild_insights' in knowledge and knowledge['guild_insights']:
            insights_text = ""
            for category, patterns in list(knowledge['guild_insights'].items())[:3]:
                insights_text += f"🔸 **{category.title()}**: {len(patterns)} patterns\n"
            
            embed.add_field(
                name="🎯 Spécialités du Serveur",
                value=insights_text or "Aucune spécialité identifiée",
                inline=False
            )
        
        embed.set_footer(text="🤖 PopoCorps s'améliore continuellement grâce à vos interactions")
        await interaction.followup.send(embed=embed)
    
    async def _show_user_profile(self, interaction: discord.Interaction, guild_id: int, user_id: int):
        """Afficher le profil utilisateur détaillé"""
        stats = self.ai_system.get_chat_memory_stats(guild_id, user_id)
        
        target_user = self.bot.get_user(user_id)
        user_name = target_user.display_name if target_user else f"Utilisateur {user_id}"
        
        embed = discord.Embed(
            title=f"👤 Profil de {user_name}",
            description="🧠 Ce que PopoCorps sait sur cet utilisateur",
            color=0xe74c3c
        )
        
        if 'user_specific' in stats:
            user_data = stats['user_specific']
            
            embed.add_field(
                name="📊 Statistiques Personnelles",
                value=f"💬 **{user_data['total_messages']}** messages avec moi\n"
                      f"♥ **{user_data['relationship_strength']:.1f}/1.0** force de relation\n"
                      f"🗣️ Style: **{user_data['communication_style']}**\n"
                      f"🕒 Dernière fois: {user_data['last_interaction']}",
                inline=False
            )
            
            # Conversations récentes
            if 'recent_conversations' in user_data:
                convs_text = ""
                for conv in user_data['recent_conversations'][:3]:
                    emoji = "😊" if conv['sentiment'] == "positive" else "😢" if conv['sentiment'] == "negative" else "😐"
                    convs_text += f"{emoji} **{conv['timestamp']}**\n"
                    convs_text += f"👤 {conv['content']}\n"
                    if conv['response']:
                        convs_text += f"🤖 {conv['response']}\n\n"
                
                embed.add_field(
                    name="💬 Conversations Récentes",
                    value=convs_text or "Aucune conversation récente",
                    inline=False
                )
        else:
            embed.add_field(
                name="❓ Utilisateur Inconnu",
                value="Je n'ai pas encore eu de conversations significatives avec cet utilisateur.",
                inline=False
            )
        
        embed.set_footer(text="🤖 PopoCorps garde précieusement le souvenir de nos échanges")
        await interaction.followup.send(embed=embed)
    
    async def _show_recent_conversations(self, interaction: discord.Interaction, guild_id: int, user_id: int = None):
        """Afficher les conversations récentes"""
        stats = self.ai_system.get_chat_memory_stats(guild_id, user_id)
        
        embed = discord.Embed(
            title="💬 Conversations Récentes",
            description="🕒 Derniers échanges avec PopoCorps",
            color=0xf39c12
        )
        
        if user_id and 'user_specific' in stats and 'recent_conversations' in stats['user_specific']:
            conversations = stats['user_specific']['recent_conversations']
            
            for i, conv in enumerate(conversations[:5], 1):
                emoji = "😊" if conv['sentiment'] == "positive" else "😢" if conv['sentiment'] == "negative" else "😐"
                
                embed.add_field(
                    name=f"{emoji} Conversation #{i} - {conv['timestamp']}",
                    value=f"👤 **Vous:** {conv['content']}\n🤖 **PopoCorps:** {conv['response'] or 'Pas de réponse enregistrée'}",
                    inline=False
                )
        else:
            # Afficher les conversations récentes du serveur
            embed.add_field(
                name="📊 Activité Récente du Serveur",
                value=f"💬 {stats['total_conversations']} conversations totales\n"
                      f"👥 {stats['unique_users']} utilisateurs actifs\n"
                      f"🧠 {stats['knowledge_entries']} éléments appris",
                inline=False
            )
            
            if stats['recent_topics']:
                topics_text = ""
                for topic, count in stats['recent_topics'][:5]:
                    topics_text += f"🔸 {topic}: {count} mentions\n"
                
                embed.add_field(
                    name="🗣️ Sujets Populaires (24h)",
                    value=topics_text,
                    inline=False
                )
        
        embed.set_footer(text="🤖 PopoCorps se souvient de tout pour mieux vous servir")
        await interaction.followup.send(embed=embed)
    
    async def _show_full_analysis(self, interaction: discord.Interaction, guild_id: int):
        """Afficher l'analyse complète"""
        stats = self.ai_system.get_chat_memory_stats(guild_id)
        knowledge = self.ai_system.get_all_knowledge_summary(guild_id)
        
        embed = discord.Embed(
            title="📈 Analyse Complète de PopoCorps",
            description="🧠 Vision globale de ma mémoire et de mes apprentissages",
            color=0x1abc9c
        )
        
        # Métriques clés
        embed.add_field(
            name="🎯 Métriques Clés",
            value=f"💬 **{stats['total_conversations']}** conversations analysées\n"
                  f"🧠 **{stats['knowledge_entries']}** patterns appris\n"
                  f"👥 **{stats['unique_users']}** relations développées\n"
                  f"📈 **{knowledge.get('learning_progress', {}).get('learning_effectiveness', 0):.1f}%** efficacité d'apprentissage",
            inline=True
        )
        
        # Évolution temporelle
        if knowledge.get('conversation_patterns', {}).get('peak_hours'):
            hours = knowledge['conversation_patterns']['peak_hours']
            peak_hour = max(hours.items(), key=lambda x: x[1])[0] if hours else 12
            embed.add_field(
                name="⏰ Activité Temporelle",
                value=f"🔥 Heure de pointe: **{peak_hour}h**\n"
                      f"📊 Répartition sur 24h disponible\n"
                      f"📈 Tendances d'engagement analysées",
                inline=True
            )
        
        # Intelligence émotionnelle
        if stats['sentiment_breakdown']:
            total = sum(stats['sentiment_breakdown'].values())
            positive_ratio = (stats['sentiment_breakdown'].get('positive', 0) / total * 100) if total > 0 else 0
            embed.add_field(
                name="🎭 Intelligence Émotionnelle",
                value=f"😊 **{positive_ratio:.1f}%** d'interactions positives\n"
                      f"🎯 Adaptation au style de communication\n"
                      f"♥ Relations renforcées automatiquement",
                inline=True
            )
        
        # Capacités adaptatives
        diversity = knowledge.get('learning_progress', {}).get('knowledge_diversity', 0)
        embed.add_field(
            name="🌟 Capacités Adaptatives",
            value=f"🎓 **{diversity}** domaines de spécialisation\n"
                  f"🔄 Apprentissage continu activé\n"
                  f"🧠 Mémoire persistante garantie\n"
                  f"⚡ Réponses contextuelles optimisées",
            inline=False
        )
        
        embed.set_footer(text="🤖 PopoCorps - IA conversationnelle évolutive | Données mises à jour en temps réel")
        await interaction.followup.send(embed=embed)


async def setup(bot):
    """Setup function for the cog"""
    await bot.add_cog(ChatMemorySystem(bot))