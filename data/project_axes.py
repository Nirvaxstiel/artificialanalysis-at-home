"""Projection engine — extract N-axis cross-source matrices from model registry.

Usage:
    from project_axes import ProjectionEngine
    pe = ProjectionEngine()
    
    # Get N-axis matrix
    matrix = pe.project(["aa.intel", "aa.inp_price", "livebench.coding", "arena_text.elo"])
    
    # Filter by model subset
    matrix = pe.project(["aa.intel", "aa.inp_price"], model_ids=["deepseek-v4-pro", "gpt-5.5-high"])
    
    # Get feasible intersections
    pe.feasibility_report(min_overlap=3)
"""

import json, os, re
from pathlib import Path

BASE = Path(__file__).resolve().parent if "__file__" in dir() else Path.cwd()
DATA = BASE / "data" if (BASE / "data").exists() else BASE

class ProjectionEngine:
    """Cross-source axis projection engine."""
    
    def __init__(self, registry_path=None, axes_path=None):
        rp = registry_path or str(DATA / "model_registry.json")
        ap = axes_path or str(DATA / "axes_catalog.json")
        
        with open(rp) as f:
            self.registry = json.load(f)
        with open(ap) as f:
            self.catalog = json.load(f)
        
        self.models = self.registry["models"]
        self.axes_meta = {a["id"].casefold(): a for a in self.catalog["axes"]}
        
        # Path overrides for axes that don't follow source.segment convention
        self._path_override = {
            # cost segment axes: stored at pricing.aa.cost_segments.{original_key}
            "aa.cost_seg_total": ("pricing", "aa", "cost_segments", "total_cost_per_task_usd"),
            "aa.cost_seg_answer": ("pricing", "aa", "cost_segments", "answer_usd"),
            "aa.cost_seg_reasoning": ("pricing", "aa", "cost_segments", "reasoning_usd"),
            "aa.cost_seg_cache_write": ("pricing", "aa", "cost_segments", "cache_write_usd"),
            "aa.cost_seg_cache_hit": ("pricing", "aa", "cost_segments", "cache_hit_usd"),
            "aa.cost_seg_input": ("pricing", "aa", "cost_segments", "input_usd"),
        }
    
    def _resolve_axis(self, axis_id):
        """Resolve axis ID case-insensitively."""
        cf = axis_id.casefold()
        if cf in self.axes_meta:
            return cf  # return the lowercased key
        raise ValueError(f"Axis '{axis_id}' not found. Known axes from this source: "
                         f"{[k for k in self.axes_meta if k.startswith(axis_id.split('.')[0].casefold())][:10]}")
    
    def get_value(self, model, axis_id):
        """Extract a single axis value from a model dict. Axis ID is case-insensitive."""
        cf = axis_id.casefold()
        # Check path overrides first
        if cf in self._path_override:
            path = self._path_override[cf]
            sec = model
            for k in path[:-1]:
                sec = sec.get(k, {})
            return sec.get(path[-1])
        
        resolved = self._resolve_axis(axis_id)
        meta = self.axes_meta[resolved]
        actual_id = meta["id"]
        parts = actual_id.split(".")
        source = parts[0]
        
        # Check for _dict_key override (LiveBench needs original mixed-case key)
        dict_key = meta.get("_dict_key")
        
        if source == "meta":
            return model.get("meta", {}).get(parts[-1])
        
        # Some sources have axes in both pricing and benchmarks (e.g. aa)
        # Try benchmarks first, then pricing
        if source in ("aa", "openrouter"):
            # Check benchmarks first
            sec = model.get("benchmarks", {}).get(source, {})
            if len(parts) == 2:
                v = sec.get(dict_key or parts[1])
                if v is not None:
                    return v
                # Try pricing
                sec = model.get("pricing", {}).get(source, {})
                if len(parts) >= 3:
                    sub = sec.get(parts[1], {})
                    return sub.get(parts[2] if len(parts)==3 else dict_key)
                return sec.get(dict_key or parts[1])
            elif len(parts) == 3:
                # Try pricing.cost_segments.X or similar sub-paths
                sec = model.get("pricing", {}).get(source, {})
                sub = sec.get(parts[1], {})
                return sub.get(parts[2])
        
        # Other benchmark-only sources
        if source in ("livebench", "arena_text", "arena_code", "openllm"):
            sec = model.get("benchmarks", {}).get(source, {})
            if len(parts) == 2:
                return sec.get(dict_key or parts[1])
            elif len(parts) == 3:
                sub = sec.get(parts[1], {})
                return sub.get(parts[2])
        
        return None
    
    def project(self, axis_ids, model_ids=None, require_all=False):
        """Build model×axis matrix.
        
        Args:
            axis_ids: list of axis IDs (e.g. ["aa.intel", "livebench.reasoning"])
            model_ids: optional filter — only these canonical model IDs
            require_all: if True, only include models that have ALL requested axes
        
        Returns:
            list of dicts: [{"id": str, "name": str, "creator": str, 
                             axes: {axis_id: value, ...}}, ...]
        """
        # Validate axes exist (case-insensitive)
        for aid in axis_ids:
            _ = self._resolve_axis(aid)  # will raise if not found
        
        results = []
        model_set = set(model_ids) if model_ids else None
        
        for m in self.models:
            cid = m["id"]
            if model_set and cid not in model_set:
                continue
            
            row = {
                "id": cid,
                "name": m.get("name"),
                "creator": m.get("creator"),
                "model_type": m.get("model_type"),
                "axes": {},
            }
            
            all_present = True
            for aid in axis_ids:
                v = self.get_value(m, aid)
                row["axes"][aid] = v
                if v is None:
                    all_present = False
            
            if require_all and not all_present:
                continue
            
            # Only include models with at least one non-None value
            if any(v is not None for v in row["axes"].values()):
                results.append(row)
        
        return results
    
    def feasibility_report(self, min_overlap=3):
        """Report which axis source-pairs have enough models for analysis."""
        axes_by_source = {}
        for a in self.catalog["axes"]:
            s = a["source"]
            if a["type"] == "meta":
                continue
            if s not in axes_by_source:
                axes_by_source[s] = []
            axes_by_source[s].append(a["id"])
        
        sources = sorted(axes_by_source.keys())
        pairs = {}
        for i, s1 in enumerate(sources):
            for s2 in sources[i+1:]:
                a1 = axes_by_source[s1][:1]   # Representative axis
                a2 = axes_by_source[s2][:1]
                matrix = self.project(a1 + a2)
                overlap = sum(1 for r in matrix if r["axes"][a1[0]] is not None and r["axes"][a2[0]] is not None)
                if overlap >= min_overlap:
                    pairs[f"{s1}×{s2}"] = {
                        "models": overlap,
                        "representative_axes": [a1[0], a2[0]],
                        "all_axes_s1": axes_by_source[s1],
                        "all_axes_s2": axes_by_source[s2],
                    }
        
        return {
            "sources": sources,
            "pairs": pairs,
            "total_models": len(self.models),
        }
    
    def describe_axis(self, axis_id):
        """Get metadata for an axis."""
        return self.axes_meta.get(axis_id)
    
    def list_axes(self, source=None, axis_type=None):
        """List axes with optional filters."""
        results = []
        for a in self.catalog["axes"]:
            if source and a["source"] != source:
                continue
            if axis_type and a["type"] != axis_type:
                continue
            results.append(a)
        return results


