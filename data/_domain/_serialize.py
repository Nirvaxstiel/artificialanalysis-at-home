from dataclasses import fields
from enum import Enum
from typing import Any, Optional

from ._base import Archetype, DomainValue, ModelType, Provenance
from ._values import (
    PricePerMToken, PricePerToken, CostPerTask, TokensPerTask,
    TokensPerSecond, TimeToFirstToken,
    UsefulCost, ReasoningTaxPct, CacheHitRate, CostSegment,
    IntelligenceScore, IQ_PerDollarPoint, IQ_PerMToken, IQ_PerMTokenDollar,
    Elo, CIMargin, VoteCount, BenchmarkScore,
    ParameterCount, CarbonKg, ContextWindow, Percentile,
    ResponseTime, OmniscienceIndex, AxisMetric,
)


def to_primitive(obj: Any) -> Any:
    if obj is None:
        return None
    if isinstance(obj, DomainValue):
        return obj.as_primitive()
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [to_primitive(v) for v in obj]
    if isinstance(obj, dict):
        return {k: to_primitive(v) for k, v in obj.items()}
    if hasattr(obj, '__dataclass_fields__'):
        return {f.name: to_primitive(getattr(obj, f.name)) for f in fields(obj)}
    return obj


def _is_valid(v):
    if v is None:
        return False
    if isinstance(v, float) and v != v:
        return False
    return True


def safe_float(v) -> Optional[float]:
    return v if _is_valid(v) else None


def safe_int(v) -> Optional[int]:
    if not _is_valid(v):
        return None
    return int(v)


def try_model_type(v) -> Optional[ModelType]:
    if not _is_valid(v):
        return None
    try:
        return ModelType(str(v).lower())
    except (ValueError, AttributeError):
        return None


def try_archetype(v) -> Archetype:
    if not _is_valid(v):
        return Archetype.UNCATEGORIZED
    try:
        return Archetype(str(v).lower())
    except (ValueError, AttributeError):
        return Archetype.UNCATEGORIZED


def safe_ppm(v) -> Optional[PricePerMToken]:
    v = safe_float(v)
    return PricePerMToken(v) if v is not None else None


def safe_ppt(v) -> Optional[PricePerToken]:
    v = safe_float(v)
    return PricePerToken(v) if v is not None else None


def safe_cost(v) -> Optional[CostPerTask]:
    v = safe_float(v)
    return CostPerTask(v) if v is not None else None


def safe_tok_per_task(v) -> Optional[TokensPerTask]:
    v = safe_float(v)
    return TokensPerTask(v) if v is not None else None


def safe_tps(v) -> Optional[TokensPerSecond]:
    v = safe_float(v)
    return TokensPerSecond(v) if v is not None else None


def safe_ttft(v) -> Optional[TimeToFirstToken]:
    v = safe_float(v)
    return TimeToFirstToken(v) if v is not None else None


def safe_axis_metric(v) -> Optional[AxisMetric]:
    v = safe_float(v)
    return AxisMetric(v) if v is not None else None


def safe_useful_cost(v) -> Optional[UsefulCost]:
    v = safe_float(v)
    return UsefulCost(v) if v is not None else None


def safe_reasoning_tax(v) -> Optional[ReasoningTaxPct]:
    v = safe_float(v)
    return ReasoningTaxPct(v) if v is not None else None


def safe_cache(v) -> Optional[CacheHitRate]:
    v = safe_float(v)
    return CacheHitRate(v) if v is not None else None


def safe_cost_segment(v) -> Optional[CostSegment]:
    v = safe_float(v)
    return CostSegment(v) if v is not None else None


def safe_intel(v) -> Optional[IntelligenceScore]:
    v = safe_float(v)
    return IntelligenceScore(v) if v is not None else None


def safe_elo(v) -> Optional[Elo]:
    v = safe_float(v)
    return Elo(v) if v is not None else None


def safe_ci(v) -> Optional[CIMargin]:
    v = safe_float(v)
    return CIMargin(v) if v is not None else None


def safe_votes(v) -> Optional[VoteCount]:
    v = safe_int(v)
    return VoteCount(v) if v is not None else None


def safe_benchmark(v) -> Optional[BenchmarkScore]:
    v = safe_float(v)
    return BenchmarkScore(v) if v is not None else None


def safe_iq_per_mtok(v) -> Optional[IQ_PerMToken]:
    v = safe_float(v)
    return IQ_PerMToken(v) if v is not None else None


def safe_iq_per_mtokdollar(v) -> Optional[IQ_PerMTokenDollar]:
    v = safe_float(v)
    return IQ_PerMTokenDollar(v) if v is not None else None


def safe_iq_per_dollar(v) -> Optional[IQ_PerDollarPoint]:
    v = safe_float(v)
    return IQ_PerDollarPoint(v) if v is not None else None


def safe_params(v) -> Optional[ParameterCount]:
    v = safe_float(v)
    return ParameterCount(v) if v is not None else None


def safe_carbon(v) -> Optional[CarbonKg]:
    v = safe_float(v)
    return CarbonKg(v) if v is not None else None


def safe_ctx_window(v) -> Optional[ContextWindow]:
    if v is None:
        return None
    try:
        tokens = int(v)
    except (TypeError, ValueError):
        return None
    if tokens <= 0:
        return None
    return ContextWindow(tokens)


def safe_pct(v) -> Optional[Percentile]:
    v = safe_float(v)
    return Percentile(v) if v is not None else None


def safe_omniscience(v) -> Optional[OmniscienceIndex]:
    v = safe_float(v)
    return OmniscienceIndex(v) if v is not None else None


def safe_response_time(v) -> Optional[ResponseTime]:
    v = safe_float(v)
    return ResponseTime(v) if v is not None else None
