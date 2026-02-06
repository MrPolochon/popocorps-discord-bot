# Guide de création du repository GitHub

## Étapes pour créer le repository

### 1. Créer le repository sur GitHub
1. Va sur [github.com](https://github.com)
2. Clique sur le bouton vert "New" ou le "+" en haut à droite
3. Nomme le repository : `popocorps-discord-bot`
4. Description : `Bot Discord avec protection anti-raid et IA conversationnelle`
5. Garde-le **Public** (obligatoire pour Railway gratuit)
6. Coche "Add a README file"
7. Choisis `.gitignore template: Python`
8. Clique "Create repository"

### 2. Préparer les fichiers localement
Télécharge depuis Replit tous ces fichiers :

**Fichiers principaux :**
- `main.py` → `run.py`
- `bot.py`
- `app.py`
- `models.py`
- `pyproject.toml`

**Dossier `cogs/` complet :**
- `cogs/ai_chat.py`
- `cogs/audit_logger.py` 
- `cogs/chat_memory.py`
- `cogs/continuous_spam_monitor.py`
- `cogs/help_system.py`
- `cogs/language_config.py`
- `cogs/raid_mode.py`
- `cogs/setup_system.py`
- `cogs/system_test_new.py`
- `cogs/warning_system.py`
- `cogs/welcome_system.py`

**Dossier `utils/` complet :**
- `utils/guild_settings.py`
- `utils/logger.py`
- `utils/permissions.py`
- `utils/spam_detector.py`
- `utils/translations.py`

**Dossier `templates/` complet :**
- `templates/dashboard.html`
- `templates/guilds.html`
- `templates/system_control.html`
- `templates/warnings.html`
- `templates/welcome_config.html`

**Fichiers de déploiement (déjà créés) :**
- `Dockerfile`
- `railway.json`
- `docker-compose.yml`
- `README.md`
- `.gitignore`
- `.env.example`
- `start.sh`
- `RAILWAY_DEPLOYMENT.md`

### 3. Upload sur GitHub
1. Dans ton repository GitHub, clique "uploading an existing file"
2. Glisse-dépose tous les fichiers (ou zip le tout)
3. Écris le commit message : "Initial commit - PopoCorps Discord Bot"
4. Clique "Commit changes"

### 4. Structure finale attendue
```
popocorps-discord-bot/
├── cogs/
├── utils/
├── templates/
├── run.py
├── bot.py
├── app.py
├── models.py
├── pyproject.toml
├── Dockerfile
├── railway.json
├── README.md
└── .env.example
```

### 5. Vérification
- Assure-toi que tous les fichiers sont bien uploadés
- Le repository doit être **Public**
- Le fichier `railway.json` doit être présent à la racine

Une fois fait, on pourra procéder au déploiement Railway !