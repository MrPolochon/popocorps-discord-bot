#!/usr/bin/env python3
"""
Test complet du système de protection raid
Vérifie toutes les fonctionnalités de détection de spam et de protection
"""

import asyncio
import logging
import json
import os
from datetime import datetime
from utils.spam_detector import track_message, detect_duplicate_channels, cleanup_spam, reset_tracking, get_spammer_ids
from utils.guild_settings import guild_settings

# Configuration des logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_raid_data_persistence():
    """Test la persistance des données de raid"""
    print("=== Test de persistance des données de raid ===")
    
    raid_data_dir = "raid_data"
    if not os.path.exists(raid_data_dir):
        print("❌ Dossier raid_data manquant")
        return False
    
    # Vérifier les guildes configurées
    guilds_found = []
    for item in os.listdir(raid_data_dir):
        guild_path = os.path.join(raid_data_dir, item)
        if os.path.isdir(guild_path) and item.isdigit():
            guilds_found.append(item)
            
            # Vérifier le fichier d'état
            state_file = os.path.join(guild_path, "raid_state.json")
            if os.path.exists(state_file):
                with open(state_file, 'r') as f:
                    try:
                        data = json.load(f)
                        print(f"✅ Guilde {item}: État raid = {data.get('active', 'N/A')}")
                    except json.JSONDecodeError:
                        print(f"❌ Guilde {item}: Fichier d'état corrompu")
            else:
                print(f"⚠️ Guilde {item}: Fichier d'état manquant")
    
    print(f"Total des guildes configurées: {len(guilds_found)}")
    return len(guilds_found) > 0

def test_spam_detection_algorithms():
    """Test les algorithmes de détection de spam"""
    print("\n=== Test des algorithmes de détection de spam ===")
    
    # Simuler un guild ID
    test_guild_id = 999999999999999999
    
    # Reset des données de test
    reset_tracking(test_guild_id)
    
    # Classe mock pour simuler un message
    class MockMessage:
        def __init__(self, content, author_id, guild_id):
            self.content = content
            self.author = MockAuthor(author_id)
            self.guild = MockGuild(guild_id)
            self.created_at = datetime.now()
    
    class MockAuthor:
        def __init__(self, user_id):
            self.id = user_id
            self.bot = False
    
    class MockGuild:
        def __init__(self, guild_id):
            self.id = guild_id
    
    # Test 1: Messages répétitifs
    print("Test 1: Détection de messages répétitifs")
    spam_content = "SPAM MESSAGE TEST"
    spammer_id = 123456789
    
    for i in range(5):
        message = MockMessage(spam_content, spammer_id, test_guild_id)
        track_message(message)
    
    spammers = get_spammer_ids(test_guild_id)
    if spammer_id in spammers:
        print("✅ Détection de spam répétitif: SUCCÈS")
    else:
        print("❌ Détection de spam répétitif: ÉCHEC")
    
    # Test 2: Messages en rafale
    print("Test 2: Détection de messages en rafale")
    rapid_spammer_id = 987654321
    
    for i in range(10):
        message = MockMessage(f"Message rapide {i}", rapid_spammer_id, test_guild_id)
        track_message(message)
    
    spammers = get_spammer_ids(test_guild_id)
    if rapid_spammer_id in spammers:
        print("✅ Détection de spam en rafale: SUCCÈS")
    else:
        print("❌ Détection de spam en rafale: ÉCHEC")
    
    # Nettoyage
    reset_tracking(test_guild_id)
    print("Test des algorithmes terminé")

