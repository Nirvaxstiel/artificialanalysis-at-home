// Result monad (Either) for result-oriented, error-short-circuiting pipelines.
// Mirrors data/_result.py. Ok(value) | Err(error). .bind short-circuits on Err.
// No dependencies, no DOM — importable from viz modules and node tests.

function ok(value) {
  return {
    tag: 'ok',
    value,
    isOk() { return true; },
    isErr() { return false; },
    bind(f) { return f(this.value); },
    map(f) { return ok(f(this.value)); },
    unwrap() { return this.value; },
    unwrapOr(_d) { return this.value; },
    match({ ok: onOk, err: _onErr }) { return onOk(this.value); },
  };
}

function err(error) {
  return {
    tag: 'err',
    error,
    isOk() { return false; },
    isErr() { return true; },
    bind(_f) { return err(this.error); },
    map(_f) { return err(this.error); },
    unwrap() { throw new Error('unwrap on Err: ' + String(this.error)); },
    unwrapOr(d) { return d; },
    match({ ok: _onOk, err: onErr }) { return onErr(this.error); },
  };
}

function fromFn(fn) {
  try {
    return ok(fn());
  } catch (e) {
    return err(e);
  }
}

if (typeof window !== 'undefined') {
  window.Result = { ok, err, fromFn };
}
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { ok, err, fromFn };
}
