import discord
from discord.ext import commands
from discord import app_commands
from utils.translations import get_text, set_guild_language, get_available_languages, create_embed
from utils.permissions import has_raid_mode_permission

class LanguageConfig(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="language", description="Configure the bot's language for this server")
    async def set_language(self, interaction: discord.Interaction):
        """Set the bot's language for the server"""
        if not has_raid_mode_permission(interaction.user):
            await interaction.response.send_message(
                get_text(interaction.guild.id, 'no_permission'),
                ephemeral=True
            )
            return

        # Create language selection embed
        embed = discord.Embed(
            title="🌐 Language Configuration",
            description="Choose the bot's language for this server:",
            color=discord.Color.blue()
        )
        
        languages = get_available_languages()
        for code, name in languages.items():
            flag = "🇺🇸" if code == "en" else "🇫🇷"
            embed.add_field(
                name=f"{flag} {name}",
                value=f"React with {flag} to select",
                inline=True
            )

        message = await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()
        
        # Add reactions
        await message.add_reaction("🇺🇸")
        await message.add_reaction("🇫🇷")

        def check(reaction, user):
            return (user == interaction.user and 
                   str(reaction.emoji) in ["🇺🇸", "🇫🇷"] and 
                   reaction.message.id == message.id)

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            
            language_map = {"🇺🇸": "en", "🇫🇷": "fr"}
            selected_language = language_map[str(reaction.emoji)]
            
            set_guild_language(interaction.guild.id, selected_language)
            
            # Create success embed in the selected language
            success_embed = create_embed(
                interaction.guild.id,
                'success',
                color=discord.Color.green()
            )
            
            language_names = {"en": "English", "fr": "Français"}
            success_embed.description = f"Language set to **{language_names[selected_language]}**"
            
            await message.edit(embed=success_embed, view=None)
            await message.clear_reactions()
            
        except TimeoutError:
            timeout_embed = discord.Embed(
                title="⏰ Timeout",
                description="Language selection timed out. Please try again.",
                color=discord.Color.orange()
            )
            await message.edit(embed=timeout_embed, view=None)
            await message.clear_reactions()

async def setup(bot):
    await bot.add_cog(LanguageConfig(bot))