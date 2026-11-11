# Bot Discord – Cooldowns (Supérette / ATM / Conteneur / Cambriolage)

Chaque panneau a un bouton : un clic lance un timer de 30 min, le bouton se
désactive, puis le panneau repasse en "Disponible" à la fin.

## Variables d'environnement
- `DISCORD_TOKEN` : token du bot (obligatoire)
- `GUILD_ID` : ID de ton serveur (optionnel, sync instantanée des commandes)

## Lancer en local
```
pip install -r requirements.txt
export DISCORD_TOKEN="ton_token"
python bot.py
```
Puis, sur Discord, tape `/panel` dans le salon voulu (admin requis).
