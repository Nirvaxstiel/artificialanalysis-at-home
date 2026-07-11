// Black-box contract tests for viz/_result.js. Node-only, no jsdom, no deps.
// Import the module via require; assert observable Result behaviour by input->output.
const { ok, err, pipe, do: doSteps, fromFn } = require("../viz/_result.js");

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

// pipe left-to-right, stops at err
check("pipe chains", pipe(1, v => ok(v + 1), v => ok(v * 2), v => ok(v + 1)).unwrap() === 5);
let calls = [];
let r3 = pipe(1,
  v => { calls.push(v); return ok(v); },
  () => err("fail"),
  v => { calls.push("late"); return ok(v); });
check("pipe stops at err", r3.isErr() && r3.error === "fail" && calls.length === 1);

// do collects / stops
check("do collects", doSteps(() => ok(1), () => ok(2), () => ok(3)).unwrap().join(",") === "1,2,3");
check("do stops", doSteps(() => ok(1), () => err("nope"), () => ok(3)).isErr());

// fromFn
check("fromFn catches", fromFn(() => { throw new Error("boom"); }).isErr());
check("fromFn wraps", fromFn(() => "v").unwrap() === "v");

// match
check("match ok", ok(5).match({ ok: v => "ok:" + v, err: e => "err:" + e }) === "ok:5");
check("match err", err("z").match({ ok: v => "ok:" + v, err: e => "err:" + e }) === "err:z");

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