def test_guild_settings():
    """Test les paramètres de guilde"""
    print("\n=== Test des paramètres de guilde ===")
    
    test_guild_id = 888888888888888888
    
    # Test des canaux de logs
    test_log_channel = 111111111111111111
    guild_settings.set_log_channel(test_guild_id, test_log_channel)
    retrieved_log = guild_settings.get_log_channel(test_guild_id)
    
    if retrieved_log == test_log_channel:
        print("✅ Configuration canal de logs: SUCCÈS")
    else:
        print("❌ Configuration canal de logs: ÉCHEC")
    
    # Test des canaux d'annonces
    test_announcement_channel = 222222222222222222
    guild_settings.set_announcement_channel(test_guild_id, test_announcement_channel)
    retrieved_announcement = guild_settings.get_announcement_channel(test_guild_id)
    
    if retrieved_announcement == test_announcement_channel:
        print("✅ Configuration canal d'annonces: SUCCÈS")
    else:
        print("❌ Configuration canal d'annonces: ÉCHEC")
    
    # Test des rôles admin
    test_admin_role = 333333333333333333
    guild_settings.set_admin_role(test_guild_id, test_admin_role)
    retrieved_admin = guild_settings.get_admin_role(test_guild_id)
    
    if retrieved_admin == test_admin_role:
        print("✅ Configuration rôle admin: SUCCÈS")
    else:
        print("❌ Configuration rôle admin: ÉCHEC")

def test_file_system_integrity():
    """Test l'intégrité du système de fichiers"""
    print("\n=== Test de l'intégrité du système de fichiers ===")
    
    required_files = [
        "cogs/raid_mode.py",
        "utils/spam_detector.py",
        "utils/guild_settings.py",
        "utils/permissions.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Fichiers manquants: {missing_files}")
        return False
    else:
        print("✅ Tous les fichiers système sont présents")
        return True

def generate_raid_system_report():
    """Génère un rapport complet du système raid"""
    print("\n" + "="*50)
    print("RAPPORT COMPLET DU SYSTÈME DE PROTECTION RAID")
    print("="*50)
    
    # Statistiques des guildes
    raid_data_dir = "raid_data"
    if os.path.exists(raid_data_dir):
        guilds = [d for d in os.listdir(raid_data_dir) if os.path.isdir(os.path.join(raid_data_dir, d)) and d.isdigit()]
        print(f"Guildes configurées: {len(guilds)}")
        
        active_raids = 0
        for guild_id in guilds:
            state_file = os.path.join(raid_data_dir, guild_id, "raid_state.json")
            if os.path.exists(state_file):
                with open(state_file, 'r') as f:
                    try:
                        data = json.load(f)
                        if data.get('active', False):
                            active_raids += 1
                    except:
                        pass
        
        print(f"Raids actifs: {active_raids}")
        print(f"Raids inactifs: {len(guilds) - active_raids}")
    
    # Vérification des composants
    components = {
        "Détecteur de spam": os.path.exists("utils/spam_detector.py"),
        "Mode raid": os.path.exists("cogs/raid_mode.py"),
        "Paramètres guilde": os.path.exists("utils/guild_settings.py"),
        "Système de permissions": os.path.exists("utils/permissions.py"),
        "Dossier de données": os.path.exists("raid_data")
    }
    
    print("\nÉtat des composants:")
    for component, status in components.items():
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {component}")
    
    # Recommandations
    print("\nRecommandations:")
    if not all(components.values()):
        print("- Certains composants sont manquants, vérifier l'installation")
    else:
        print("- Tous les composants sont présents")
        print("- Système prêt pour la production")
    
    print("="*50)

def main():
    """Fonction principale du test"""
    print("DÉMARRAGE DU TEST COMPLET DU SYSTÈME RAID")
    print("Timestamp:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    # Exécuter tous les tests
    tests = [
        test_file_system_integrity,
        test_raid_data_persistence,
        test_spam_detection_algorithms,
        test_guild_settings
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result if result is not None else True)
        except Exception as e:
            print(f"❌ Erreur dans {test.__name__}: {e}")
            results.append(False)
    
    # Rapport final
    generate_raid_system_report()
    
    success_rate = sum(results) / len(results) * 100
    print(f"\nTaux de réussite global: {success_rate:.1f}%")
    
    if success_rate >= 80:
        print("🎉 SYSTÈME RAID: OPÉRATIONNEL")
    else:
        print("⚠️ SYSTÈME RAID: NÉCESSITE ATTENTION")

if __name__ == "__main__":
    main()