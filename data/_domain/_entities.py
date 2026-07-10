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
            model_type=model_type,
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
