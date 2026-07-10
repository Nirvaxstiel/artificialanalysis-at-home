from dataclasses import dataclass
from typing import Optional

from ._base import DomainValue


@dataclass(frozen=True)
class PricePerMToken(DomainValue):
    usd: float

    def __post_init__(self):
        if self.usd < 0:
            raise ValueError(f"Negative price per M tokens: {self.usd}")

    def as_per_token(self) -> float:
        return self.usd / 1_000_000

    def __mul__(self, other: float) -> 'PricePerMToken':
        return PricePerMToken(self.usd * other)

    def __truediv__(self, other: float) -> 'PricePerMToken':
        return PricePerMToken(self.usd / other)


@dataclass(frozen=True)
class PricePerToken(DomainValue):
    usd: float

    def __post_init__(self):
        if self.usd < 0:
            raise ValueError(f"Negative price per token: {self.usd}")

    def as_per_m(self) -> PricePerMToken:
        return PricePerMToken(self.usd * 1_000_000)


@dataclass(frozen=True)
class CostPerTask(DomainValue):
    usd: float

    def __post_init__(self):
        if self.usd < 0:
            raise ValueError(f"Negative cost per task: {self.usd}")


@dataclass(frozen=True)
class TokensPerTask(DomainValue):
    mtok: float

    def __post_init__(self):
        if self.mtok <= 0:
            raise ValueError(f"Non-positive tokens per task: {self.mtok}")


@dataclass(frozen=True)
class TokensPerSecond(DomainValue):
    tps: float

    def __post_init__(self):
        if self.tps < 0:
            raise ValueError(f"Negative tokens per second: {self.tps}")


@dataclass(frozen=True)
class TimeToFirstToken(DomainValue):
    seconds: float

    def __post_init__(self):
        if self.seconds < 0:
            raise ValueError(f"Negative TTFT: {self.seconds}")


@dataclass(frozen=True)
class UsefulCost(DomainValue):
    usd: float

    def __post_init__(self):
        if self.usd < 0:
            raise ValueError(f"Negative useful cost: {self.usd}")


@dataclass(frozen=True)
class ReasoningTaxPct(DomainValue):
    pct: float

    def __post_init__(self):
        if self.pct < 0:
            raise ValueError(f"Negative reasoning tax: {self.pct}")


@dataclass(frozen=True)
class CacheHitRate(DomainValue):
    pct: float

    def __post_init__(self):
        if not (0 <= self.pct <= 100):
            raise ValueError(f"Cache hit rate out of [0, 100]: {self.pct}")


@dataclass(frozen=True)
class CostSegment(DomainValue):
    usd: float

    def __post_init__(self):
        if self.usd < 0:
            raise ValueError(f"Negative cost segment: {self.usd}")


@dataclass(frozen=True)
class IntelligenceScore(DomainValue):
    value: float

    def __post_init__(self):
        if not (0 <= self.value <= 100):
            raise ValueError(f"Intelligence score out of [0, 100]: {self.value}")


@dataclass(frozen=True)
class Elo(DomainValue):
    score: float

    def __post_init__(self):
        if self.score < 0:
            raise ValueError(f"Negative Elo: {self.score}")


@dataclass(frozen=True)
class CIMargin(DomainValue):
    margin: float

    def __post_init__(self):
        if self.margin < 0:
            raise ValueError(f"Negative CI margin: {self.margin}")


@dataclass(frozen=True)
class VoteCount(DomainValue):
    count: int

    def __post_init__(self):
        if self.count < 0:
            raise ValueError(f"Negative vote count: {self.count}")

    def as_primitive(self) -> int:
        return self.count


@dataclass(frozen=True)
class BenchmarkScore(DomainValue):
    score: float

    def __post_init__(self):
        if not (0 <= self.score <= 100):
            raise ValueError(f"Benchmark score out of [0, 100]: {self.score}")


@dataclass(frozen=True)
class IQ_PerMToken(DomainValue):
    value: float

    def as_primitive(self) -> float:
        return self.value


@dataclass(frozen=True)
class IQ_PerMTokenDollar(DomainValue):
    value: float

    def as_primitive(self) -> float:
        return self.value


@dataclass(frozen=True)
class IQ_PerDollarPoint(DomainValue):
    value: float

    def as_primitive(self) -> float:
        return self.value


@dataclass(frozen=True)
class CostPerIQPoint(DomainValue):
    usd_per_iq: float

    def __post_init__(self):
        if self.usd_per_iq < 0:
            raise ValueError(f"Negative cost per IQ point: {self.usd_per_iq}")


@dataclass(frozen=True)
class ParameterCount(DomainValue):
    b: float

    def __post_init__(self):
        if self.b <= 0:
            raise ValueError(f"Non-positive parameter count: {self.b}")


@dataclass(frozen=True)
class CarbonKg(DomainValue):
    kg: float

    def __post_init__(self):
        if self.kg < 0:
            raise ValueError(f"Negative CO₂: {self.kg}")


@dataclass(frozen=True)
class ContextWindow(DomainValue):
    tokens: int

    def __post_init__(self):
        if self.tokens <= 0:
            raise ValueError(f"Context window must be positive: {self.tokens}")


@dataclass(frozen=True)
class Percentile(DomainValue):
    pct: float

    def __post_init__(self):
        if not (0 <= self.pct <= 100):
            raise ValueError(f"Percentile out of [0, 100]: {self.pct}")


@dataclass(frozen=True)
class Count(DomainValue):
    value: int

    def __post_init__(self):
        if self.value < 0:
            raise ValueError(f"Negative count: {self.value}")

    def as_primitive(self) -> int:
        return self.value
