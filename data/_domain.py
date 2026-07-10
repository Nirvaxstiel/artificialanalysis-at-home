import re
from dataclasses import dataclass, field, fields
from datetime import date
from enum import Enum
from typing import Any, ClassVar, Dict, List, Optional, Tuple


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
    LIVEBENCH = "livebench"
    ARENA_CODE = "arena_code"
    ARENA_TEXT = "arena_text"
    OPENLLM = "openllm"
    OPENROUTER = "openrouter"
    COST_BREAKDOWN = "cost_breakdown"


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


def safe_ttft(v) -> Optional[TimeToFirstToken]:
    v = safe_float(v)
    return TimeToFirstToken(v) if v is not None else None


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

    def as_primitive(self) -> Any:
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


@dataclass(frozen=True)
class Axis:
    id: str
    name: str
    source: SourceKey
    category: AxisCategory
    datatype: str
    direction: Direction
    unit: Optional[str] = None
    range: Optional[Tuple[float, float]] = None
    description: str = ""
    models_have: int = 0
    group: str = ""

    def __post_init__(self):
        if not re.match(r'^[a-zA-Z_][\w]*\.[a-zA-Z_][\w.]*$', self.id):
            raise ValueError(f"Invalid axis ID format: {self.id}")
        if self.models_have < 0:
            raise ValueError(f"Negative models_have: {self.models_have}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.name,
            "source": self.source.value,
            "type": self.category.value,
            "unit": self.unit,
            "higher_is_better": self.direction == Direction.HIGHER_IS_BETTER,
            "description": self.description,
            "models_have": self.models_have,
            "range": list(self.range) if self.range else None,
            "group": self.group,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'Axis':
        return cls(
            id=d["id"],
            name=d.get("label", d["id"]),
            source=SourceKey(d["source"].lower().replace(" ", "_")),
            category=AxisCategory(d["type"]),
            datatype=d.get("datatype", "float"),
            direction=Direction.HIGHER_IS_BETTER if d.get("higher_is_better", True) else Direction.LOWER_IS_BETTER,
            unit=d.get("unit"),
            range=tuple(d["range"]) if d.get("range") else None,
            description=d.get("description", ""),
            models_have=d.get("models_have", 0),
            group=d.get("group", ""),
        )


# ═══════════════════════════════════════════════════════════════
# Entity — Pricing records (per source, sealed)
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class AAPricing:
    inp_price: PricePerMToken
    out_price: PricePerMToken
    blended: PricePerMToken
    cost_per_task: CostPerTask
    tokens_m: TokensPerTask
    speed_tps: TokensPerSecond
    useful_cost: Optional[UsefulCost] = None
    reasoning_tax_pct: Optional[ReasoningTaxPct] = None
    cache: Optional[CacheHitRate] = None
    cost_segments: Optional['CostBreakdownPricing'] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "inp_price": self.inp_price.as_primitive(),
            "out_price": self.out_price.as_primitive(),
            "blended": self.blended.as_primitive(),
            "cost_per_task": self.cost_per_task.as_primitive(),
            "tokens_m": self.tokens_m.as_primitive(),
            "speed_tps": self.speed_tps.as_primitive(),
        }
        if self.useful_cost is not None:
            d["useful_cost"] = self.useful_cost.as_primitive()
        if self.reasoning_tax_pct is not None:
            d["reasoning_tax_pct"] = self.reasoning_tax_pct.as_primitive()
        if self.cache is not None:
            d["cache"] = self.cache.as_primitive()
        if self.cost_segments is not None:
            d["cost_segments"] = self.cost_segments.to_dict()
        return d


@dataclass(frozen=True)
class CostBreakdownPricing:
    total_cost_per_task_usd: CostSegment
    answer_usd: CostSegment
    reasoning_usd: CostSegment
    cache_write_usd: CostSegment
    cache_hit_usd: CostSegment
    input_usd: CostSegment

    def to_dict(self) -> Dict[str, float]:
        return {
            "total_cost_per_task_usd": self.total_cost_per_task_usd.as_primitive(),
            "answer_usd": self.answer_usd.as_primitive(),
            "reasoning_usd": self.reasoning_usd.as_primitive(),
            "cache_write_usd": self.cache_write_usd.as_primitive(),
            "cache_hit_usd": self.cache_hit_usd.as_primitive(),
            "input_usd": self.input_usd.as_primitive(),
        }


