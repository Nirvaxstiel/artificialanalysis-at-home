"""Deployment gate: the committed artifact must match the release manifest.

`_build_dashboard_data.build()` writes `data/manifest.json` next to the artifact
it records. This gate recomputes the artifact digest and compares it with the
manifest, so a `processed.js` that was regenerated without its manifest (or the
reverse) stops the deploy instead of shipping a stale release record.
"""

import hashlib
import json
import sys
from pathlib import Path

from _result import ok, err

BASE = Path(__file__).resolve().parent

GATED_FIELDS = ("artifact_sha256", "model_count", "sources")


def _load_json(path: Path):
    try:
        return ok(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeError, json.JSONDecodeError) as e:
        return err(f"{path.name}: {e}")


def _load_processed(path: Path):
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as e:
        return err(f"{path.name}: {e}")
    raw = raw.removeprefix("window.PROCESSED_DATA = ").removesuffix(";")
    try:
        return ok(json.loads(raw))
    except json.JSONDecodeError as e:
        return err(f"{path.name}: {e}")


def _artifact_digest(path: Path):
    try:
        return ok(hashlib.sha256(path.read_bytes()).hexdigest())
    except OSError as e:
        return err(f"{path.name}: {e}")


def verify(data_dir=None):
    root = Path(data_dir) if data_dir else BASE

    manifest = _load_json(root / "manifest.json")
    if manifest.is_err():
        return err(manifest.error)
    manifest = manifest.unwrap()

    artifact = root / manifest.get("artifact", "processed.js")
    payload = _load_processed(artifact)
    if payload.is_err():
        return err(payload.error)
    payload = payload.unwrap()

    digest = _artifact_digest(artifact)
    if digest.is_err():
        return err(digest.error)

    meta = payload["meta"]
    observed = {
        "artifact_sha256": digest.unwrap(),
        "model_count": meta["model_count"],
        "sources": {name: info.get("as_of") for name, info in meta["sources_meta"].items()},
    }
    for field in GATED_FIELDS:
        if manifest.get(field) != observed[field]:
            return err(f"{artifact.name} does not match manifest build {manifest.get('build_id')}: {field}")
    return ok(manifest)


if __name__ == "__main__":
    result = verify()
    if result.is_err():
        print("MANIFEST GATE FAILED:", result.error)
        raise SystemExit(1)
    state = result.unwrap()
    print(f"MANIFEST OK: {state['build_id']} ({state['model_count']} models, {len(state['sources'])} sources)")
