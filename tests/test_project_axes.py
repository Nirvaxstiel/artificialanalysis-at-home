"""Black-box Result-contract tests for project_axes.ProjectionEngine.

Builds a minimal registry + axes catalog in a temp dir (no committed-artifact
dependency), constructs the engine, and asserts the observable Result behaviour:
known axis -> Ok, unknown axis -> Err, legitimately-absent value -> Ok(None),
project() still rejects unknown axes. No internal spying.
"""
import sys, os, json, tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))
from project_axes import ProjectionEngine  # noqa: E402


@pytest.fixture
def engine():
    d = tempfile.mkdtemp()
    registry = {
        "models": [
            {"id": "m1", "name": "Model One", "creator": "acme", "model_type": "chat",
             "meta": {"archetype": "frontier", "context_window": 1000},
             "benchmarks": {"aa": {"intel": 50}}, "pricing": {"aa": {"inp_price": 2.0}}},
            {"id": "m2", "name": "Model Two", "creator": "globex", "model_type": "chat",
             "meta": {}, "benchmarks": {}, "pricing": {}},
        ]
    }
    catalog = {
        "meta": {"sources": ["aa"]},
        "axes": [
            {"id": "aa.intel", "source": "aa", "type": "bench"},
            {"id": "aa.inp_price", "source": "aa", "type": "pricing"},
            {"id": "meta.context_window", "source": "meta", "type": "meta"},
        ],
    }
    rp = os.path.join(d, "model_registry.json")
    ap = os.path.join(d, "axes_catalog.json")
    with open(rp, "w") as f:
        json.dump(registry, f)
    with open(ap, "w") as f:
        json.dump(catalog, f)
    return ProjectionEngine(registry_path=rp, axes_path=ap)


def test_resolve_known_axis_ok(engine):
    r = engine.resolve_axis("aa.intel")
    assert r.is_ok()
    assert r.unwrap() == "aa.intel"


def test_resolve_unknown_axis_err(engine):
    r = engine.resolve_axis("nonexistent.axis")
    assert r.is_err()


def test_get_value_known_present_ok(engine):
    r = engine.get_value(engine.models[0], "aa.intel")
    assert r.is_ok()
    assert r.unwrap() == 50


def test_get_value_known_absent_ok_none(engine):
    r = engine.get_value(engine.models[1], "aa.intel")
    assert r.is_ok()
    assert r.unwrap() is None


def test_get_value_meta_axis_ok(engine):
    r = engine.get_value(engine.models[0], "meta.context_window")
    assert r.is_ok()
    assert r.unwrap() == 1000


def test_get_value_unknown_axis_err(engine):
    r = engine.get_value(engine.models[0], "nonexistent.axis")
    assert r.is_err()


def test_case_insensitive_axis_id(engine):
    assert engine.resolve_axis("AA.INTEL").is_ok()
    assert engine.get_value(engine.models[0], "AA.INTEL").unwrap() == 50


def test_project_rejects_unknown_axis(engine):
    with pytest.raises(ValueError):
        engine.project(["aa.intel", "bogus.axis"])


def test_project_rows_carry_ok_values(engine):
    rows = engine.project(["aa.intel", "meta.context_window"])
    by_id = {r["id"]: r for r in rows}
    assert by_id["m1"]["axes"]["aa.intel"] == 50
    assert by_id["m1"]["axes"]["meta.context_window"] == 1000
    assert "m2" not in by_id  # no axes present
