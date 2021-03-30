from enum import IntEnum
from inspect import signature
from typing import Any, Awaitable, Callable, Optional

from discord.http import Route

from .slash_cog import SlashCog


def compare_list(a, b):
    b = b.copy()
    try:
        for elem in a:
            b.remove(elem)
    except ValueError:
        return False
    else:
        return not b


class SlashOptionType(IntEnum):
    SUB_COMMAND = 1
    SUB_COMMAND_GROUP = 2
    STRING = 3
    INTEGER = 4
    BOOLEAN = 5
    USER = 6
    CHANNEL = 7
    ROLE = 8


class _GroupMixin:
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.commands = {}
        self.options = []

    def command(self, name=None, cls=None, **attrs):
        cls = SlashSubCommand if cls is None else cls

        def decorator(func):
            nonlocal name
            name = name or func.__name__
            params = list(signature(func).parameters.values())
            if not params:
                raise RuntimeError("Missing 'ctx' parameter")

            attrs["options"] = attrs.get("options") or [
                annotation
                for p in params
                if isinstance((annotation := p.annotation), SlashOption)
            ]
            res = cls(func, self, name, **attrs)
            self.commands[name] = res
            self.options.append(res)
            return res

        return decorator


class _Callable:
    callback: Callable[..., Awaitable[Any]]
    cog: Optional[SlashCog]

    def __call__(self, *args, **kwargs):
        if self.cog:
            args = list(args)
            args.insert(0, self.cog)

        return self.callback(*args, **kwargs)


class SlashCommand(_GroupMixin, _Callable):
    def __init__(
        self,
        callback,
        name=None,
        *,
        id=None,
        application_id=None,
        description,
        options=[],
        cog=None,
    ):
        super().__init__()
        self.callback = callback
        self.id = id
        self.application_id = application_id
        self.name = name if name else callback.__name__
        self.description = description
        self.cog = cog
        self.groups = {}

        params = list(signature(callback).parameters.values())
        if not params:
            raise RuntimeError("Missing 'ctx' parameter")

        self.options = options or [
            annotation
            for p in params
            if isinstance((annotation := p.annotation), SlashOption)
        ]

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return (
            isinstance(other, SlashCommand)
            and self.application_id == other.application_id
            and self.name == other.name
            and self.description == other.description
            and compare_list(self.options, other.options)
        )

    def __hash__(self):
        return hash(self.name)

    def get_route(self, application_id=None):
        application_id = application_id or self.application_id

        if not application_id:
            raise RuntimeError("Missing 'application_id' attribute or parameter")

        if not self.id:
            return Route(
                "POST",
                "/applications/{application_id}/commands",
                application_id=self.application_id,
            )

        return Route(
            "PATCH",
            "/applications/{application_id}/commands/{id}",
            application_id=self.application_id,
            id=self.id,
        )

    def to_dict(self):
        if not self.application_id:
            raise RuntimeError("'application_id' is None")

        d = dict(
            name=self.name,
            application_id=self.application_id,
            description=self.description,
            options=[option.to_dict() for option in self.options],
        )

        if self.id:
            d["id"] = self.id

        return d

    def group(self, name=None, cls=None, **attrs):
        cls = SlashSubCommandGroup if cls is None else cls

        def decorator(func):
            name = name or func.__name__
            params = list(signature(func).parameters.values())
            if not params:
                raise RuntimeError("Missing 'ctx' parameter")

            attrs["options"] = attrs.get("options") or [
                annotation
                for p in params[1:]
                if isinstance((annotation := p.annotation), SlashOption)
            ]
            res = cls(func, self, name, **attrs)
            self.groups[name] = res
            self.options.append(res)
            return res

        return decorator

    @classmethod
    def make_dummy(cls, data):
        name = data["name"]
        description = data["description"]
        id = int(data["id"])
        application_id = int(data["application_id"])
        options = (
            "options" in data
            and [SlashOption.from_json(option) for option in data["options"]]
            or []
        )
        return cls(
            lambda *args: None,
            name,
            id=id,
            application_id=application_id,
            description=description,
            options=options,
        )


class _BaseSlashOption:
    _type = NotImplemented

    def __init__(
        self, name, *, description, required, choices=[], options=[], **kwargs
    ):
        super().__init__(**kwargs)
        self.name = name
        self.description = description
        self.required = required
        self.choices = choices
        self.options = options

    @property
    def type(self):
        return self._type

    def __eq__(self, other):
        return (
            isinstance(other, _BaseSlashOption)
            and self.name == other.name
            and self.required == other.required
            and compare_list(self.choices, other.choices)
            and compare_list(self.options, other.options)
        )

    def to_dict(self):
        d = dict(
            type=int(self.type),
            name=self.name,
            description=self.description,
            required=self.required,
        )

        if self.choices:
            d["choices"] = [choice.to_dict() for choice in self.choices]

        if self.options:
            d["options"] = [option.to_dict() for option in self.options]

        return d

    @classmethod
    def from_json(cls, data):
        name = data["name"]
        description = data["description"]
        required = data.get("required", False)
        choices = (
            "choices" in data
            and [SlashOptionChoice.from_json(choice) for choice in data["choices"]]
            or []
        )
        options = (
            "options" in data
            and [SlashOption.from_json(option) for option in data["options"]]
            or []
        )
        return cls(
            name,
            type=data["type"],
            description=description,
            required=required,
            choices=choices,
            options=options,
        )

    def __str__(self):
        return self.name


class SlashOption(_BaseSlashOption):
    def __init__(self, *args, type: SlashOptionType, **kwargs):
        self._type = type
        super().__init__(*args, **kwargs)

    @classmethod
    def string(cls, *args, **kwargs):
        return cls(type=SlashOptionType.STRING, *args, **kwargs)

    @classmethod
    def integer(cls, *args, **kwargs):
        return cls(type=SlashOptionType.INTEGER, *args, **kwargs)

    @classmethod
    def boolean(cls, *args, **kwargs):
        return cls(type=SlashOptionType.BOOLEAN, *args, **kwargs)

    @classmethod
    def user(cls, *args, **kwargs):
        return cls(type=SlashOptionType.USER, *args, **kwargs)

    @classmethod
    def channel(cls, *args, **kwargs):
        return cls(type=SlashOptionType.CHANNEL, *args, **kwargs)

    @classmethod
    def role(cls, *args, **kwargs):
        return cls(type=SlashOptionType.ROLE, *args, **kwargs)


class _BaseChild(_BaseSlashOption, _Callable):
    def __init__(self, callback, parent, name=None, *args, **kwargs):
        self.callback = callback
        self.parent = parent
        self.name = name or callback.__name__
        super().__init__(name=self.name, *args, **kwargs)

    @property
    def cog(self):
        return self.parent.cog


class SlashSubCommand(_BaseChild):
    _type = SlashOptionType.SUB_COMMAND


class SlashSubCommandGroup(_BaseChild, _GroupMixin):
    _type = SlashOptionType.SUB_COMMAND_GROUP


class SlashOptionChoice:
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def to_dict(self):
        return dict(name=self.name, value=self.value)

    def __eq__(self, other):
        return (
            isinstance(other, SlashOptionChoice)
            and self.name == other.name
            and self.value == other.value
        )

    @classmethod
    def from_json(cls, data):
        name = data["name"]
        value = data["value"]
        return cls(name, value)


def slash_command(name=None, cls=SlashCommand, **attrs):
    def decorator(func):
        return cls(func, name, **attrs)

    return decorator