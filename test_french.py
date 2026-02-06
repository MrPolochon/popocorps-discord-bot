#!/usr/bin/env python3
"""
Quick test script to verify French translations
"""

from utils.translations import set_guild_language, get_text, get_guild_language

# Test guild ID
test_guild = 123456789

print("Testing French translation system...")

# Set language to French
result = set_guild_language(test_guild, 'fr')
print(f"Set language to French: {result}")

# Check current language
current_lang = get_guild_language(test_guild)
print(f"Current language: {current_lang}")

# Test some translations
print("\nTesting translations:")
print(f"English 'no_permission': {get_text(123, 'no_permission')}")
print(f"French 'no_permission': {get_text(test_guild, 'no_permission')}")
print(f"English 'raid_enabled': {get_text(123, 'raid_enabled')}")
print(f"French 'raid_enabled': {get_text(test_guild, 'raid_enabled')}")
print(f"English 'warning_issued': {get_text(123, 'warning_issued')}")
print(f"French 'warning_issued': {get_text(test_guild, 'warning_issued')}")

print("\nTranslation test complete!")