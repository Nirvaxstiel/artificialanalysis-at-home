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

// Monadic pipeline — compose boot/render steps that return Result, threading a
// shared ctx. Mirrors data/_pipeline.Pipeline: each .then(name, fn) runs
// fn(ctx); a thrown error or returned Err short-circuits the rest. Steps that
// return a plain value are coerced to ok(value).
function Pipeline(ctx) {
  const self = {};
  self.ctx = ctx || {};
  self._steps = [];
  self.then = function (name, fn) {
    self._steps.push({ name, fn });
    return self;
  };
  self.run = function () {
    for (const step of self._steps) {
      let returned;
      try {
        returned = step.fn(self.ctx);
      } catch (e) {
        self.ctx._failed_step = step.name;
        self.ctx._error = e;
        return self.ctx;
      }
      const result = returned && typeof returned.isErr === 'function' ? returned : ok(returned);
      if (result.isErr()) {
        self.ctx._failed_step = step.name;
        self.ctx._error = result.error;
        return self.ctx;
      }
      self.ctx[step.name] = result.unwrap();
    }
    return self.ctx;
  };
  return self;
}

if (typeof window !== 'undefined') {
  window.Result = { ok, err, fromFn, Pipeline };
}
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { ok, err, fromFn, Pipeline };
}
