# Déploiement PopoCorps Bot sur Railway

## Étapes de déploiement

### 1. Préparation du repository
- Créer un repository GitHub avec tous les fichiers du bot
- S'assurer que `railway.json`, `Dockerfile` et `pyproject.toml` sont présents

### 2. Configuration Railway
1. Aller sur [railway.app](https://railway.app)
2. Se connecter avec GitHub
3. Cliquer "New Project" → "Deploy from GitHub repo"
4. Sélectionner le repository du bot

### 3. Variables d'environnement requises
Dans Railway, aller dans Settings → Variables et ajouter :

```
DISCORD_TOKEN=ton_token_discord_ici
OPENAI_API_KEY=ta_clé_openai_ici
DATABASE_URL=postgresql://railway_fourni_automatiquement
SESSION_SECRET=une_clé_secrète_aléatoire
```

### 4. Configuration automatique
Railway détecte automatiquement :
- Le Dockerfile pour la conteneurisation
- Le port 5000 pour le dashboard web
- Les dépendances Python depuis pyproject.toml

### 5. Déploiement
- Railway déploie automatiquement à chaque push sur la branche main
- Le bot redémarre automatiquement en cas de crash
- Logs accessibles en temps réel dans l'interface Railway

### 6. Monitoring
- URL du dashboard : `https://[nom-projet].railway.app`
- Logs du bot visibles dans l'onglet "Deployments"
- Métriques de performance disponibles

## Avantages Railway
- 500h gratuites/mois (largement suffisant)
- Redémarrage automatique 24/7
- Base de données PostgreSQL incluse
- SSL/TLS automatique
- Déploiement continu depuis GitHub

## Support
Le bot inclut :
- Système de reconnexion infinie
- Monitoring de santé intégré
- Dashboard web accessible
- Logs détaillés pour debugging

Une fois déployé, le bot maintiendra une connectivité 24/7 sans intervention.