@dataclass(frozen=True)
class OpenRouterPricing:
    inp_price: PricePerToken
    inp_price_per_m: PricePerMToken
    out_price: PricePerToken
    out_price_per_m: PricePerMToken
    cache_read_price: Optional[PricePerToken] = None
    cache_read_price_per_m: Optional[PricePerMToken] = None
    vendor: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "inp_price": self.inp_price.as_primitive(),
            "inp_price_per_m": self.inp_price_per_m.as_primitive(),
            "out_price": self.out_price.as_primitive(),
            "out_price_per_m": self.out_price_per_m.as_primitive(),
            "vendor": self.vendor,
        }
        if self.cache_read_price is not None:
            d["cache_read_price"] = self.cache_read_price.as_primitive()
        if self.cache_read_price_per_m is not None:
            d["cache_read_price_per_m"] = self.cache_read_price_per_m.as_primitive()
        return d


# ═══════════════════════════════════════════════════════════════
# Entity — Benchmark records (per source, sealed)
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class AABenchmarks:
    intel: IntelligenceScore
    iq_per_dollar_pt: Optional[IQ_PerDollarPoint] = None
    iq_per_mtok: Optional[IQ_PerMToken] = None
    iq_per_mtokdollar: Optional[IQ_PerMTokenDollar] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "intel": self.intel.as_primitive(),
        }
        if self.iq_per_dollar_pt is not None:
            d["iq_per_dollar_pt"] = self.iq_per_dollar_pt.as_primitive()
        if self.iq_per_mtok is not None:
            d["iq_per_mtok"] = self.iq_per_mtok.as_primitive()
        if self.iq_per_mtokdollar is not None:
            d["iq_per_mtokdollar"] = self.iq_per_mtokdollar.as_primitive()
        return d


@dataclass(frozen=True)
class LiveBenchBenchmarks:
    average: BenchmarkScore
    agentic_coding: Optional[BenchmarkScore] = None
    coding: Optional[BenchmarkScore] = None
    data_analysis: Optional[BenchmarkScore] = None
    if_: Optional[BenchmarkScore] = None
    language: Optional[BenchmarkScore] = None
    mathematics: Optional[BenchmarkScore] = None
    reasoning: Optional[BenchmarkScore] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"average": self.average.as_primitive()}
        mappings = {
            "agentic_coding": self.agentic_coding,
            "coding": self.coding,
            "data_analysis": self.data_analysis,
            "if": self.if_,
            "language": self.language,
            "mathematics": self.mathematics,
            "reasoning": self.reasoning,
        }
        for key, val in mappings.items():
            if val is not None:
                d[key] = val.as_primitive()
        return d


@dataclass(frozen=True)
class ArenaBenchmarks:
    elo: Elo
    ci: CIMargin
    votes: VoteCount

    def to_dict(self) -> Dict[str, Any]:
        return {
            "elo": self.elo.as_primitive(),
            "ci": self.ci.as_primitive(),
            "votes": self.votes.as_primitive(),
        }


@dataclass(frozen=True)
class OpenLLMBenchmarks:
    average: BenchmarkScore
    ifeval: Optional[BenchmarkScore] = None
    bbh: Optional[BenchmarkScore] = None
    math_lvl_5: Optional[BenchmarkScore] = None
    gpqa: Optional[BenchmarkScore] = None
    musr: Optional[BenchmarkScore] = None
    mmlu_pro: Optional[BenchmarkScore] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"average": self.average.as_primitive()}
        for key in ("ifeval", "bbh", "math_lvl_5", "gpqa", "musr", "mmlu_pro"):
            val = getattr(self, key)
            if val is not None:
                d[key] = val.as_primitive()
        return d


