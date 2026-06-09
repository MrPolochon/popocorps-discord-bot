#!/usr/bin/env python3
"""
Nettoyage des données de guildes obsolètes
Supprime les configurations des serveurs qui ont retiré le bot
"""

import asyncio
import discord
from discord.ext import commands
import os
import json
import shutil
from datetime import datetime

# Token du bot depuis l'environnement
TOKEN = os.environ.get('DISCORD_TOKEN')

# Configuration du bot
intents = discord.Intents.default()
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot connecté : {bot.user}")
    print(f"Serveurs actuels : {len(bot.guilds)}")
    
    # Lister les serveurs actuels
    current_guilds = set(str(guild.id) for guild in bot.guilds)
    print("Serveurs connectés :")
    for guild in bot.guilds:
        print(f"  - {guild.name} (ID: {guild.id})")
    
    # Vérifier les données raid obsolètes
    raid_data_dir = "raid_data"
    if os.path.exists(raid_data_dir):
        stored_guilds = [d for d in os.listdir(raid_data_dir) 
                        if os.path.isdir(os.path.join(raid_data_dir, d)) and d.isdigit()]
        
        print(f"\nDonnées stockées : {len(stored_guilds)} guildes")
        obsolete_guilds = []
        
        for guild_id in stored_guilds:
            if guild_id not in current_guilds:
                obsolete_guilds.append(guild_id)
                print(f"  - Guilde obsolète : {guild_id}")
        
        if obsolete_guilds:
            print(f"\n{len(obsolete_guilds)} guildes obsolètes détectées")
            
            # Créer un backup avant nettoyage
            backup_dir = f"backup_raid_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            if not os.path.exists(backup_dir):
                shutil.copytree(raid_data_dir, backup_dir)
                print(f"Backup créé : {backup_dir}")
            
            # Supprimer les données obsolètes
            for guild_id in obsolete_guilds:
                obsolete_path = os.path.join(raid_data_dir, guild_id)
                if os.path.exists(obsolete_path):
                    shutil.rmtree(obsolete_path)
                    print(f"Supprimé : données de la guilde {guild_id}")
        else:
            print("Aucune donnée obsolète trouvée")
    
    # Rapport final
    print(f"\nRapport final :")
    print(f"  - Serveurs actifs : {len(current_guilds)}")
    print(f"  - Données nettoyées : {len(obsolete_guilds) if 'obsolete_guilds' in locals() else 0}")
    
    await bot.close()

async def main():
    if not TOKEN:
        print("Erreur : Token Discord manquant")
        return
    
    try:
        await bot.start(TOKEN)
    except Exception as e:
        print(f"Erreur : {e}")

if __name__ == "__main__":
    asyncio.run(main())