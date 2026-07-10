import re
from dataclasses import dataclass, field, fields
from typing import Any, Dict, List, Optional, Tuple

from ._base import (
    DomainValue, Direction, AxisCategory, SourceKey, ModelType,
)
from ._values import (
    PricePerMToken, PricePerToken, CostPerTask, TokensPerTask, TokensPerSecond,
    UsefulCost, ReasoningTaxPct, CacheHitRate, CostSegment,
    IntelligenceScore, IQ_PerDollarPoint, IQ_PerMToken, IQ_PerMTokenDollar,
    Elo, CIMargin, VoteCount, BenchmarkScore,
    ParameterCount, CarbonKg, ContextWindow,
)


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


@dataclass(frozen=True)
class AABenchmarks:
    intel: IntelligenceScore
    iq_per_dollar_pt: Optional[IQ_PerDollarPoint] = None
    iq_per_mtok: Optional[IQ_PerMToken] = None
    iq_per_mtokdollar: Optional[IQ_PerMTokenDollar] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"intel": self.intel.as_primitive()}
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
    release_date: Optional[str] = None
    confirmed_scraped: Optional[bool] = None
    context_window: Optional[int] = None

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

    @classmethod
    def from_flat(cls, d: Dict[str, Any]) -> 'RegistryModel':
        """Build from the pipeline's plain-dict registry contract.

        Wraps the flat `meta` dict in RegistryModelMeta (typed/validated) while
        keeping pricing/benchmarks as plain dicts — the pipeline emits those as
        dicts, not AAPricing/CostBreakdownPricing objects. This makes
        RegistryModel a validating serializer over the existing contract without
        forcing a rewrite of every source module.
        """
        meta = d.get("meta") or {}
        meta_obj = RegistryModelMeta(
            archetype=meta.get("archetype"),
            pareto_optimal=meta.get("pareto_optimal", False),
            has_breakdown=meta.get("has_breakdown", False),
            params_b=meta.get("params_b"),
            co2_kg=meta.get("co2_kg"),
            architecture=meta.get("architecture"),
            license=meta.get("license"),
            precision=meta.get("precision"),
            release_date=meta.get("release_date"),
            confirmed_scraped=meta.get("confirmed_scraped"),
            context_window=meta.get("context_window"),
        )
        mt = d.get("model_type")
        model_type = None
        if mt:
            try:
                model_type = ModelType(mt)
            except ValueError:
                model_type = None
        return cls(
            id=d["id"],
            name=d.get("name"),
            creator=d.get("creator"),
            model_type=ModelType(mt) if mt else None,
            meta=meta_obj,
            pricing=d.get("pricing", {}) or {},
            benchmarks=d.get("benchmarks", {}) or {},
            aliases=d.get("aliases", {}) or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"id": self.id}
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