# ═══════════════════════════════════════════════════════════════
# Entity — Model (in registry)
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class RegistryModelMeta:
    archetype: Optional[str] = None
    pareto_optimal: bool = False
    cost_percentile: Optional[float] = None
    iq_percentile: Optional[float] = None
    has_breakdown: bool = False
    params_b: Optional[ParameterCount] = None
    co2_kg: Optional[CarbonKg] = None
    architecture: Optional[str] = None
    license: Optional[str] = None
    precision: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {}
        for f in fields(self):
            val = getattr(self, f.name)
            if val is None or val is False:
                continue
            if isinstance(val, DomainValue):
                d[f.name] = val.as_primitive()
            else:
                d[f.name] = val
        return d


@dataclass(frozen=True)
class RegistryModel:
    id: str
    name: Optional[str] = None
    creator: Optional[str] = None
    model_type: Optional[ModelType] = None
    meta: RegistryModelMeta = field(default_factory=RegistryModelMeta)
    pricing: Dict[str, Any] = field(default_factory=dict)
    benchmarks: Dict[str, Any] = field(default_factory=dict)
    aliases: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            raise ValueError(f"Model ID cannot be empty")
        # Validate creator invariant for AA models
        if "aa" in self.pricing and self.creator is None:
            raise ValueError(f"Model {self.id} has AA pricing but no creator")

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "id": self.id,
        }
        if self.name is not None:
            d["name"] = self.name
        if self.creator is not None:
            d["creator"] = self.creator
        if self.model_type is not None:
            d["model_type"] = self.model_type.value

        meta_dict = self.meta.to_dict()
        if meta_dict:
            d["meta"] = meta_dict

        if self.pricing:
            d["pricing"] = {}
            for key, val in self.pricing.items():
                if hasattr(val, "to_dict"):
                    d["pricing"][key] = val.to_dict()
                elif val is not None:
                    d["pricing"][key] = val

        if self.benchmarks:
            d["benchmarks"] = {}
            for key, val in self.benchmarks.items():
                if hasattr(val, "to_dict"):
                    d["benchmarks"][key] = val.to_dict()
                elif val is not None:
                    d["benchmarks"][key] = val

        if self.aliases:
            d["aliases"] = dict(self.aliases)

        return d


# ═══════════════════════════════════════════════════════════════
# Entity — ProjectionRow (dashboard row)
# ═══════════════════════════════════════════════════════════════

@dataclass
class ProjectionRowMeta:
    archetype: Archetype = Archetype.UNCATEGORIZED
    pareto_optimal: bool = False
    has_breakdown: bool = False
    cost_percentile: Optional[Percentile] = None
    iq_percentile: Optional[Percentile] = None


