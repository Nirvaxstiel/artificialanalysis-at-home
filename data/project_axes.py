import json, os, re
from pathlib import Path

from _result import ok, err

BASE = Path(__file__).resolve().parent if "__file__" in dir() else Path.cwd()
DATA = BASE / "data" if (BASE / "data").exists() else BASE


class ProjectionEngine:
    def __init__(self, registry_path=None, axes_path=None):
        rp = registry_path or str(DATA / "model_registry.json")
        ap = axes_path or str(DATA / "axes_catalog.json")

        with open(rp) as f:
            self.registry = json.load(f)
        with open(ap) as f:
            self.catalog = json.load(f)

        self.models = self.registry["models"]
        self.axes_meta = {a["id"].casefold(): a for a in self.catalog["axes"]}

        self._path_override = {
            "aa.cost_seg_total": ("pricing", "aa", "cost_segments", "total_cost_per_task_usd"),
            "aa.cost_seg_answer": ("pricing", "aa", "cost_segments", "answer_usd"),
            "aa.cost_seg_reasoning": ("pricing", "aa", "cost_segments", "reasoning_usd"),
            "aa.cost_seg_cache_write": ("pricing", "aa", "cost_segments", "cache_write_usd"),
            "aa.cost_seg_cache_hit": ("pricing", "aa", "cost_segments", "cache_hit_usd"),
            "aa.cost_seg_input": ("pricing", "aa", "cost_segments", "input_usd"),
        }

    def resolve_axis(self, axis_id):
        """Return Ok(lowercased axis key) or Err(unknown axis id)."""
        cf = axis_id.casefold()
        if cf in self.axes_meta:
            return ok(cf)
        return err(f"Axis '{axis_id}' not found")

    def get_value(self, model, axis_id):
        """Return Ok(value) where value may be None, or Err(unknown axis id)."""
        cf = axis_id.casefold()
        if cf in self._path_override:
            path = self._path_override[cf]
            sec = model
            for k in path[:-1]:
                sec = sec.get(k, {}) if isinstance(sec, dict) else {}
            return ok(sec.get(path[-1]) if isinstance(sec, dict) else None)

        resolved = self.resolve_axis(axis_id)
        if resolved.is_err():
            return resolved
        meta = self.axes_meta[resolved.unwrap()]
        actual_id = meta["id"]
        parts = actual_id.split(".")
        source = parts[0]

        dict_key = meta.get("_dict_key")

        if source == "meta":
            return ok(model.get("meta", {}).get(parts[-1]))

        if source in ("aa", "openrouter"):
            sec = model.get("benchmarks", {}).get(source, {})
            if len(parts) == 2:
                v = sec.get(dict_key or parts[1])
                if v is not None:
                    return ok(v)
                sec = model.get("pricing", {}).get(source, {})
                if len(parts) >= 3:
                    sub = sec.get(parts[1], {})
                    return ok(sub.get(parts[2] if len(parts) == 3 else dict_key))
                return ok(sec.get(dict_key or parts[1]))
            elif len(parts) == 3:
                sec = model.get("pricing", {}).get(source, {})
                sub = sec.get(parts[1], {})
                return ok(sub.get(parts[2]))

        if source in ("livebench", "arena_text", "arena_code", "openllm", "aa_img", "dirac"):
            sec = model.get("benchmarks", {}).get(source, {})
            if len(parts) == 2:
                return ok(sec.get(dict_key or parts[1]))
            elif len(parts) == 3:
                sub = sec.get(parts[1], {})
                return ok(sub.get(parts[2]))

        return ok(None)

    def project(self, axis_ids, model_ids=None, require_all=False):
        for aid in axis_ids:
            if self.resolve_axis(aid).is_err():
                raise ValueError(f"Axis '{aid}' not found")

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
                r = self.get_value(m, aid)
                if r.is_err():
                    raise ValueError(r.error)
                v = r.unwrap()
                row["axes"][aid] = v
                if v is None:
                    all_present = False

            if require_all and not all_present:
                continue

            if any(v is not None for v in row["axes"].values()):
                results.append(row)

        return results

    def feasibility_report(self, min_overlap=3):
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
            for s2 in sources[i + 1:]:
                a1 = axes_by_source[s1][:1]
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
        return self.axes_meta.get(axis_id)

    def list_axes(self, source=None, axis_type=None):
        results = []
        for a in self.catalog["axes"]:
            if source and a["source"] != source:
                continue
            if axis_type and a["type"] != axis_type:
                continue
            results.append(a)
        return results


if __name__ == "__main__":
    pe = ProjectionEngine()

    print("═══ PROJECTION ENGINE ═══")
    print(f"  Models: {len(pe.models):,}")
    print(f"  Axes:   {len(pe.catalog['axes'])}")
    print(f"  Sources: {pe.catalog['meta']['sources']}")

    print("\n═══ EXAMPLE QUERIES ═══")

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

    print("\n── Query 4: LiveBench coding vs Arena Code Elo ──")
    m4 = pe.project(["livebench.coding", "arena_code.elo"], require_all=True)
    print(f"  Models in both LiveBench coding + Arena Code: {len(m4)}")
    for r in sorted(m4, key=lambda x: -(x["axes"]["livebench.coding"] or 0))[:6]:
        lbc = r['axes']['livebench.coding']
        elo = r['axes']['arena_code.elo']
        name = r['name'] or r['id']
        print(f"  {r['id']:35s} LB-Coding={lbc if lbc is not None else '-':>6}  Code-Elo={elo if elo is not None else '-':>4}")

    print("\n── Query 5: OR price vs AA intel (all models) ──")
    m5 = pe.project(["aa.intel", "openrouter.inp_price_per_m"])
    with_data = [r for r in m5 if r["axes"]["aa.intel"] is not None and r["axes"]["openrouter.inp_price_per_m"] is not None]
    print(f"  Models with both AA intel + OR pricing: {len(with_data)}")
    for r in sorted(with_data, key=lambda x: -(x["axes"]["aa.intel"] or 0))[:10]:
        iq = r['axes']['aa.intel']
        orp = r['axes']['openrouter.inp_price_per_m']
        print(f"  {r['id']:35s} IQ={iq if iq is not None else '-':>5}  "
              f"OR-Inp=${orp if orp is not None else '-':>}/Mtok")