# ── CLI / Demo ──
if __name__ == "__main__":
    pe = ProjectionEngine()
    
    print("═══ PROJECTION ENGINE ═══")
    print(f"  Models: {len(pe.models):,}")
    print(f"  Axes:   {len(pe.catalog['axes'])}")
    print(f"  Sources: {pe.catalog['meta']['sources']}")
    
    print("\n═══ EXAMPLE QUERIES ═══")
    
    # Query 1: AA "Sweet Spot" — quality vs cost
    print("\n── Query 1: AA Intelligence vs AA Input Price (sweet-spot archetypes) ──")
    m1 = pe.project(["aa.intel", "aa.inp_price", "aa.speed_tps"],
                     model_ids=[m["id"] for m in pe.models if m.get("meta", {}).get("archetype") == "sweet-spot"])
    for r in m1[:10]:
        iq = r['axes']['aa.intel']
        inp = r['axes']['aa.inp_price']
        spd = r['axes']['aa.speed_tps']
        print(f"  {r['id']:35s} IQ={iq if iq is not None else '-':>5}  "
              f"${inp if inp is not None else '-':>6}/Mtok  "
              f"{spd if spd is not None else '-':>6} t/s")
    
    # Query 2: Multi-source crossover — AA intel + LiveBench coding + Arena Elo + OpenRouter price
    print("\n── Query 2: 4-axis crossover (require_all=True) ──")
    axes_4 = ["aa.intel", "livebench.coding", "arena_code.elo", "openrouter.inp_price_per_m"]
    m2 = pe.project(axes_4, require_all=True)
    print(f"  Models with ALL 4 axes: {len(m2)}")
    for r in sorted(m2, key=lambda x: -(x["axes"]["aa.intel"] or 0))[:8]:
        iq = r['axes']['aa.intel']
        lb = r['axes']['livebench.coding']
        elo = r['axes']['arena_code.elo']
        orp = r['axes']['openrouter.inp_price_per_m']
        print(f"  {r['id']:35s} IQ={iq if iq is not None else '-':>5}  "
              f"LB-Code={lb if lb is not None else '-':>6}  "
              f"Code-Elo={elo if elo is not None else '-':>4}  "
              f"OR-Inp=${orp if orp is not None else '-':>}/Mtok")
    
    # Query 3: Cost segment vs benchmark (cache efficiency)
    print("\n── Query 3: Cost segments vs LiveBench reasoning ──")
    m3 = pe.project(["livebench.reasoning", "aa.cost_seg_reasoning", "aa.cost_seg_cache_hit", "aa.reasoning_tax_pct"],
                     require_all=True)
    print(f"  Models with cost segmentation + LiveBench reasoning: {len(m3)}")
    for r in sorted(m3, key=lambda x: -(x["axes"]["livebench.reasoning"] or 0))[:6]:
        lbr = r['axes']['livebench.reasoning']
        rc = r['axes']['aa.cost_seg_reasoning']
        ch = r['axes']['aa.cost_seg_cache_hit']
        tax = r['axes']['aa.reasoning_tax_pct']
        print(f"  {r['id']:35s} LB-Reason={lbr if lbr is not None else '-':>6}  "
              f"ReasonCost=${rc if rc is not None else '-':>}  "
              f"CacheHit=${ch if ch is not None else '-':>}  "
              f"Tax={tax if tax is not None else 0:>3.0f}%")
    
    # Query 4: Multi-benchmark comparison — LiveBench coding vs Arena Code Elo
    print("\n── Query 4: LiveBench coding vs Arena Code Elo ──")
    m4 = pe.project(["livebench.coding", "arena_code.elo"], require_all=True)
    print(f"  Models in both LiveBench coding + Arena Code: {len(m4)}")
    for r in sorted(m4, key=lambda x: -(x["axes"]["livebench.coding"] or 0))[:6]:
        lbc = r['axes']['livebench.coding']
        elo = r['axes']['arena_code.elo']
        name = r['name'] or r['id']
        print(f"  {r['id']:35s} LB-Coding={lbc if lbc is not None else '-':>6}  Code-Elo={elo if elo is not None else '-':>4}")
    
    # Query 5: Pareto check — models with OR pricing + AA benchmarking
    print("\n── Query 5: OR price vs AA intel (all models) ──")
    m5 = pe.project(["aa.intel", "openrouter.inp_price_per_m"])
    with_data = [r for r in m5 if r["axes"]["aa.intel"] is not None and r["axes"]["openrouter.inp_price_per_m"] is not None]
    print(f"  Models with both AA intel + OR pricing: {len(with_data)}")
    for r in sorted(with_data, key=lambda x: -(x["axes"]["aa.intel"] or 0))[:10]:
        iq = r['axes']['aa.intel']
        orp = r['axes']['openrouter.inp_price_per_m']
        print(f"  {r['id']:35s} IQ={iq if iq is not None else '-':>5}  "
              f"OR-Inp=${orp if orp is not None else '-':>}/Mtok")
