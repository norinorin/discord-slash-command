import random

import discord

import slash_command


class SlashTest(slash_command.SlashCog):
    def __init__(self, bot):
        super().__init__(bot)

    @staticmethod
    def get_gay_rate():
        return random.randint(0, 201)

    @slash_command.slash_command(description="A Test!")
    async def test(self, ctx):
        await ctx.send("Tested!")

    @slash_command.slash_command(description="The gay command.")
    async def gay(self, ctx):
        ...  # just make an entry for the sub commands
        # as it's pretty much useless to implement something here
        # since this won't show up when using slash commands

    @gay.command(description="See how gay someone is.", required=False)
    async def user(
        self,
        ctx,
        user: slash_command.SlashOption(
            "user",
            type=slash_command.SlashOptionType.USER,
            description="The user",
            required=False,
        ),
    ):
        if user:
            user = self.bot.get_user(user) or await self.bot.fetch_user(user)
            return await ctx.send(f"{user} is {self.get_gay_rate()}% gay!")

        await ctx.send(f"You're {self.get_gay_rate()}% gay!")

    @gay.command(description="See how gay a random user is.", required=False)
    async def random(self, ctx):
        if not ctx.guild_id:
            return await ctx.send(
                "This is a guild-only command"  # maybe implement a decorator some day?
            )  # or I can make it so that it's compatible with discord.py's decorators :thonk:

        guild = self.bot.get_guild(ctx.guild_id)
        user_id = random.choice(guild._partial_members)
        user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
        await ctx.send(f"{user} is {self.get_gay_rate()}% gay!")


def setup(bot):
    bot.add_slash_cog(SlashTest(bot))