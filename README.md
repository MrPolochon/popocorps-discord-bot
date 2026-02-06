# PopoCorps Discord Bot

Bot Discord sophistiqué avec protection anti-raid, IA conversationnelle, et dashboard web intégré.

## Fonctionnalités

- **Protection Anti-Raid** : Détection de spam en temps réel avec double scan (3+3 secondes)
- **IA Conversationnelle** : Système d'IA avec mémoire persistante utilisant OpenAI GPT-4o-mini
- **Dashboard Web** : Interface de gestion complète avec statistiques en temps réel
- **Système d'Avertissements** : Suivi universel des avertissements multi-bots
- **Messages de Bienvenue** : Système personnalisable avec génération d'images
- **Surveillance 24/7** : Monitoring continu avec reconnexion automatique

## Stack Technique

- **Backend** : Python 3.11, Discord.py, Flask
- **Base de données** : PostgreSQL avec SQLAlchemy
- **IA** : OpenAI API (GPT-4o-mini)
- **Déploiement** : Docker, Railway

## Déploiement Railway

### Prérequis
- Compte Discord Developer avec bot configuré
- Clé API OpenAI
- Compte GitHub
- Compte Railway (gratuit)

### Étapes

1. **Fork ce repository** sur ton GitHub

2. **Configurer le bot Discord** :
   - Aller sur [Discord Developer Portal](https://discord.com/developers/applications)
   - Activer les intents : Message Content, Server Members, Guilds

3. **Déployer sur Railway** :
   - Aller sur [railway.app](https://railway.app)
   - Connecter avec GitHub
   - Sélectionner ce repository
   - Railway détecte automatiquement la configuration

4. **Variables d'environnement** dans Railway :
   ```
   DISCORD_TOKEN=ton_token_discord
   OPENAI_API_KEY=ta_clé_openai
   SESSION_SECRET=clé_secrète_aléatoire
   ```

5. **Base de données** : Railway fournit automatiquement PostgreSQL

### Dashboard Web
Une fois déployé, accède au dashboard sur : `https://[ton-projet].railway.app`

## Déploiement Render

Ce projet inclut un `render.yaml` prêt pour Render.

1. Créer un service Web Render depuis ce repo.
2. Render détecte `render.yaml` et lance `python run.py`.
3. Variables d'environnement à définir dans Render :
   ```
   DISCORD_TOKEN=ton_token_discord
   OPENAI_API_KEY=ta_clé_openai
   SESSION_SECRET=clé_secrète_aléatoire
   DATABASE_URL=postgresql://...
   DISCORD_CLIENT_ID=ton_client_id
   ```

> Render fournit automatiquement `PORT` que le bot utilise pour le dashboard web.

## Lien d'invitation du bot

Le lien d'invitation se génère avec l'ID d'application (Client ID) :

```
DISCORD_CLIENT_ID=ton_client_id python invite_generator.py
```

## Développement local rapide

Si `DATABASE_URL` n'est pas défini, le bot démarre avec une base SQLite locale (`popocorps.db`).

1. Copier le fichier d'exemple :
   ```
   cp .env.example .env
   ```
2. Renseigner au minimum `DISCORD_TOKEN` et `OPENAI_API_KEY`.
3. Lancer le bot :
   ```
   python run.py
   ```

## Commandes Principales

- `/ping` - Test de connectivité
- `/raid on/off/status` - Gestion protection anti-raid
- `/help` - Guide interactif complet
- `/testsystem` - Diagnostic système
- `/setup` - Configuration serveur

## Surveillance 24/7

Le bot inclut :
- Reconnexion automatique infinie
- Monitoring de santé intégré
- Logs détaillés
- Redémarrage automatique en cas de crash

## Support

Le bot maintient une connectivité stable 24/7 avec gestion d'erreurs robuste et reconnexion automatique.

## Licence

Code propriétaire - Utilisation autorisée pour déploiement personnel uniquement.
