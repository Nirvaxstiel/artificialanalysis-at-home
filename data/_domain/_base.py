from enum import Enum
from typing import Any


class DomainValue:
    def as_primitive(self) -> Any:
        name = next(iter(self.__dataclass_fields__))
        return getattr(self, name)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.as_primitive()!r})"


class ModelType(str, Enum):
    CHAT = "chat"
    REASONING = "reasoning"


class Provenance(str, Enum):
    SOURCED = "sourced"
    DERIVED = "derived"


class Direction(str, Enum):
    HIGHER_IS_BETTER = "higher_is_better"
    LOWER_IS_BETTER = "lower_is_better"


class AxisCategory(str, Enum):
    PERFORMANCE = "performance"
    PRICING = "pricing"
    QUALITY = "quality"
    META = "meta"


class Archetype(str, Enum):
    FRONTIER = "frontier"
    CHEAP = "cheap"
    REASONING = "reasoning"
    FAST = "fast"
    COMPACT = "compact"
    UNCATEGORIZED = "uncategorized"

    @classmethod
    def _missing_(cls, value):
        return cls.UNCATEGORIZED


class SourceKey(str, Enum):
    AA = "aa"
    AA_IMG = "aa_img"
    LIVEBENCH = "livebench"
    ARENA_CODE = "arena_code"
    ARENA_TEXT = "arena_text"
    OPENLLM = "openllm"
    OPENROUTER = "openrouter"
    COST_BREAKDOWN = "cost_breakdown"
