from discord.http import Route
from discord.ext.commands.bot import BotBase

from .core import SlashCommand, slash_command
from .context import SlashContext
from .interaction import InteractionType, Interaction


class BotPatcher:
    def __init__(self, bot):
        if not isinstance(bot, BotBase):
            raise RuntimeError("'BotBase' subclass is necessary")

        self.bot = bot

    def get_slash_context(self, interaction, *, cls=SlashContext):
        return cls(bot=self.bot, interaction=interaction)

    def add_slash_command(self, slash_command):
        if slash_command.name in self.bot.slash_commands:
            raise RuntimeError(f"{slash_command.name} is a registered slash command.")

        slash_command.application_id = self.bot.user.id
        self.bot.slash_commands[slash_command.name] = slash_command
        return slash_command

    def get_slash_command(self, name):
        return self.bot.slash_commands.get(name)

    def raw_delete_slash_command(self, command_id, guild_id=None):
        url = (
            "applications/{application_id}/commands/{command_id}"
            if not guild_id
            else "applications/{my_application_id}/guilds/{guild_id}/commands/{command_id}"
        )
        r = Route(
            "DELETE",
            url,
            application_id=self.bot.user.id,
            command_id=command_id,
            guild_id=guild_id,
        )
        return self.bot.http.request(r)

    async def delete_slash_command(self, name, *, guild_id=None):
        command = self.bot.slash_commands.pop(name, None)
        if not command:
            raise RuntimeError(f"Slash command {name} wasn't found!")

        if not command.id:
            raise RuntimeError(
                f"Slash command {name}'s ID was missing, make sure to sync it first"
            )

        await self.bot.http.delete_slash_command(command.id, guild_id)
        return command

    def add_slash_cog(self, cog):
        if cog.name in self.bot.slash_cogs:
            raise RuntimeError(f"{cog.name} is a registered slash cog.")

        self.bot.slash_cogs[cog.name] = cog
        for command in cog.commands:
            self.bot.add_slash_command(command)

    def slash_command(self, *args, **kwargs):
        def decorator(func):
            res = slash_command(*args, application_id=self.bot.user.id, **kwargs)(func)
            self.bot.add_slash_command(res)
            return res

        return decorator

    def sync_slash_commands(self):
        return self.put_slash_commands(self.bot.slash_commands.values())

    async def on_slash_command_error(self, ctx, error):
        self.bot.logger.error(
            "Slash command %s raised an error", ctx.command, exc_info=error
        )

    def _remove_module_references(self, name):
        BotBase._remove_module_references(self.bot, name)

        for cog in self.bot.slash_cogs.copy().values():
            if cog.__module__ == name:
                cog.teardown()

    def put_slash_commands(self, commands, guild_id=None):
        r = Route(
            "PUT",
            "/applications/{application_id}/commands"
            if not guild_id
            else "/applications/{application_id}/guilds/{guild_id}/commands",
            application_id=self.bot.user.id,
            guild_id=guild_id,
        )
        return self.bot.http.request(
            r, json=[command.to_dict(with_id=False) for command in commands]
        )

    async def on_socket_response(self, p):
        if not p["t"] == "INTERACTION_CREATE":
            return

        interaction = Interaction(state=self.bot._connection, data=p["d"])

        if interaction.type is not InteractionType.APPLICATION_COMMAND:
            return

        ctx = self.bot.get_slash_context(interaction)
        await ctx.invoke()

    def patch(self, force_override=True):
        attrs = [
            "get_slash_context",
            "get_slash_command",
            "add_slash_cog",
            "add_slash_command",
            "delete_slash_command",
            "slash_command",
            "sync_slash_commands",
            "on_slash_command_error",
            "_remove_module_references",
            "put_slash_commands",
        ]

        for attr in attrs:
            if hasattr(self.bot, attr) and not force_override:
                raise RuntimeError(f"The bot already has {attr} attribute")

            setattr(self.bot, attr, getattr(self, attr))

        for attr in ("slash_commands", "slash_cogs"):
            if hasattr(self.bot, "slash_commands") and not force_override:
                raise RuntimeError(f"The bot already has {attr} attribute")

            setattr(self.bot, attr, {})

        self.bot.http.delete_slash_command = self.raw_delete_slash_command

        self.bot.add_listener(self.on_socket_response)