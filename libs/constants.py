import enum


class BaseEnum(enum.Enum):
    @classmethod
    def values(cls):
        return [e.value for e in cls]

    @classmethod
    def keys(cls):
        return [e.name for e in cls]


class RoleType(BaseEnum):
    General = 0
    Admin = 1
