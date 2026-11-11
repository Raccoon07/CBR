import asyncio
import json
import os
import time

import discord
from discord.ext import commands

TOKEN = "MTU3MDE0MDYwMTQ5MDM1MDM2NA.GXnMj6.8sKsrKp0cS3eOztMnTnf0P6wF8-gqLm97SQX2U"  # Ne le partage jamais !
DUREE = 30 * 60  # 30 minutes (en secondes)
FICHIER = "timers.json"

ACTIVITES = {
    "superette": ("Superette", "🏪"),
    "atm": ("ATM", "🏧"),
    "conteneur": ("Conteneur", "📦"),
    "cambriolage": ("Cambriolage", "🏠"),
}

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

taches = set()  # garde une référence aux timers en cours


# ---------- Sauvegarde (pour survivre à un redémarrage) ----------
def charger():
    if os.path.exists(FICHIER):
        with open(FICHIER, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"timers": {}, "panel": None}


def sauvegarder():
    with open(FICHIER, "w", encoding="utf-8") as f:
        json.dump(etat, f)


etat = charger()


# ---------- Affichage ----------
def construire_embed():
    embed = discord.Embed(
        title="🚨 Suivi des activités",
        description="Clique sur un bouton pour lancer le timer de 30 minutes.",
        color=discord.Color.blurple(),
    )
    maintenant = time.time()
    for cle, (nom, emoji) in ACTIVITES.items():
        fin = etat["timers"].get(cle, 0)
        if fin > maintenant:
            valeur = f"⏳ Disponible <t:{int(fin)}:R>"
        else:
            valeur = "✅ Disponible"
        embed.add_field(name=f"{emoji} {nom}", value=valeur, inline=False)
    return embed


async def rafraichir_panneau():
    panneau = etat.get("panel")
    if not panneau:
        return
    try:
        salon = bot.get_channel(panneau["channel"]) or await bot.fetch_channel(panneau["channel"])
        message = await salon.fetch_message(panneau["message"])
        await message.edit(embed=construire_embed())
    except discord.HTTPException:
        pass


# ---------- Timers ----------
async def attendre_fin(cle):
    fin = etat["timers"].get(cle, 0)
    await asyncio.sleep(max(0, fin - time.time()))
    if etat["timers"].get(cle) != fin:  # timer relancé entre-temps
        return
    nom, emoji = ACTIVITES[cle]
    await rafraichir_panneau()
    panneau = etat.get("panel")
    if panneau:
        salon = bot.get_channel(panneau["channel"])
        if salon:
            await salon.send(f"✅ {emoji} **{nom}** est de nouveau disponible !")


def lancer_timer(cle):
    tache = asyncio.create_task(attendre_fin(cle))
    taches.add(tache)
    tache.add_done_callback(taches.discard)


# ---------- Boutons ----------
class BoutonActivite(discord.ui.Button):
    def __init__(self, cle):
        nom, emoji = ACTIVITES[cle]
        super().__init__(
            label=nom,
            emoji=emoji,
            style=discord.ButtonStyle.primary,
            custom_id=f"activite:{cle}",
        )
        self.cle = cle

    async def callback(self, interaction: discord.Interaction):
        nom, _ = ACTIVITES[self.cle]
        fin = etat["timers"].get(self.cle, 0)
        if fin > time.time():
            await interaction.response.send_message(
                f"⏳ **{nom}** est déjà en cours, disponible <t:{int(fin)}:R>.",
                ephemeral=True,
            )
            return

        etat["timers"][self.cle] = time.time() + DUREE
        sauvegarder()
        await interaction.response.edit_message(embed=construire_embed())
        lancer_timer(self.cle)


class PanneauView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # vue persistante
        for cle in ACTIVITES:
            self.add_item(BoutonActivite(cle))


# ---------- Bot ----------
@bot.event
async def setup_hook():
    bot.add_view(PanneauView())


@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")
    # Relance les timers restants après un redémarrage
    for cle, fin in etat["timers"].items():
        if fin > time.time():
            lancer_timer(cle)


@bot.command()
@commands.has_permissions(manage_guild=True)
async def panneau(ctx):
    """Poste le panneau de boutons dans ce salon."""
    message = await ctx.send(embed=construire_embed(), view=PanneauView())
    etat["panel"] = {"channel": ctx.channel.id, "message": message.id}
    sauvegarder()


bot.run(TOKEN)
