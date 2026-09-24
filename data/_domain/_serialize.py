from dataclasses import fields
from enum import Enum
from math import isfinite
from typing import Any, Optional

from _result import Err, Ok, ok, err
from ._base import DomainValue, ModelType, Provenance
from ._values import (
    PricePerMToken, PricePerToken, CostPerTask, TokensPerSecond,
    ReasoningTaxPct, CacheHitRate, CostSegment, IntelligenceScore,
    Elo, CIMargin, VoteCount, BenchmarkScore, ParameterCount, CarbonKg,
    ContextWindow, ResponseTime, OmniscienceIndex,
    FinanceAccountingIndex, PassRate,
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





def safe_ppm(v) -> Optional[PricePerMToken]:
    v = safe_float(v)
    return PricePerMToken(v) if v is not None else None


def safe_ppt(v) -> Optional[PricePerToken]:
    v = safe_float(v)
    return PricePerToken(v) if v is not None else None


def safe_cost(v) -> Optional[CostPerTask]:
    v = safe_float(v)
    return CostPerTask(v) if v is not None else None





def safe_tps(v) -> Optional[TokensPerSecond]:
    v = safe_float(v)
    return TokensPerSecond(v) if v is not None else None











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





def safe_params(v) -> Optional[ParameterCount]:
    v = safe_float(v)
    if v is None or v <= 0:
        return None
    return ParameterCount(v)


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





def safe_omniscience(v) -> Ok[Optional[OmniscienceIndex]] | Err[str]:
    if v is None:
        return ok(None)
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return err("Omniscience index must be numeric")
    value = float(v)
    if not isfinite(value) or not -100 <= value <= 100:
        return err(f"Omniscience index out of [-100, 100]: {v}")
    return ok(OmniscienceIndex(value))


def safe_finance_accounting_index(v) -> Ok[Optional[FinanceAccountingIndex]] | Err[str]:
    if v is None:
        return ok(None)
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return err("Finance & Accounting Index must be numeric")
    score = float(v)
    if not isfinite(score) or not 0 <= score <= 100:
        return err(f"Finance & Accounting Index out of [0, 100]: {v}")
    return ok(FinanceAccountingIndex(score))


def safe_pass_rate(v) -> Ok[Optional[PassRate]] | Err[str]:
    if v is None:
        return ok(None)
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return err("Pass rate must be a numeric fraction")
    ratio = float(v)
    if not isfinite(ratio) or not 0 <= ratio <= 1:
        return err(f"Pass rate out of [0, 1]: {v}")
    return ok(PassRate(ratio))


def safe_response_time(v) -> Ok[Optional[ResponseTime]] | Err[str]:
    if v is None:
        return ok(None)
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return err("Time per task must be numeric seconds")
    seconds = float(v)
    if not isfinite(seconds) or seconds < 0:
        return err(f"Time per task must be finite and non-negative: {v}")
    return ok(ResponseTime(seconds))
