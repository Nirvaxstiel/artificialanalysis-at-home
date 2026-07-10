from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, Optional

from ._base import Archetype, DomainValue, ModelType, Provenance
from ._values import (
    PricePerMToken, PricePerToken,
    CostPerTask, TokensPerTask, TokensPerSecond, TimeToFirstToken,
    UsefulCost, ReasoningTaxPct, CacheHitRate, CostSegment,
    IntelligenceScore, IQ_PerDollarPoint, IQ_PerMToken, IQ_PerMTokenDollar,
    CostPerIQPoint,
    Elo, CIMargin, VoteCount, BenchmarkScore,
    ParameterCount, CarbonKg, ContextWindow, Percentile,
    ResponseTime, OmniscienceIndex, AxisMetric,
)


@dataclass
class ProjectionRowMeta:
    archetype: Archetype = Archetype.UNCATEGORIZED
    pareto_optimal: bool = False
    has_breakdown: bool = False
    cost_percentile: Optional[Percentile] = None
    iq_percentile: Optional[Percentile] = None
    release_date: Optional[str] = None
    confirmed_scraped: Optional[bool] = None


@dataclass
class ProjectionRow:
    slug: str
    name: str
    creator: Optional[str] = None
    inp_price: Optional[PricePerMToken] = None
    out_price: Optional[PricePerMToken] = None
    type: Optional[ModelType] = None
    meta: ProjectionRowMeta = field(default_factory=ProjectionRowMeta)
    blended: Optional[PricePerMToken] = None
    cache_hit_price: Optional[PricePerMToken] = None
    cost_per_task: Optional[CostPerTask] = None
    tokens_m: Optional[TokensPerTask] = None
    speed_tps: Optional[TokensPerSecond] = None
    ttft: Optional[TimeToFirstToken] = None
    useful_cost: Optional[UsefulCost] = None
    reasoning_tax_pct: Optional[ReasoningTaxPct] = None
    cost_seg_total: Optional[CostSegment] = None
    cost_seg_answer: Optional[CostSegment] = None
    cost_seg_reasoning: Optional[CostSegment] = None
    cost_seg_cache_write: Optional[CostSegment] = None
    cost_seg_cache_hit: Optional[CostSegment] = None
    cost_seg_input: Optional[CostSegment] = None
    intel: Optional[IntelligenceScore] = None
    iq_per_dollar_pt: Optional[IQ_PerDollarPoint] = None
    iq_per_mtok: Optional[IQ_PerMToken] = None
    iq_per_mtokdollar: Optional[IQ_PerMTokenDollar] = None
    livebench_average: Optional[BenchmarkScore] = None
    livebench_coding: Optional[BenchmarkScore] = None
    livebench_reasoning: Optional[BenchmarkScore] = None
    livebench_mathematics: Optional[BenchmarkScore] = None
    livebench_language: Optional[BenchmarkScore] = None
    livebench_data_analysis: Optional[BenchmarkScore] = None
    livebench_agentic_coding: Optional[BenchmarkScore] = None
    livebench_if: Optional[BenchmarkScore] = None
    arena_code_elo: Optional[Elo] = None
    arena_code_ci: Optional[CIMargin] = None
    arena_code_votes: Optional[VoteCount] = None
    arena_text_elo: Optional[Elo] = None
    arena_text_ci: Optional[CIMargin] = None
    arena_text_votes: Optional[VoteCount] = None
    openllm_average: Optional[BenchmarkScore] = None
    openllm_ifeval: Optional[BenchmarkScore] = None
    openllm_bbh: Optional[BenchmarkScore] = None
    openllm_math_lvl_5: Optional[BenchmarkScore] = None
    openllm_gpqa: Optional[BenchmarkScore] = None
    openllm_musr: Optional[BenchmarkScore] = None
    openllm_mmlu_pro: Optional[BenchmarkScore] = None
    aa_coding_index: Optional[BenchmarkScore] = None
    aa_math_index: Optional[BenchmarkScore] = None
    aa_gpqa: Optional[BenchmarkScore] = None
    aa_mmlu_pro: Optional[BenchmarkScore] = None
    aa_hle: Optional[BenchmarkScore] = None
    aa_aime: Optional[BenchmarkScore] = None
    aa_aime_25: Optional[BenchmarkScore] = None
    aa_math_500: Optional[BenchmarkScore] = None
    aa_livecodebench: Optional[BenchmarkScore] = None
    aa_ifbench: Optional[BenchmarkScore] = None
    aa_lcr: Optional[BenchmarkScore] = None
    aa_scicode: Optional[BenchmarkScore] = None
    aa_tau2: Optional[BenchmarkScore] = None
    aa_tau_banking: Optional[BenchmarkScore] = None
    aa_terminalbench_hard: Optional[BenchmarkScore] = None
    aa_terminalbench_v2_1: Optional[BenchmarkScore] = None
    aa_omniscience_hallucination_rate: Optional[BenchmarkScore] = None
    aa_briefcase_analytical_quality_elo: Optional[Elo] = None
    aa_briefcase_presentation_elo: Optional[Elo] = None
    aa_time_per_task: Optional[ResponseTime] = None
    openrouter_inp_price_per_m: Optional[PricePerMToken] = None
    openrouter_out_price_per_m: Optional[PricePerMToken] = None
    openrouter_cache_read_price_per_m: Optional[PricePerMToken] = None
    openrouter_vendor: Optional[str] = None
    params_b: Optional[ParameterCount] = None
    params_total_b: Optional[ParameterCount] = None
    params_active_b: Optional[ParameterCount] = None
    co2_kg: Optional[CarbonKg] = None
    context_window: Optional[ContextWindow] = None
    omniscience_index: Optional[OmniscienceIndex] = None
    omniscience_accuracy: Optional[BenchmarkScore] = None
    omniscience_hallucination_rate: Optional[BenchmarkScore] = None
    briefcase_elo: Optional[Elo] = None
    briefcase_analytical_quality_elo: Optional[Elo] = None
    briefcase_presentation_elo: Optional[Elo] = None
    briefcase_rubric_score: Optional[BenchmarkScore] = None
    agentic_index: Optional[BenchmarkScore] = None
    coding_index: Optional[BenchmarkScore] = None
    openness_index: Optional[BenchmarkScore] = None
    e2e_response_time_s: Optional[ResponseTime] = None
    ttft_variance: Optional[AxisMetric] = None
    cache_hit_rate_max: Optional[CacheHitRate] = None
    iq_per_dollar_pt: Optional[IQ_PerDollarPoint] = None
    iq_per_1k_pt: Optional[IQ_PerDollarPoint] = None
    cost_per_iq_pt: Optional[CostPerIQPoint] = None
    radar_intel: Optional[float] = None
    radar_speed: Optional[float] = None
    radar_cache_eff: Optional[float] = None
    radar_cost_eff: Optional[float] = None
    radar_ctx: Optional[float] = None

    def __post_init__(self):
        if not self.slug:
            raise ValueError("slug required")

    FIELD_PROVENANCE: ClassVar[Dict[str, Provenance]] = {
        "slug": Provenance.SOURCED, "name": Provenance.SOURCED,
        "creator": Provenance.SOURCED, "type": Provenance.SOURCED,
        "meta": Provenance.SOURCED,
        "inp_price": Provenance.SOURCED, "out_price": Provenance.SOURCED,
        "blended": Provenance.SOURCED, "cache_hit_price": Provenance.SOURCED,
        "cost_per_task": Provenance.SOURCED, "tokens_m": Provenance.SOURCED,
        "speed_tps": Provenance.SOURCED, "ttft": Provenance.SOURCED,
        "useful_cost": Provenance.SOURCED, "reasoning_tax_pct": Provenance.SOURCED,
        "cost_seg_total": Provenance.SOURCED, "cost_seg_answer": Provenance.SOURCED,
        "cost_seg_reasoning": Provenance.SOURCED, "cost_seg_cache_write": Provenance.SOURCED,
        "cost_seg_cache_hit": Provenance.SOURCED, "cost_seg_input": Provenance.SOURCED,
        "intel": Provenance.SOURCED, "iq_per_dollar_pt": Provenance.SOURCED,
        "iq_per_mtok": Provenance.SOURCED, "iq_per_mtokdollar": Provenance.SOURCED,
        "livebench_average": Provenance.SOURCED,
        "livebench_coding": Provenance.SOURCED,
        "livebench_reasoning": Provenance.SOURCED,
        "livebench_mathematics": Provenance.SOURCED,
        "livebench_language": Provenance.SOURCED,
        "livebench_data_analysis": Provenance.SOURCED,
        "livebench_agentic_coding": Provenance.SOURCED,
        "livebench_if": Provenance.SOURCED,
        "arena_code_elo": Provenance.SOURCED, "arena_code_ci": Provenance.SOURCED,
        "arena_code_votes": Provenance.SOURCED, "arena_text_elo": Provenance.SOURCED,
        "arena_text_ci": Provenance.SOURCED, "arena_text_votes": Provenance.SOURCED,
        "openllm_average": Provenance.SOURCED, "openllm_ifeval": Provenance.SOURCED,
        "openllm_bbh": Provenance.SOURCED, "openllm_math_lvl_5": Provenance.SOURCED,
        "openllm_gpqa": Provenance.SOURCED, "openllm_musr": Provenance.SOURCED,
        "openllm_mmlu_pro": Provenance.SOURCED,
        "aa_coding_index": Provenance.SOURCED, "aa_math_index": Provenance.SOURCED,
        "aa_gpqa": Provenance.SOURCED, "aa_mmlu_pro": Provenance.SOURCED,
        "aa_hle": Provenance.SOURCED, "aa_aime": Provenance.SOURCED,
        "aa_aime_25": Provenance.SOURCED, "aa_math_500": Provenance.SOURCED,
        "aa_livecodebench": Provenance.SOURCED, "aa_ifbench": Provenance.SOURCED,
        "aa_lcr": Provenance.SOURCED, "aa_scicode": Provenance.SOURCED,
        "aa_tau2": Provenance.SOURCED, "aa_tau_banking": Provenance.SOURCED,
        "aa_terminalbench_hard": Provenance.SOURCED, "aa_terminalbench_v2_1": Provenance.SOURCED,
        "aa_omniscience_hallucination_rate": Provenance.SOURCED,
        "aa_briefcase_analytical_quality_elo": Provenance.SOURCED,
        "aa_briefcase_presentation_elo": Provenance.SOURCED,
        "aa_time_per_task": Provenance.SOURCED,
        "openrouter_inp_price_per_m": Provenance.SOURCED,
        "openrouter_out_price_per_m": Provenance.SOURCED,
        "openrouter_cache_read_price_per_m": Provenance.SOURCED,
        "openrouter_vendor": Provenance.SOURCED,
        "params_b": Provenance.SOURCED, "co2_kg": Provenance.SOURCED,
        "context_window": Provenance.SOURCED,
        "params_total_b": Provenance.SOURCED,
        "params_active_b": Provenance.SOURCED,
        "omniscience_index": Provenance.SOURCED,
        "omniscience_accuracy": Provenance.SOURCED,
        "omniscience_hallucination_rate": Provenance.SOURCED,
        "briefcase_elo": Provenance.SOURCED,
        "briefcase_analytical_quality_elo": Provenance.SOURCED,
        "briefcase_presentation_elo": Provenance.SOURCED,
        "briefcase_rubric_score": Provenance.SOURCED,
        "agentic_index": Provenance.SOURCED,
        "coding_index": Provenance.SOURCED,
        "openness_index": Provenance.SOURCED,
        "e2e_response_time_s": Provenance.SOURCED,
        "ttft_variance": Provenance.SOURCED,
        "cache_hit_rate_max": Provenance.SOURCED,
        "archetype": Provenance.DERIVED,
        "iq_per_dollar_pt": Provenance.SOURCED,
        "iq_per_1k_pt": Provenance.DERIVED, "cost_per_iq_pt": Provenance.DERIVED,
        "radar_intel": Provenance.DERIVED, "radar_speed": Provenance.DERIVED,
        "radar_cache_eff": Provenance.DERIVED, "radar_cost_eff": Provenance.DERIVED,
        "radar_ctx": Provenance.DERIVED,
    }

    def compute_derived(self) -> 'ProjectionRow':
        intel_val = self.intel.as_primitive() if self.intel else None
        cost_task = self.cost_per_task.as_primitive() if self.cost_per_task else None
        if intel_val is not None and cost_task is not None and cost_task > 0:
            self.iq_per_1k_pt = IQ_PerDollarPoint(round(intel_val / cost_task * 1000, 1))
            self.cost_per_iq_pt = CostPerIQPoint(round(cost_task / intel_val, 6))
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
            "aa_coding_index": self.aa_coding_index,
            "aa_math_index": self.aa_math_index,
            "aa_gpqa": self.aa_gpqa,
            "aa_mmlu_pro": self.aa_mmlu_pro,
            "aa_hle": self.aa_hle,
            "aa_aime": self.aa_aime,
            "aa_aime_25": self.aa_aime_25,
            "aa_math_500": self.aa_math_500,
            "aa_livecodebench": self.aa_livecodebench,
            "aa_ifbench": self.aa_ifbench,
            "aa_lcr": self.aa_lcr,
            "aa_scicode": self.aa_scicode,
            "aa_tau2": self.aa_tau2,
            "aa_tau_banking": self.aa_tau_banking,
            "aa_terminalbench_hard": self.aa_terminalbench_hard,
            "aa_terminalbench_v2_1": self.aa_terminalbench_v2_1,
            "aa_omniscience_hallucination_rate": self.aa_omniscience_hallucination_rate,
            "aa_briefcase_analytical_quality_elo": self.aa_briefcase_analytical_quality_elo,
            "aa_briefcase_presentation_elo": self.aa_briefcase_presentation_elo,
            "aa_time_per_task": self.aa_time_per_task,
            "openrouter_inp_price_per_m": self.openrouter_inp_price_per_m,
            "openrouter_out_price_per_m": self.openrouter_out_price_per_m,
            "openrouter_cache_read_price_per_m": self.openrouter_cache_read_price_per_m,
            "params_b": self.params_b,
            "params_total_b": self.params_total_b,
            "params_active_b": self.params_active_b,
            "co2_kg": self.co2_kg,
            "context_window": self.context_window,
            "omniscience_index": self.omniscience_index,
            "omniscience_accuracy": self.omniscience_accuracy,
            "omniscience_hallucination_rate": self.omniscience_hallucination_rate,
            "briefcase_elo": self.briefcase_elo,
            "briefcase_analytical_quality_elo": self.briefcase_analytical_quality_elo,
            "briefcase_presentation_elo": self.briefcase_presentation_elo,
            "briefcase_rubric_score": self.briefcase_rubric_score,
            "agentic_index": self.agentic_index,
            "coding_index": self.coding_index,
            "openness_index": self.openness_index,
            "e2e_response_time_s": self.e2e_response_time_s,
            "ttft_variance": self.ttft_variance,
            "cache_hit_rate_max": self.cache_hit_rate_max,
            "iq_per_dollar_pt": self.iq_per_dollar_pt,
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
            if self.meta.release_date is not None:
                d["release_date"] = self.meta.release_date
            if self.meta.confirmed_scraped is not None:
                d["confirmed_scraped"] = self.meta.confirmed_scraped
        if self.openrouter_vendor is not None:
            d["openrouter_vendor"] = self.openrouter_vendor
        return d
