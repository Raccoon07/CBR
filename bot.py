import asyncio
import discord
from discord.ext import commands

TOKEN = "TON_TOKEN_ICI"  # Ne le partage jamais !

intents = discord.Intents.default()
intents.message_content = True  # À activer aussi dans le portail développeur

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")


# ---------- 1) COOLDOWN : limite l'usage d'une commande ----------
# 1 utilisation toutes les 10 secondes par utilisateur
@bot.command()
@commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
async def ping(ctx):
    await ctx.send("Pong ! 🏓")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Attends encore {error.retry_after:.1f} secondes.")
    else:
        raise error


# ---------- 2) COUNTDOWN : compte à rebours ----------
# Utilisation : !countdown 10
@bot.command()
async def countdown(ctx, secondes: int):
    if secondes < 1 or secondes > 60:
        await ctx.send("Choisis un nombre entre 1 et 60.")
        return

    message = await ctx.send(f"⏳ {secondes}")
    for i in range(secondes - 1, 0, -1):
        await asyncio.sleep(1)
        await message.edit(content=f"⏳ {i}")
    await asyncio.sleep(1)
    await message.edit(content="🎉 Terminé !")


bot.run(TOKEN)
