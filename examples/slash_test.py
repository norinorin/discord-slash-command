import random
from io import BytesIO

import discord

import slash_commands


class SlashTest(slash_commands.SlashCog):
    def __init__(self, bot):
        super().__init__(bot)

    @staticmethod
    def get_gay_rate():
        return random.randint(0, 201)

    @slash_commands.slash_command(description="A Test!")
    async def test(self, ctx):
        await ctx.send("Tested!")

    @slash_commands.slash_command(description="The gay command.")
    async def gay(self, ctx):
        ...  # just make an entry for the sub commands
        # as it's pretty much useless to implement something here
        # since this won't show up when using slash commands

    @gay.command(description="See how gay someone is.")
    async def user(
        self,
        ctx,
        user: slash_commands.SlashOption.user("user", description="The user"),
    ):
        if user:
            user = self.bot.get_user(user) or await self.bot.fetch_user(user)
            return await ctx.send(f"{user} is {self.get_gay_rate()}% gay!")

        await ctx.send(f"You're {self.get_gay_rate()}% gay!")

    @gay.command(description="See how gay a random user is.")
    async def random(self, ctx):
        if not ctx.guild_id:
            return await ctx.send(
                "This is a guild-only command"  # maybe implement a decorator some day?
            )  # or I can make it so that it's compatible with discord.py's decorators :thonk:

        # _partial_members is my own thing, it's just an array of member IDs
        user_id = random.choice(ctx.guild._partial_members)
        user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
        await ctx.send(f"{user} is {self.get_gay_rate()}% gay!")

    @slash_commands.slash_command(description="Sends a spotify card")
    async def spotify(
        self,
        ctx,
        user: slash_commands.SlashOption.user("user", description="The user"),
        hidden: slash_commands.SlashOption.boolean(
            "hidden", description="Hide the progress bar"
        ) = False,
        style: slash_commands.SlashOption.string(
            "style",
            description="The style",
            choices=[
                slash_commands.SlashOptionChoice("1", value="1"),
                slash_commands.SlashOptionChoice("2", value="2"),
            ],
        ) = "2",
    ):
        # again, this is my own thing, the purpose of this example
        # is to show how you can add options, choices and whatnot
        images = self.bot.get_cog("Images")
        member = user or ctx.author.id
        spotify = (spotify := self.bot._presences.get(member)) and spotify[0]
        if not spotify:
            n = "You" if member == ctx.author.id else "They"
            return await ctx.send(f"{n} have no Spotify activity")

        # send the initial response
        await ctx.send("Creating the card...")

        with BytesIO() as image:
            (
                timestamp,
                album_url,
                artists,
                title,
                album_title,
            ) = await images._get_data(spotify, ctx.author)
            im = await images._get_spotify_card(
                style,
                album_url,
                artists,
                title,
                album_title,
                not isinstance(spotify, discord.Spotify),
                bool(hidden),
                None,
                timestamp=timestamp,
            )
            im.save(image, "PNG")
            image.seek(0)

            # send the actual card
            await ctx.send(
                type=None,
                file=discord.File(fp=image, filename=f"{member}-card.png"),
            )


def setup(bot):
    bot.add_slash_cog(SlashTest(bot))