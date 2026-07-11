// Black-box contract tests for viz/_result.js. Node-only, no jsdom, no deps.
// Import the module via require; assert observable Result behaviour by input->output.
const { ok, err, fromFn } = require("../viz/_result.js");

let pass = 0, fail = 0;
function check(name, cond) {
  if (cond) { pass++; } else { fail++; console.log("FAIL:", name); }
}

// ok/err basics
check("ok unwrap", ok(42).unwrap() === 42);
check("ok isOk", ok(42).isOk() && !ok(42).isErr());
check("err isErr", err("x").isErr() && !err("x").isOk());
check("err unwrapOr", err("x").unwrapOr(7) === 7);

// bind short-circuit on err
let called = [];
let r1 = err("stop").bind(v => { called.push(v); return ok(v * 2); });
check("err bind skips step", r1.isErr() && r1.error === "stop" && called.length === 0);

// bind threads ok
let r2 = ok(3).bind(v => ok(v + 1)).bind(v => ok(v * 10));
check("ok bind chains", r2.unwrap() === 40);

// map
check("map ok only", ok(2).map(v => v + 5).unwrap() === 7 && err("e").map(v => v).isErr());

// unwrapOr
check("err unwrapOr", err("e").unwrapOr(0) === 0);
check("ok unwrapOr", ok(9).unwrapOr(0) === 9);

// fromFn
check("fromFn catches", fromFn(() => { throw new Error("boom"); }).isErr());
check("fromFn wraps", fromFn(() => "v").unwrap() === "v");

// match
check("match ok", ok(5).match({ ok: v => "ok:" + v, err: e => "err:" + e }) === "ok:5");
check("match err", err("z").match({ ok: v => "ok:" + v, err: e => "err:" + e }) === "err:z");

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
