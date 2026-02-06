import os
import discord

# Bot Application ID (Client ID) from environment or fallback
BOT_ID = int(os.getenv("DISCORD_CLIENT_ID", "1366294494386851880"))

# Required permissions for the bot functionality
permissions = discord.Permissions(
    # Basic bot permissions
    read_messages=True,
    send_messages=True,
    send_messages_in_threads=True,
    embed_links=True,
    attach_files=True,
    read_message_history=True,
    use_external_emojis=True,
    add_reactions=True,
    
    # Moderation permissions for raid protection
    manage_channels=True,
    manage_messages=True,
    manage_roles=True,
    kick_members=True,
    ban_members=True,
    moderate_members=True,
    
    # Warning system permissions
    view_audit_log=True,
    
    # Application command permissions are handled by scope
)

# Generate the invite URL
invite_url = f"https://discord.com/api/oauth2/authorize?client_id={BOT_ID}&permissions={permissions.value}&scope=bot%20applications.commands"

print("Discord Bot Invite Link:")
print("=" * 50)
print(invite_url)
print("=" * 50)
print("\nPermissions included:")
print("- Read/Send Messages & Embeds")
print("- Manage Channels (for raid lockdown)")
print("- Manage Messages (for spam cleanup)")
print("- Manage Roles (for raid restrictions)")
print("- Kick/Ban Members (for moderation)")
print("- View Audit Log (for warning tracking)")
print("- Slash Commands support")
print("\nBot Features:")
print("- Raid protection with 3-second scanning")
print("- Universal warning system (tracks DraftBot & other bots)")
print("- Spam detection and cleanup")
print("- Cross-bot warning tracking")
