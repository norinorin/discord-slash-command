from discord.enums import Enum, try_enum
from discord.utils import _get_as_snowflake
from discord import User, Member


class InteractionType(Enum):
    PING = 1
    APPLICATION_COMMAND = 2


class InteractionResponseType(Enum):
    PONG = 1
    ACKNOWLEDGE = 2
    CHANNEL_MESSAGE = 3
    CHANNEL_MESSAGE_WITH_SOURCE = 4
    DEFFERED_CHANNEL_MESSAGE_WITH_SOURCE = 5

    def __int__(self):
        return self.value


class Interaction:
    def __init__(self, *, state, data):
        self._state = state
        self.id = int(data["id"])
        self.type = try_enum(InteractionType, data["type"])
        self.data = "data" in data and InteractionData(data["data"])
        self.guild_id = _get_as_snowflake(data, "guild_id")
        self.channel_id = _get_as_snowflake(data, "channel_id")
        self.author = (
            (
                "member" in data
                and Member(data=data["member"], guild=guild, state=state)
                if (guild := state._get_guild(self.guild_id))
                else User(state=state, data=data["member"]["user"])
            )
            or "user" in data
            and User(state=state, data=data["user"])
        )
        self.token = data["token"]
        self.version = data["version"]


class _BaseOptions:
    def __init__(self, data):
        self.options = (
            "options" in data
            and [InteractionDataOption(option) for option in data["options"]]
            or []
        )


class InteractionData(_BaseOptions):
    def __init__(self, data):
        super().__init__(data)
        self.id = int(data["id"])
        self.name = data["name"]


class InteractionDataOption(_BaseOptions):
    def __init__(self, data):
        super().__init__(data)
        self.name = data["name"]
        self.value = data.get("value")