@dataclass
class ProjectionRow:
    """Single dashboard row — flat, enriched, ready for JS consumption.

    Non-AA fields are Optional (None when data not available for this model).
    AA fields are required for curated models.
    """
    # Identity
    slug: str
    name: str
    creator: Optional[str] = None

    # AA pricing (required for curated models)
    inp_price: Optional[PricePerMToken] = None
    out_price: Optional[PricePerMToken] = None

    # Identity optional + metadata (has defaults — after required fields)
    type: Optional[ModelType] = None

    # Computed metadata (has default — keep after required fields)
    meta: ProjectionRowMeta = field(default_factory=ProjectionRowMeta)

    # AA pricing (optional additional)
    blended: Optional[PricePerMToken] = None
    cache_hit_price: Optional[PricePerMToken] = None
    cost_per_task: Optional[CostPerTask] = None
    tokens_m: Optional[TokensPerTask] = None
    speed_tps: Optional[TokensPerSecond] = None
    ttft: Optional[TimeToFirstToken] = None
    useful_cost: Optional[UsefulCost] = None
    reasoning_tax_pct: Optional[ReasoningTaxPct] = None

    # AA cost breakdown (all or nothing)
    cost_seg_total: Optional[CostSegment] = None
    cost_seg_answer: Optional[CostSegment] = None
    cost_seg_reasoning: Optional[CostSegment] = None
    cost_seg_cache_write: Optional[CostSegment] = None
    cost_seg_cache_hit: Optional[CostSegment] = None
    cost_seg_input: Optional[CostSegment] = None

    # AA benchmarks
    intel: Optional[IntelligenceScore] = None
    iq_per_dollar_pt: Optional[IQ_PerDollarPoint] = None
    iq_per_mtok: Optional[IQ_PerMToken] = None
    iq_per_mtokdollar: Optional[IQ_PerMTokenDollar] = None

    # LiveBench
    livebench_average: Optional[BenchmarkScore] = None
    livebench_coding: Optional[BenchmarkScore] = None
    livebench_reasoning: Optional[BenchmarkScore] = None
    livebench_mathematics: Optional[BenchmarkScore] = None
    livebench_language: Optional[BenchmarkScore] = None
    livebench_data_analysis: Optional[BenchmarkScore] = None
    livebench_agentic_coding: Optional[BenchmarkScore] = None
    livebench_if: Optional[BenchmarkScore] = None

    # Arena
    arena_code_elo: Optional[Elo] = None
    arena_code_ci: Optional[CIMargin] = None
    arena_code_votes: Optional[VoteCount] = None
    arena_text_elo: Optional[Elo] = None
    arena_text_ci: Optional[CIMargin] = None
    arena_text_votes: Optional[VoteCount] = None

    # OpenLLM
    openllm_average: Optional[BenchmarkScore] = None
    openllm_ifeval: Optional[BenchmarkScore] = None
    openllm_bbh: Optional[BenchmarkScore] = None
    openllm_math_lvl_5: Optional[BenchmarkScore] = None
    openllm_gpqa: Optional[BenchmarkScore] = None
    openllm_musr: Optional[BenchmarkScore] = None
    openllm_mmlu_pro: Optional[BenchmarkScore] = None

    # OpenRouter pricing
    openrouter_inp_price_per_m: Optional[PricePerMToken] = None
    openrouter_out_price_per_m: Optional[PricePerMToken] = None
    openrouter_cache_read_price_per_m: Optional[PricePerMToken] = None
    openrouter_vendor: Optional[str] = None

    # Meta
    params_b: Optional[ParameterCount] = None
    co2_kg: Optional[CarbonKg] = None
    context_window: Optional[ContextWindow] = None

    # Derived fields (computed lazily or set after construction)
    iq_per_1k_pt: Optional[IQ_PerDollarPoint] = None
    cost_per_iq_pt: Optional[CostPerIQPoint] = None

    # Radar-normalized scores [0, 1]. Computed in pipeline from dataset-wide maxes.
    radar_intel: Optional[float] = None
    radar_speed: Optional[float] = None
    radar_cache_eff: Optional[float] = None
    radar_cost_eff: Optional[float] = None
    radar_ctx: Optional[float] = None

    def __post_init__(self):
        if not self.slug:
            raise ValueError("slug required")

    # ── Field provenance ──
    # Every data field is either SOURCED (read from a provider file) or
    # DERIVED (computed in-pipeline from SOURCED inputs). The test suite
    # uses this to guarantee DERIVED fields are always produced from valid
    # SOURCED inputs — that's how the domain model stays safe.
    FIELD_PROVENANCE: ClassVar[Dict[str, 'Provenance']] = {
        # Identity / meta
        "slug": Provenance.SOURCED, "name": Provenance.SOURCED,
        "creator": Provenance.SOURCED, "type": Provenance.SOURCED,
        "meta": Provenance.SOURCED,
        # AA pricing (sourced)
        "inp_price": Provenance.SOURCED, "out_price": Provenance.SOURCED,
        "blended": Provenance.SOURCED, "cache_hit_price": Provenance.SOURCED,
        "cost_per_task": Provenance.SOURCED, "tokens_m": Provenance.SOURCED,
        "speed_tps": Provenance.SOURCED, "ttft": Provenance.SOURCED,
        "useful_cost": Provenance.SOURCED, "reasoning_tax_pct": Provenance.SOURCED,
        # AA cost breakdown (sourced — all-or-nothing from AA)
        "cost_seg_total": Provenance.SOURCED, "cost_seg_answer": Provenance.SOURCED,
        "cost_seg_reasoning": Provenance.SOURCED, "cost_seg_cache_write": Provenance.SOURCED,
        "cost_seg_cache_hit": Provenance.SOURCED, "cost_seg_input": Provenance.SOURCED,
        # AA benchmarks
        "intel": Provenance.SOURCED, "iq_per_dollar_pt": Provenance.SOURCED,
        "iq_per_mtok": Provenance.SOURCED, "iq_per_mtokdollar": Provenance.SOURCED,
        # LiveBench / Arena / OpenLLM (sourced)
        "livebench_average": Provenance.SOURCED, "livebench_coding": Provenance.SOURCED,
        "livebench_reasoning": Provenance.SOURCED, "livebench_mathematics": Provenance.SOURCED,
        "livebench_language": Provenance.SOURCED, "livebench_data_analysis": Provenance.SOURCED,
        "livebench_agentic_coding": Provenance.SOURCED, "livebench_if": Provenance.SOURCED,
        "arena_code_elo": Provenance.SOURCED, "arena_code_ci": Provenance.SOURCED,
        "arena_code_votes": Provenance.SOURCED, "arena_text_elo": Provenance.SOURCED,
        "arena_text_ci": Provenance.SOURCED, "arena_text_votes": Provenance.SOURCED,
        "openllm_average": Provenance.SOURCED, "openllm_ifeval": Provenance.SOURCED,
        "openllm_bbh": Provenance.SOURCED, "openllm_math_lvl_5": Provenance.SOURCED,
        "openllm_gpqa": Provenance.SOURCED, "openllm_musr": Provenance.SOURCED,
        "openllm_mmlu_pro": Provenance.SOURCED,
        # OpenRouter pricing (sourced)
        "openrouter_inp_price_per_m": Provenance.SOURCED,
        "openrouter_out_price_per_m": Provenance.SOURCED,
        "openrouter_cache_read_price_per_m": Provenance.SOURCED,
        "openrouter_vendor": Provenance.SOURCED,
        # Meta (sourced)
        "params_b": Provenance.SOURCED, "co2_kg": Provenance.SOURCED,
        "context_window": Provenance.SOURCED,
        # Archetype — computed from SOURCED inputs (intel, cost, speed, reasoning, params)
        "archetype": Provenance.DERIVED,
        # Derived fields (computed in-pipeline)
        "iq_per_1k_pt": Provenance.DERIVED, "cost_per_iq_pt": Provenance.DERIVED,
        # Radar-normalized scores
        "radar_intel": Provenance.DERIVED, "radar_speed": Provenance.DERIVED,
        "radar_cache_eff": Provenance.DERIVED, "radar_cost_eff": Provenance.DERIVED,
        "radar_ctx": Provenance.DERIVED,
    }

    # ── Derived field computation ──

    def compute_derived(self) -> 'ProjectionRow':
        intel = None
        if self.intel is not None:
            intel = self.intel.as_primitive()
        cost_task = None
        if self.cost_per_task is not None:
            cost_task = self.cost_per_task.as_primitive()

        if intel is not None and cost_task is not None and cost_task > 0:
            self.iq_per_1k_pt = IQ_PerDollarPoint(round(intel / cost_task * 1000, 1))
            self.cost_per_iq_pt = CostPerIQPoint(round(cost_task / intel, 6))

        return self

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "slug": self.slug,
            "name": self.name,
            "creator": self.creator,
            "type": self.type.value if self.type else None,
            "intel": None,
            "cost_per_task": None,
            "tokens_m": None,
            "speed_tps": None,
            "inp_price": self.inp_price.as_primitive() if self.inp_price else None,
            "out_price": self.out_price.as_primitive() if self.out_price else None,
            "iq_per_dollar_pt": None,
            "iq_per_mtok": None,
            "iq_per_mtokdollar": None,
            "useful_cost": None,
            "reasoning_tax_pct": None,
            "archetype": self.meta.archetype.value if self.meta else None,
            "has_breakdown": self.meta.has_breakdown if self.meta else False,
            "pareto_optimal": self.meta.pareto_optimal if self.meta else False,
            "cost_percentile": None,
            "iq_percentile": None,
            "context_window": None,
        }

        # Map optional fields
        optional_map: Dict[str, Optional[DomainValue]] = {
            "intel": self.intel,
            "cost_per_task": self.cost_per_task,
            "tokens_m": self.tokens_m,
            "speed_tps": self.speed_tps,
            "ttft": self.ttft,
            "blended": self.blended,
            "cache_hit_price": self.cache_hit_price,
            "iq_per_dollar_pt": self.iq_per_dollar_pt,
            "iq_per_mtok": self.iq_per_mtok,
            "iq_per_mtokdollar": self.iq_per_mtokdollar,
            "useful_cost": self.useful_cost,
            "reasoning_tax_pct": self.reasoning_tax_pct,
            "cost_seg_total": self.cost_seg_total,
            "cost_seg_answer": self.cost_seg_answer,
            "cost_seg_reasoning": self.cost_seg_reasoning,
            "cost_seg_cache_write": self.cost_seg_cache_write,
            "cost_seg_cache_hit": self.cost_seg_cache_hit,
            "cost_seg_input": self.cost_seg_input,
            "livebench_average": self.livebench_average,
            "livebench_coding": self.livebench_coding,
            "livebench_reasoning": self.livebench_reasoning,
            "livebench_mathematics": self.livebench_mathematics,
            "livebench_language": self.livebench_language,
            "livebench_data_analysis": self.livebench_data_analysis,
            "livebench_agentic_coding": self.livebench_agentic_coding,
            "livebench_if": self.livebench_if,
            "arena_code_elo": self.arena_code_elo,
            "arena_code_ci": self.arena_code_ci,
            "arena_code_votes": self.arena_code_votes,
            "arena_text_elo": self.arena_text_elo,
            "arena_text_ci": self.arena_text_ci,
            "arena_text_votes": self.arena_text_votes,
            "openllm_average": self.openllm_average,
            "openllm_ifeval": self.openllm_ifeval,
            "openllm_bbh": self.openllm_bbh,
            "openllm_math_lvl_5": self.openllm_math_lvl_5,
            "openllm_gpqa": self.openllm_gpqa,
            "openllm_musr": self.openllm_musr,
            "openllm_mmlu_pro": self.openllm_mmlu_pro,
            "openrouter_inp_price_per_m": self.openrouter_inp_price_per_m,
            "openrouter_out_price_per_m": self.openrouter_out_price_per_m,
            "openrouter_cache_read_price_per_m": self.openrouter_cache_read_price_per_m,
            "params_b": self.params_b,
            "co2_kg": self.co2_kg,
            "context_window": self.context_window,
            "iq_per_1k_pt": self.iq_per_1k_pt,
            "cost_per_iq_pt": self.cost_per_iq_pt,
            "radar_intel": self.radar_intel,
            "radar_speed": self.radar_speed,
            "radar_cache_eff": self.radar_cache_eff,
            "radar_cost_eff": self.radar_cost_eff,
            "radar_ctx": self.radar_ctx,
        }
        for key, val in optional_map.items():
            if val is not None:
                d[key] = val.as_primitive() if isinstance(val, DomainValue) else val

        if self.meta is not None:
            if self.meta.cost_percentile is not None:
                d["cost_percentile"] = self.meta.cost_percentile.as_primitive()
            if self.meta.iq_percentile is not None:
                d["iq_percentile"] = self.meta.iq_percentile.as_primitive()

        if self.openrouter_vendor is not None:
            d["openrouter_vendor"] = self.openrouter_vendor

        return d


# ═══════════════════════════════════════════════════════════════
# Serialization helpers
# ═══════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════
# Safe constructors (accept raw data, handle null/NaN, return None)
# ═══════════════════════════════════════════════════════════════

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

