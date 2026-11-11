import json
import os
import time

import discord
from discord import app_commands
from discord.ext import commands, tasks

TOKEN = os.environ["DISCORD_TOKEN"]
GUILD_ID = os.environ.get("GUILD_ID")  # optionnel : sync instantanée des commandes
COOLDOWN = 30 * 60  # 30 minutes
STATE_FILE = "state.json"

# clé -> (emoji, titre affiché)
CATEGORIES = {
    "superette": ("🏪", "SUPÉRETTE"),
    "atm": ("🏧", "ATM"),
    "conteneur": ("📦", "CONTENEUR"),
    "cambriolage": ("🏠", "CAMBRIOLAGE"),
}


# ---------- Sauvegarde (survit aux redémarrages) ----------
def load_state() -> dict:
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f)


# ---------- Affichage ----------
def build_embed(key: str, entry: dict) -> discord.Embed:
    emoji, title = CATEGORIES[key]
    ends_at = entry.get("ends_at")
    if ends_at and ends_at > time.time():
        embed = discord.Embed(
            title=f"{emoji} {title}",
            description=(
                f"🔴 **En cooldown**\n"
                f"Disponible <t:{int(ends_at)}:R> (à <t:{int(ends_at)}:t>)"
            ),
            color=discord.Color.red(),
        )
        if entry.get("by"):
            embed.set_footer(text=f"Lancé par {entry['by_name']}")
    else:
        embed = discord.Embed(
            title=f"{emoji} {title}",
            description="🟢 **Disponible**",
            color=discord.Color.green(),
        )
    return embed


class CooldownButton(discord.ui.Button):
    def __init__(self, key: str, disabled: bool = False):
        emoji, title = CATEGORIES[key]
        super().__init__(
            label=f"Lancer {title}",
            emoji=emoji,
            style=discord.ButtonStyle.danger if disabled else discord.ButtonStyle.success,
            custom_id=f"cd:{key}",  # nécessaire pour que le bouton marche après redémarrage
            disabled=disabled,
        )
        self.key = key

    async def callback(self, interaction: discord.Interaction):
        state = load_state()
        entry = state.get(str(interaction.message.id))
        if entry is None:
            return await interaction.response.send_message(
                "Ce panneau est inconnu, refais /panel.", ephemeral=True
            )
        if entry.get("ends_at") and entry["ends_at"] > time.time():
            return await interaction.response.send_message(
                "⏳ Déjà en cooldown !", ephemeral=True
            )

        entry["ends_at"] = time.time() + COOLDOWN
        entry["by"] = interaction.user.id
        entry["by_name"] = interaction.user.display_name
        save_state(state)

        await interaction.response.edit_message(
            embed=build_embed(self.key, entry),
            view=build_view(self.key, disabled=True),
        )


def build_view(key: str, disabled: bool = False) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    view.add_item(CooldownButton(key, disabled))
    return view


# ---------- Bot ----------
class CooldownBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.default())

    async def setup_hook(self):
        # Réenregistre les boutons pour qu'ils fonctionnent après un redémarrage
        for key in CATEGORIES:
            self.add_view(build_view(key))

        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()

        self.check_cooldowns.start()

    @tasks.loop(seconds=10)
    async def check_cooldowns(self):
        state = load_state()
        changed = False
        for message_id, entry in list(state.items()):
            ends_at = entry.get("ends_at")
            if not ends_at or ends_at > time.time():
                continue
            entry["ends_at"] = None
            changed = True
            try:
                channel = self.get_channel(entry["channel_id"]) or await self.fetch_channel(
                    entry["channel_id"]
                )
                message = await channel.fetch_message(int(message_id))
                await message.edit(
                    embed=build_embed(entry["key"], entry),
                    view=build_view(entry["key"]),
                )
                await channel.send(
                    f"✅ **{CATEGORIES[entry['key']][1]}** est de nouveau disponible !",
                    delete_after=60,
                )
            except discord.NotFound:
                state.pop(message_id, None)  # message supprimé
            except discord.HTTPException:
                pass
        if changed:
            save_state(state)

    @check_cooldowns.before_loop
    async def before_check(self):
        await self.wait_until_ready()


bot = CooldownBot()


@bot.tree.command(name="panel", description="Poste les panneaux de cooldown")
@app_commands.default_permissions(administrator=True)
async def panel(interaction: discord.Interaction):
    await interaction.response.send_message("Panneaux créés ✅", ephemeral=True)
    state = load_state()
    for key in CATEGORIES:
        entry = {"key": key, "channel_id": interaction.channel_id, "ends_at": None}
        msg = await interaction.channel.send(
            embed=build_embed(key, entry), view=build_view(key)
        )
        state[str(msg.id)] = entry
    save_state(state)


@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")


bot.run(TOKEN)
