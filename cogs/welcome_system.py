import discord
from discord.ext import commands
import logging
from datetime import datetime, timezone
from utils.guild_settings import guild_settings
from PIL import Image, ImageDraw, ImageFont, ImageSequence
import requests
import io
import asyncio
import aiohttp
import os
from typing import Optional

class WelcomeSystem(commands.Cog):
    """Welcome and goodbye message system with custom images"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.temp_dir = "temp_images"
        self.fonts_dir = "fonts"
        
        # Create directories if they don't exist
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.fonts_dir, exist_ok=True)
        
        # Available fonts dictionary
        self.available_fonts = {
            "Arial": "arial.ttf",
            "Times": "times.ttf",
            "Courier": "courier.ttf",
            "Helvetica": "helvetica.ttf",
            "Comic Sans": "comic.ttf",
            "Impact": "impact.ttf",
            "Trebuchet": "trebuchet.ttf"
        }
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Handle member join events"""
        try:
            guild_id = member.guild.id
            self.logger.info(f"Member join detected: {member.name} ({member.id}) in {member.guild.name} ({guild_id})")
            
            # Check if welcome messages are enabled
            welcome_enabled = guild_settings.is_welcome_enabled(guild_id)
            self.logger.info(f"Welcome enabled for guild {guild_id}: {welcome_enabled}")
            if not welcome_enabled:
                self.logger.info(f"Welcome messages disabled for guild {guild_id}")
                return
            
            # Get welcome channel
            welcome_channel_id = guild_settings.get_welcome_channel(guild_id)
            self.logger.info(f"Welcome channel ID for guild {guild_id}: {welcome_channel_id}")
            if not welcome_channel_id:
                self.logger.warning(f"No welcome channel configured for guild {guild_id}")
                return
            
            welcome_channel = member.guild.get_channel(welcome_channel_id)
            if not welcome_channel:
                self.logger.error(f"Welcome channel {welcome_channel_id} not found in guild {guild_id}")
                return
            
            self.logger.info(f"Found welcome channel: {welcome_channel.name} ({welcome_channel_id})")
            
            # Get welcome message template
            message_template = guild_settings.get_welcome_message(guild_id)
            self.logger.info(f"Welcome message template: {message_template[:50]}...")
            
            # Create custom welcome image
            self.logger.info("Attempting to create welcome image...")
            welcome_image = await self.create_welcome_image(member, message_template, "welcome")
            
            if welcome_image:
                # Send welcome message with custom image
                self.logger.info("Sending welcome message with custom image...")
                file = discord.File(welcome_image, filename="welcome.png")
                await welcome_channel.send(file=file)
                self.logger.info(f"Successfully sent welcome image for {member.name}")
            else:
                # Fallback to embed if image generation fails
                self.logger.warning("Image generation failed, using embed fallback...")
                embed = await self.create_welcome_embed(member, message_template)
                await welcome_channel.send(embed=embed)
                self.logger.info(f"Successfully sent welcome embed for {member.name}")
            
            self.logger.info(f"Welcome message sent successfully for {member.name} in {member.guild.name}")
            
        except Exception as e:
            self.logger.error(f"Error sending welcome message for {member.name if member else 'unknown'}: {e}")
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Handle member leave events"""
        try:
            guild_id = member.guild.id
            self.logger.info(f"Member leave detected: {member.name} ({member.id}) from {member.guild.name} ({guild_id})")
            
            # Check if goodbye messages are enabled
            goodbye_enabled = guild_settings.is_goodbye_enabled(guild_id)
            self.logger.info(f"Goodbye enabled for guild {guild_id}: {goodbye_enabled}")
            if not goodbye_enabled:
                self.logger.info(f"Goodbye messages disabled for guild {guild_id}")
                return
            
            # Get goodbye channel
            goodbye_channel_id = guild_settings.get_goodbye_channel(guild_id)
            self.logger.info(f"Goodbye channel ID for guild {guild_id}: {goodbye_channel_id}")
            if not goodbye_channel_id:
                self.logger.warning(f"No goodbye channel configured for guild {guild_id}")
                return
            
            goodbye_channel = member.guild.get_channel(goodbye_channel_id)
            if not goodbye_channel:
                self.logger.error(f"Goodbye channel {goodbye_channel_id} not found in guild {guild_id}")
                return
            
            self.logger.info(f"Found goodbye channel: {goodbye_channel.name} ({goodbye_channel_id})")
            
            # Get goodbye message template
            message_template = guild_settings.get_goodbye_message(guild_id)
            self.logger.info(f"Goodbye message template: {message_template[:50]}...")
            
            # Create custom goodbye image
            self.logger.info("Attempting to create goodbye image...")
            goodbye_image = await self.create_welcome_image(member, message_template, "goodbye")
            
            if goodbye_image:
                # Send goodbye message with custom image
                self.logger.info("Sending goodbye message with custom image...")
                file = discord.File(goodbye_image, filename="goodbye.png")
                await goodbye_channel.send(file=file)
                self.logger.info(f"Successfully sent goodbye image for {member.name}")
            else:
                # Fallback to embed if image generation fails
                self.logger.warning("Image generation failed, using embed fallback...")
                embed = await self.create_goodbye_embed(member, message_template)
                await goodbye_channel.send(embed=embed)
                self.logger.info(f"Successfully sent goodbye embed for {member.name}")
            
            self.logger.info(f"Goodbye message sent successfully for {member.name} from {member.guild.name}")
            
        except Exception as e:
            self.logger.error(f"Error sending goodbye message for {member.name if member else 'unknown'}: {e}")
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
    
    @commands.command(name='testwelcome')
    @commands.has_permissions(administrator=True)
    async def test_welcome(self, ctx):
        """Test the welcome system by simulating a join event"""
        try:
            self.logger.info(f"Admin {ctx.author.name} testing welcome system in {ctx.guild.name}")
            
            # Simulate the member join event with the command author
            await self.on_member_join(ctx.author)
            
            await ctx.send("✅ Test de bienvenue effectué ! Vérifiez le canal de bienvenue.")
            self.logger.info(f"Welcome test completed for {ctx.author.name}")
            
        except Exception as e:
            await ctx.send(f"❌ Erreur lors du test de bienvenue: {e}")
            self.logger.error(f"Welcome test failed: {e}")
    
    @commands.command(name='testgoodbye')
    @commands.has_permissions(administrator=True)
    async def test_goodbye(self, ctx):
        """Test the goodbye system by simulating a leave event"""
        try:
            self.logger.info(f"Admin {ctx.author.name} testing goodbye system in {ctx.guild.name}")
            
            # Simulate the member leave event with the command author
            await self.on_member_remove(ctx.author)
            
            await ctx.send("✅ Test d'au revoir effectué ! Vérifiez le canal d'au revoir.")
            self.logger.info(f"Goodbye test completed for {ctx.author.name}")
            
        except Exception as e:
            await ctx.send(f"❌ Erreur lors du test d'au revoir: {e}")
            self.logger.error(f"Goodbye test failed: {e}")
    
    async def create_welcome_embed(self, member, message_template):
        """Create a styled welcome embed similar to Koya's design"""
        # Format the message template
        formatted_message = message_template.format(
            user_mention=member.mention,
            user_name=member.display_name,
            server_name=member.guild.name,
            member_count=member.guild.member_count
        )
        
        # Create embed with cosmic theme
        embed = discord.Embed(
            title="🌟 WELCOME",
            description=formatted_message,
            color=0x9966FF,  # Purple color similar to the image
            timestamp=datetime.now(timezone.utc)
        )
        
        # Add member avatar
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # Add server info
        embed.add_field(
            name="Member Count",
            value=f"#{member.guild.member_count}",
            inline=True
        )
        
        embed.add_field(
            name="Account Created",
            value=f"<t:{int(member.created_at.timestamp())}:R>",
            inline=True
        )
        
        # Add footer
        embed.set_footer(
            text=f"Welcome to {member.guild.name}",
            icon_url=member.guild.icon.url if member.guild.icon else None
        )
        
        return embed
    
    async def create_goodbye_embed(self, member, message_template):
        """Create a styled goodbye embed"""
        # Format the message template
        formatted_message = message_template.format(
            user_mention=member.mention,
            user_name=member.display_name,
            server_name=member.guild.name,
            member_count=member.guild.member_count
        )
        
        # Create embed with cosmic theme
        embed = discord.Embed(
            title="👋 GOODBYE",
            description=formatted_message,
            color=0x4169E1,  # Blue color for goodbye
            timestamp=datetime.now(timezone.utc)
        )
        
        # Add member avatar
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # Add server info
        embed.add_field(
            name="Time in Server",
            value=f"<t:{int(member.joined_at.timestamp())}:R>" if member.joined_at else "Unknown",
            inline=True
        )
        
        embed.add_field(
            name="Members Left",
            value=f"{member.guild.member_count}",
            inline=True
        )
        
        # Add footer
        embed.set_footer(
            text=f"Goodbye from {member.guild.name}",
            icon_url=member.guild.icon.url if member.guild.icon else None
        )
        
        return embed
    
    async def download_image(self, url: str) -> Optional[bytes]:
        """Download image from URL"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.read()
            return None
        except Exception as e:
            self.logger.error(f"Error downloading image: {e}")
            return None
    
    async def create_welcome_image(self, member, message_template: str, message_type: str) -> Optional[str]:
        """Create custom welcome/goodbye image with background and custom font"""
        try:
            guild_id = member.guild.id
            
            # Get settings based on message type
            if message_type == "welcome":
                background_url = guild_settings.get_welcome_background(guild_id)
                font_name = guild_settings.get_welcome_font(guild_id)
                title_text = "WELCOME"
                color = (153, 102, 255)  # Purple
            else:
                background_url = guild_settings.get_goodbye_background(guild_id)
                font_name = guild_settings.get_goodbye_font(guild_id)
                title_text = "GOODBYE"
                color = (65, 105, 225)  # Blue
            
            # Format message
            formatted_message = message_template.format(
                user_mention=f"@{member.display_name}",
                user_name=member.display_name,
                server_name=member.guild.name,
                member_count=member.guild.member_count
            )
            
            # Create base image size
            width, height = 800, 400
            
            # Handle background image
            if background_url:
                bg_data = await self.download_image(background_url)
                if bg_data:
                    try:
                        background = Image.open(io.BytesIO(bg_data))
                        
                        # Check if it's a GIF
                        if background.format == 'GIF':
                            try:
                                # Check if GIF has multiple frames
                                background.seek(1)
                                background.seek(0)
                                is_animated = True
                            except:
                                is_animated = False
                            
                            if is_animated:
                                return await self.create_animated_welcome_gif(
                                    background, member, formatted_message, title_text, color, font_name
                                )
                        else:
                            # Resize background to fit
                            background = background.convert('RGBA')
                            background = background.resize((width, height), Image.Resampling.LANCZOS)
                    except Exception as e:
                        self.logger.error(f"Error processing background image: {e}")
                        background = self.create_default_background(width, height, color)
                else:
                    background = self.create_default_background(width, height, color)
            else:
                background = self.create_default_background(width, height, color)
            
            # Create the welcome image
            img = background.copy()
            draw = ImageDraw.Draw(img)
            
            # Load custom font with improved error handling
            try:
                font_path = self.get_font_path(font_name)
                if font_path and os.path.exists(font_path):
                    title_font = ImageFont.truetype(font_path, 48)
                    message_font = ImageFont.truetype(font_path, 24)
                    name_font = ImageFont.truetype(font_path, 32)
                else:
                    # Use default font
                    title_font = ImageFont.load_default()
                    message_font = ImageFont.load_default()  
                    name_font = ImageFont.load_default()
            except Exception:
                # Fallback to default font
                title_font = ImageFont.load_default()
                message_font = ImageFont.load_default()
                name_font = ImageFont.load_default()
            
            # Add avatar circle
            try:
                avatar_data = await self.download_image(str(member.display_avatar.url))
                if avatar_data:
                    avatar = Image.open(io.BytesIO(avatar_data))
                    avatar = avatar.convert('RGBA')
                    avatar = avatar.resize((120, 120), Image.Resampling.LANCZOS)
                    
                    # Create circular mask
                    mask = Image.new('L', (120, 120), 0)
                    mask_draw = ImageDraw.Draw(mask)
                    mask_draw.ellipse((0, 0, 120, 120), fill=255)
                    
                    # Apply mask to avatar
                    avatar.putalpha(mask)
                    
                    # Paste avatar on image
                    avatar_x = (width - 120) // 2
                    avatar_y = 50
                    img.paste(avatar, (avatar_x, avatar_y), avatar)
            except Exception as e:
                self.logger.error(f"Error adding avatar: {e}")
            
            # Add title text with outline
            title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
            title_width = title_bbox[2] - title_bbox[0]
            title_x = (width - title_width) // 2
            title_y = 190
            
            # Draw title outline
            for adj_x in range(-2, 3):
                for adj_y in range(-2, 3):
                    if adj_x != 0 or adj_y != 0:
                        draw.text((title_x + adj_x, title_y + adj_y), title_text, font=title_font, fill=(0, 0, 0))
            
            # Draw title
            draw.text((title_x, title_y), title_text, font=title_font, fill=(255, 255, 255))
            
            # Add member name
            name_bbox = draw.textbbox((0, 0), member.display_name, font=name_font)
            name_width = name_bbox[2] - name_bbox[0]
            name_x = (width - name_width) // 2
            name_y = 250
            
            # Draw name outline
            for adj_x in range(-1, 2):
                for adj_y in range(-1, 2):
                    if adj_x != 0 or adj_y != 0:
                        draw.text((name_x + adj_x, name_y + adj_y), member.display_name, font=name_font, fill=(0, 0, 0))
            
            # Draw name
            draw.text((name_x, name_y), member.display_name, font=name_font, fill=(255, 255, 255))
            
            # Add additional message if it's not just the default
            if len(formatted_message) > len(member.display_name) + 20:
                lines = self.wrap_text(formatted_message, message_font, width - 100)
                total_height = len(lines) * 30
                start_y = 300
                
                for i, line in enumerate(lines):
                    line_bbox = draw.textbbox((0, 0), line, font=message_font)
                    line_width = line_bbox[2] - line_bbox[0]
                    line_x = (width - line_width) // 2
                    line_y = start_y + (i * 30)
                    
                    # Draw line outline
                    for adj_x in range(-1, 2):
                        for adj_y in range(-1, 2):
                            if adj_x != 0 or adj_y != 0:
                                draw.text((line_x + adj_x, line_y + adj_y), line, font=message_font, fill=(0, 0, 0))
                    
                    # Draw line
                    draw.text((line_x, line_y), line, font=message_font, fill=(255, 255, 255))
            
            # Save image
            filename = f"{message_type}_{member.id}_{guild_id}.png"
            filepath = os.path.join(self.temp_dir, filename)
            img.save(filepath, 'PNG')
            
            return filepath
            
        except Exception as e:
            self.logger.error(f"Error creating {message_type} image: {e}")
            return None
    
    async def create_animated_welcome_gif(self, background_gif, member, message, title_text, color, font_name):
        """Create animated welcome GIF with custom background"""
        try:
            frames = []
            
            for frame in ImageSequence.Iterator(background_gif):
                frame = frame.convert('RGBA')
                frame = frame.resize((800, 400), Image.Resampling.LANCZOS)
                
                # Create overlay for text
                overlay = Image.new('RGBA', (800, 400), (0, 0, 0, 0))
                draw = ImageDraw.Draw(overlay)
                
                # Load font
                try:
                    font_path = self.get_font_path(font_name)
                    if font_path:
                        title_font = ImageFont.truetype(font_path, 48)
                        name_font = ImageFont.truetype(font_path, 32)
                    else:
                        raise Exception("No font found")
                except:
                    title_font = ImageFont.load_default()
                    name_font = ImageFont.load_default()
                
                # Add title
                title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
                title_width = title_bbox[2] - title_bbox[0]
                title_x = (800 - title_width) // 2
                title_y = 150
                
                # Draw title with outline
                for adj_x in range(-2, 3):
                    for adj_y in range(-2, 3):
                        if adj_x != 0 or adj_y != 0:
                            draw.text((title_x + adj_x, title_y + adj_y), title_text, font=title_font, fill=(0, 0, 0, 255))
                draw.text((title_x, title_y), title_text, font=title_font, fill=(255, 255, 255, 255))
                
                # Add member name
                name_bbox = draw.textbbox((0, 0), member.display_name, font=name_font)
                name_width = name_bbox[2] - name_bbox[0]
                name_x = (800 - name_width) // 2
                name_y = 220
                
                # Draw name with outline
                for adj_x in range(-1, 2):
                    for adj_y in range(-1, 2):
                        if adj_x != 0 or adj_y != 0:
                            draw.text((name_x + adj_x, name_y + adj_y), member.display_name, font=name_font, fill=(0, 0, 0, 255))
                draw.text((name_x, name_y), member.display_name, font=name_font, fill=(255, 255, 255, 255))
                
                # Composite frame with overlay
                final_frame = Image.alpha_composite(frame, overlay)
                frames.append(final_frame.convert('RGB'))
            
            # Save as GIF
            filename = f"welcome_{member.id}_{member.guild.id}.gif"
            filepath = os.path.join(self.temp_dir, filename)
            
            frames[0].save(
                filepath,
                save_all=True,
                append_images=frames[1:],
                duration=background_gif.info.get('duration', 100),
                loop=0
            )
            
            return filepath
            
        except Exception as e:
            self.logger.error(f"Error creating animated GIF: {e}")
            return None
    
    def create_default_background(self, width: int, height: int, color: tuple) -> Image.Image:
        """Create a default cosmic background"""
        # Create gradient background
        img = Image.new('RGB', (width, height), color)
        draw = ImageDraw.Draw(img)
        
        # Add cosmic effect with circles
        import random
        for _ in range(100):
            x = random.randint(0, width)
            y = random.randint(0, height)
            size = random.randint(1, 3)
            brightness = random.randint(100, 255)
            draw.ellipse(
                (x - size, y - size, x + size, y + size),
                fill=(brightness, brightness, brightness)
            )
        
        return img
    
    def get_font_path(self, font_name: str) -> Optional[str]:
        """Get path to font file or return system default"""
        if font_name in self.available_fonts:
            font_path = os.path.join(self.fonts_dir, self.available_fonts[font_name])
            if os.path.exists(font_path):
                return font_path
        
        # Try system fonts
        system_fonts = [
            "/System/Library/Fonts/Arial.ttf",  # macOS
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
            "C:\\Windows\\Fonts\\arial.ttf",  # Windows
        ]
        
        for font_path in system_fonts:
            if os.path.exists(font_path):
                return font_path
        
        # Return None to use default font
        return None
    
    def wrap_text(self, text: str, font, max_width: int) -> list:
        """Wrap text to fit within max_width"""
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = font.getbbox(test_line)
            if bbox[2] - bbox[0] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines

async def setup(bot):
    await bot.add_cog(WelcomeSystem(bot))