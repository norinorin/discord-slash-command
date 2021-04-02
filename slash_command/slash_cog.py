from inspect import getmembers

from .core import SlashCommand


class SlashCog:
    def __init__(self, bot, name=None):
        self.bot = bot
        self.name = name if name is not None else self.__class__.__name__
        self._commands = {}

        for name, command in getmembers(self):
            if not isinstance(command, SlashCommand):
                continue

            command.cog = self
            self._commands[name] = command

    @property
    def commands(self):
        return set(self._commands.values())

    def teardown(self):
        self.bot.slash_cogs.pop(self.name)
        for command in self.commands:
            self.bot.slash_commands.pop(command.name, None)