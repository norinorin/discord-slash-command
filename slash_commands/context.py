from inspect import signature, _empty

import aiohttp
import discord
from discord.http import Route
from discord import utils, Object

from .interaction import InteractionResponseType
from .core import SlashSubCommand, SlashSubCommandGroup


class SlashContext:
    def __init__(self, **kw):
        self.bot = kw["bot"]
        self._state = self.bot._connection
        self.interaction = kw["interaction"]
        self.command = self.bot.get_slash_command(self.interaction.data.name)
        self.invoked_subcommand_group = None
        self.invoked_subcommand = None

    @property
    def author(self):
        return self.interaction.author

    @property
    def guild_id(self):
        return self.interaction.guild_id

    @property
    def guild(self):
        return self.bot.get_guild(self.guild_id) if self.guild_id else None

    @property
    def channel_id(self):
        return self.interaction.channel_id

    @property
    def channel(self):
        return (
            (self.bot.get_channel(self.channel_id) or Object(self.channel_id))
            if self.channel_id
            else None
        )

    def get_command(self, command, options):
        temp_subcommand, temp_subcommand_group = None, None
        for option in options:
            temp_subcommand = command.commands.get(option.name)
            temp_subcommand_group = hasattr(command, "groups") and command.groups.get(
                option.name
            )
            if temp_subcommand or temp_subcommand_group:
                options = option.options
                break

        if temp_subcommand:
            command = self.invoked_subcommand = temp_subcommand
        elif temp_subcommand_group:
            self.invoked_subcommand_group = temp_subcommand_group
            return self.get_command(self.invoked_subcommand_group, options)

        return command, {option.name: option.value for option in options}

    async def invoke(self):
        if not self.command:
            return

        self.bot.dispatch("slash_command", self)
        try:
            command, options = self.get_command(
                self.command, self.interaction.data.options
            )
            parameters = signature(command.callback).parameters

            for option in command.options:
                if option.name not in options:
                    if parameters[option.name].default is _empty:
                        options[option.name] = None
                    continue

                if (val := options[option.name]) is None:
                    continue

                if option.type > 5:
                    # case where the value is a snowflake
                    # since option 6, 7, and 8 return snowflakes
                    options[option.name] = int(val)

            await command(self, **options)

        except Exception as e:
            self.bot.dispatch("slash_command_error", self, e)
        else:
            self.bot.dispatch("slash_command_completion", self)

    def send(
        self,
        content=None,
        *,
        type=InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
        tts=False,
        embed=None,
        embeds=[],
        allowed_mentions=None,
        ephemeral=False,
        file=None,
        files=[],
    ):
        state = self._state
        if embed and embeds:
            raise RuntimeError("Both 'embed' and 'embeds' are specified.")

        if file and files:
            raise RuntimeError("Both 'file' and 'files' are specified.")

        if embed is not None:
            embeds = [embed]

        embeds = [embed.to_dict() for embed in embeds]

        if allowed_mentions is not None:
            if state.allowed_mentions is not None:
                allowed_mentions = state.allowed_mentions.merge(
                    allowed_mentions
                ).to_dict()
            else:
                allowed_mentions = allowed_mentions.to_dict()
        else:
            allowed_mentions = (
                state.allowed_mentions and state.allowed_mentions.to_dict()
            )

        r = Route(
            "POST",
            "/interactions/{interaction.id}/{interaction.token}/callback"
            if type is not None
            else "/webhooks/{application_id}/{interaction.token}",
            interaction=self.interaction,
            application_id=self.bot.user.id,
        )

        if file:
            files = [file]

        json = dict(
            content=content,
            embeds=embeds,
            allowed_mentions=allowed_mentions,
            tts=tts,
        )
        kwargs = {}
        if files:
            form = aiohttp.FormData()
            form.add_field("payload_json", utils.to_json(json))
            multiple_files = len(files) > 1
            for idx, file in enumerate(files):
                name = f"file{idx if multiple_files else ''}"
                form.add_field(
                    name,
                    file.fp,
                    filename=file.filename,
                    content_type="application/octet-stream",
                )
            kwargs["data"] = form
            kwargs["files"] = files
        else:
            json = dict(
                type=int(type),
                data=json,
            )
            if ephemeral:
                json["data"]["flags"] = 64

            kwargs["json"] = json

        try:
            return state.http.request(r, **kwargs)
        finally:
            if files:
                for file in files:
                    file.close()

    def acknowledge(self):
        return self.send(type=InteractionResponseType.ACKNOWLEDGE)